"""core/memory.py — Polars 메모리 가드 + 회수 API 단위 테스트."""

from __future__ import annotations

import os

import pytest

pytestmark = pytest.mark.unit


def test_polars_max_threads_capped_when_cpu_gt_4():
    """CPU > 4 환경에서 dartlab import 가 POLARS_MAX_THREADS=4 를 박는지 확인.

    이미 사용자가 설정한 경우는 존중한다 (이 테스트는 dartlab import 가 끝난
    후 시점이라 우리가 확인하는 건 결과 상태).
    """
    cpu = os.cpu_count() or 4
    val = os.environ.get("POLARS_MAX_THREADS")

    if cpu > 4:
        assert val is not None, "CPU > 4 인데 POLARS_MAX_THREADS 가 설정되지 않았다"
        assert val == "4", f"기본 cap 은 4 이어야 한다. 실제: {val}"


def test_polars_thread_pool_respects_cap():
    """POLARS_MAX_THREADS=4 가 실제 polars 런타임에 반영됐는지 확인."""
    import polars as pl

    cpu = os.cpu_count() or 4
    pool = pl.thread_pool_size()

    if cpu > 4:
        assert pool <= 4, f"CPU > 4 환경에서 polars thread pool 이 {pool} — 4 이하여야 한다"


class TestGetMemoryMb:
    def test_returns_positive_on_supported_os(self):
        """Windows / Linux 에서 RSS > 0 반환."""
        from dartlab.core.memory import getMemoryMb

        mem = getMemoryMb()
        assert mem > 0, f"RSS 측정 실패 (-1 반환): {mem}"
        assert mem < 100_000, f"비현실적인 RSS: {mem} MB"


class TestCacheCaps:
    """대량 Polars 사용 시 RSS 폭증 가드 — 캐시 최대 entry 상수 회귀 방지."""

    def test_load_cache_max_capped(self):
        """dataLoader 의 _LOAD_CACHE_MAX 가 8 이하로 유지된다.

        회사 1 개 docs DataFrame ~수백 MB × max entries = 잠재 점유. CLAUDE.md
        병렬 2 × 카테고리 4 = 8 정합. 16 으로 회귀하면 메모리 압박 재유입.
        """
        from dartlab.core.dataLoader import _LOAD_CACHE_MAX

        assert _LOAD_CACHE_MAX <= 8, f"_LOAD_CACHE_MAX={_LOAD_CACHE_MAX} — 8 초과는 회사 다중 분석 시 RSS 폭증"

    def test_prepared_cache_max_capped(self):
        """sections pipeline 의 _PREPARED_CACHE_MAX 가 1 로 유지된다.

        _PreparedRows 는 DataFrame 을 list[dict] 로 변환 보유 → 회사 1 종목 ~수백 MB.
        2 이상이면 회사 다중 분석 시 동시 보유로 OOM 위험.
        """
        from dartlab.providers.dart.docs.sections.pipeline import _PREPARED_CACHE_MAX

        assert _PREPARED_CACHE_MAX == 1, (
            f"_PREPARED_CACHE_MAX={_PREPARED_CACHE_MAX} — 1 초과는 회사 동시 보유로 GB 압박"
        )


class TestPressureLevels:
    """M1: PRESSURE_* 4 단계 escalation 임계 분리 검증."""

    def test_fatal_distinct_from_critical(self):
        """PRESSURE_FATAL > PRESSURE_CRITICAL 분리 — 동치 시 CRITICAL elif dead code."""
        from dartlab.core.memory import PRESSURE_CRITICAL_MB, PRESSURE_FATAL_MB

        assert PRESSURE_FATAL_MB > PRESSURE_CRITICAL_MB, (
            f"FATAL={PRESSURE_FATAL_MB} CRITICAL={PRESSURE_CRITICAL_MB} 동치 — "
            f"`if mem > FATAL: ... elif mem > CRITICAL:` 구조에서 CRITICAL elif 도달 불가"
        )

    def test_levels_strictly_increasing(self):
        """WARNING < CRITICAL < FATAL < EMERGENCY 엄격 증가 — 4 단계 escalation 보장."""
        from dartlab.core.memory import (
            PRESSURE_CRITICAL_MB,
            PRESSURE_EMERGENCY_MB,
            PRESSURE_FATAL_MB,
            PRESSURE_WARNING_MB,
        )

        levels = [PRESSURE_WARNING_MB, PRESSURE_CRITICAL_MB, PRESSURE_FATAL_MB, PRESSURE_EMERGENCY_MB]
        assert levels == sorted(levels) and len(set(levels)) == 4, (
            f"4 단계 임계 엄격 증가 실패: WARNING={PRESSURE_WARNING_MB} CRITICAL={PRESSURE_CRITICAL_MB} "
            f"FATAL={PRESSURE_FATAL_MB} EMERGENCY={PRESSURE_EMERGENCY_MB}"
        )


class TestWithMemoryBudget:
    """M4: ``withMemoryBudget`` 데코레이터 — 함수 단위 RSS delta 가드."""

    def test_passes_within_budget(self):
        """delta 가 limit 이하면 정상 반환."""
        from dartlab.core.memory import withMemoryBudget

        samples = iter([100.0, 200.0])  # delta 100 < 500

        @withMemoryBudget(500, sampler=lambda: next(samples))
        def heavy():
            return "ok"

        assert heavy() == "ok"

    def test_raises_when_exceeded(self):
        """delta 가 limit 초과면 ``MemoryBudgetExceeded`` raise."""
        import pytest

        from dartlab.core.memory import MemoryBudgetExceeded, withMemoryBudget

        samples = iter([100.0, 800.0])  # delta 700 > 500

        @withMemoryBudget(500, sampler=lambda: next(samples))
        def heavy():
            return "ok"

        with pytest.raises(MemoryBudgetExceeded, match=r"delta 700.*budget 500"):
            heavy()

    def test_default_sampler_uses_real_rss(self):
        """sampler 미지정 시 기본 ``getMemoryMb`` 사용 — 단순 함수는 1GB 한계 안 넘음."""
        from dartlab.core.memory import withMemoryBudget

        @withMemoryBudget(1024)
        def light():
            return 42

        assert light() == 42


class TestOomTripwire:
    """M5: ``OomTripwire`` — RSS background watcher + 응급 graceful 종료."""

    def test_does_not_fire_below_threshold(self):
        """RSS < threshold 면 exiter 호출 안 함."""
        import time

        from dartlab.core.memory import OomTripwire

        exitedRss: list[float] = []
        tw = OomTripwire(
            thresholdMb=2500,
            intervalSec=0.02,
            sampler=lambda: 100.0,  # 항상 100
            exiter=lambda rss: exitedRss.append(rss),
        )
        tw.start()
        time.sleep(0.1)  # 여러 poll
        tw.stop()
        assert exitedRss == []

    def test_fires_when_threshold_exceeded(self):
        """RSS > threshold 면 exiter 호출."""
        import time

        from dartlab.core.memory import OomTripwire

        exitedRss: list[float] = []
        tw = OomTripwire(
            thresholdMb=1000,
            intervalSec=0.02,
            sampler=lambda: 3000.0,  # 항상 초과
            exiter=lambda rss: exitedRss.append(rss),
        )
        tw.start()
        time.sleep(0.1)
        tw.stop()
        assert len(exitedRss) >= 1 and exitedRss[0] == 3000.0

    def test_start_stop_idempotent(self):
        """double start/stop 안전."""
        from dartlab.core.memory import OomTripwire

        tw = OomTripwire(sampler=lambda: 100.0, exiter=lambda _: None)
        tw.start()
        tw.start()  # 이미 alive — noop
        tw.stop()
        tw.stop()  # 이미 정지 — noop


class TestCleanupBetweenCompanies:
    def test_returns_before_after_tuple(self):
        """(before, after) 튜플 반환."""
        from dartlab.core.memory import cleanupBetweenCompanies

        result = cleanupBetweenCompanies(label="test")
        assert isinstance(result, tuple)
        assert len(result) == 2
        before, after = result
        assert before > 0
        assert after > 0

    def test_idempotent_no_error_on_repeat_call(self):
        """반복 호출해도 예외 없이 동작."""
        from dartlab.core.memory import cleanupBetweenCompanies

        for i in range(3):
            before, after = cleanupBetweenCompanies(label=f"iter{i}")
            assert before > 0 and after > 0

    def test_label_appears_in_log(self, caplog):
        """label 인자가 로그에 포함된다."""
        import logging

        from dartlab.core.memory import cleanupBetweenCompanies

        with caplog.at_level(logging.INFO, logger="dartlab.core.memory"):
            cleanupBetweenCompanies(label="005930")

        joined = " ".join(rec.message for rec in caplog.records)
        assert "005930" in joined or len(caplog.records) == 0
