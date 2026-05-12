"""dartlab.gather.infra.telemetry mirror + emit 동작 검증 (G+ P-Q5.1)."""

from __future__ import annotations

import importlib

import pytest

pytestmark = pytest.mark.unit


def test_smoke_import() -> None:
    """``dartlab.gather.infra.telemetry`` 모듈 import 가능."""
    importlib.import_module("dartlab.gather.infra.telemetry")


def test_emit_fetch_no_op_listener_absent() -> None:
    """listener 없어도 emitGatherFetch 가 raise 하지 않음 (fire-and-forget)."""
    from dartlab.gather.infra.telemetry import emitGatherFetch

    # 호출 자체가 raise 없이 종료
    emitGatherFetch("price", 100.0, cacheHit=False, market="KR")
    emitGatherFetch("flow", 50.5, cacheHit=True)  # market 생략


def test_emit_cache_stats_updates_counters() -> None:
    """emitGatherCacheStats 가 모듈 카운터 갱신 — snapshot 으로 확인."""
    from dartlab.gather.infra.telemetry import emitGatherCacheStats, getCacheStatsSnapshot

    emitGatherCacheStats(hit=100, miss=20, evicted=5)
    snap = getCacheStatsSnapshot()
    assert snap["hit"] == 100
    assert snap["miss"] == 20
    assert snap["evicted"] == 5


def test_emit_fallback_no_op() -> None:
    """emitGatherFallback 도 raise 없음."""
    from dartlab.gather.infra.telemetry import emitGatherFallback

    emitGatherFallback("price", primary="naver", fallback="yahoo")


def test_snapshot_thread_safe_read() -> None:
    """getCacheStatsSnapshot 가 dict 사본 — caller 가 변경해도 모듈 상태 무영향."""
    from dartlab.gather.infra.telemetry import emitGatherCacheStats, getCacheStatsSnapshot

    emitGatherCacheStats(hit=10, miss=2, evicted=1)
    snap = getCacheStatsSnapshot()
    snap["hit"] = 99999  # caller 가 mutate
    snap2 = getCacheStatsSnapshot()
    assert snap2["hit"] == 10  # 원본 unchanged
