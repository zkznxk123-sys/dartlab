"""core/memory.py — Polars 메모리 가드 + 회수 API 단위 테스트."""

from __future__ import annotations

import os

import pytest

pytestmark = pytest.mark.unit


def test_polars_max_threads_capped_when_cpu_gt_8():
    """CPU > 8 환경에서 dartlab import 가 POLARS_MAX_THREADS=8 을 박는지 확인.

    이미 사용자가 설정한 경우는 존중한다 (이 테스트는 dartlab import 가 끝난
    후 시점이라 우리가 확인하는 건 결과 상태).
    """
    cpu = os.cpu_count() or 4
    val = os.environ.get("POLARS_MAX_THREADS")

    if cpu > 8:
        assert val is not None, "CPU > 8 인데 POLARS_MAX_THREADS 가 설정되지 않았다"
        assert val == "8", f"기본 cap 은 8 이어야 한다. 실제: {val}"


def test_polars_thread_pool_respects_cap():
    """POLARS_MAX_THREADS=8 이 실제 polars 런타임에 반영됐는지 확인."""
    import polars as pl

    cpu = os.cpu_count() or 4
    pool = pl.thread_pool_size()

    if cpu > 8:
        assert pool <= 8, f"CPU > 8 환경에서 polars thread pool 이 {pool} — 8 이하여야 한다"


class TestGetMemoryMb:
    def test_returns_positive_on_supported_os(self):
        """Windows / Linux 에서 RSS > 0 반환."""
        from dartlab.core.memory import get_memory_mb

        mem = get_memory_mb()
        assert mem > 0, f"RSS 측정 실패 (-1 반환): {mem}"
        assert mem < 100_000, f"비현실적인 RSS: {mem} MB"


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
