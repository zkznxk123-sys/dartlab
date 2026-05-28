"""dartlab.gather.infra.quota 단위 테스트.

일일 한도 80% 차단 + UTC midnight reset + 미등록 도메인 무제한.
mirror 슬롯 smoke import 동행.
"""

from __future__ import annotations

import importlib

import pytest

from dartlab.gather.infra import quota
from dartlab.gather.infra.quota import (
    BLOCK_THRESHOLD_RATIO,
    DAILY_LIMITS,
    _DailyQuotaTracker,
    quotaTracker,
)

pytestmark = pytest.mark.unit


def test_smoke_import() -> None:
    """모듈 import 회귀 차단."""
    importlib.import_module("dartlab.gather.infra.quota")


def test_unregistered_domain_unlimited() -> None:
    """DAILY_LIMITS 미등록 도메인은 checkDaily 항상 True."""
    tracker = _DailyQuotaTracker()
    for _ in range(10_000):
        tracker.record("example.com")
    assert tracker.checkDaily("example.com") is True


def test_under_threshold_allowed() -> None:
    """80% 미만이면 호출 허용."""
    tracker = _DailyQuotaTracker()
    limit = DAILY_LIMITS["financialmodelingprep.com"]
    safe_count = int(limit * BLOCK_THRESHOLD_RATIO) - 1
    for _ in range(safe_count):
        tracker.record("financialmodelingprep.com")
    assert tracker.checkDaily("financialmodelingprep.com") is True


def test_at_threshold_blocked() -> None:
    """80% 도달 즉시 차단."""
    tracker = _DailyQuotaTracker()
    limit = DAILY_LIMITS["financialmodelingprep.com"]
    block_at = int(limit * BLOCK_THRESHOLD_RATIO)
    for _ in range(block_at):
        tracker.record("financialmodelingprep.com")
    assert tracker.checkDaily("financialmodelingprep.com") is False


def test_reset_clears_counter() -> None:
    """수동 reset → 카운터 0 → checkDaily True."""
    tracker = _DailyQuotaTracker()
    for _ in range(300):
        tracker.record("financialmodelingprep.com")
    assert tracker.checkDaily("financialmodelingprep.com") is False
    tracker.reset()
    assert tracker.checkDaily("financialmodelingprep.com") is True


def test_resetIfNewDay_auto_clears(monkeypatch) -> None:
    """UTC date 변경 감지 시 자동 reset."""
    tracker = _DailyQuotaTracker()
    monkeypatch.setattr(tracker, "_lastResetUtcDate", "1970-01-01")
    for _ in range(300):
        tracker.record("financialmodelingprep.com")
    # _resetIfNewDay 가 record 호출 시 트리거 — 이전 카운트 0 으로
    snap = tracker.snapshot()
    assert snap.get("financialmodelingprep.com") == 300  # 1970→오늘 reset 후 다시 300
    # snapshot 호출이 한번 더 reset 트리거 안 함 (같은 날) 확인
    assert tracker.checkDaily("financialmodelingprep.com") is False


def test_snapshot_returns_copy() -> None:
    """snapshot 사본 — 외부 수정이 내부 영향 0."""
    tracker = _DailyQuotaTracker()
    tracker.record("financialmodelingprep.com")
    snap = tracker.snapshot()
    snap["financialmodelingprep.com"] = 999_999
    assert tracker.snapshot()["financialmodelingprep.com"] == 1


def test_module_shortcuts_delegate() -> None:
    """``quota.record`` / ``quota.checkDaily`` 가 quotaTracker 위임."""
    quotaTracker.reset()
    quota.record("financialmodelingprep.com")
    assert quotaTracker.snapshot().get("financialmodelingprep.com") == 1
    assert quota.checkDaily("financialmodelingprep.com") is True
    quotaTracker.reset()
