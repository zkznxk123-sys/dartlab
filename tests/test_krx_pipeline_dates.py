"""KRX 데이터 파이프라인 날짜 정책 회귀 테스트.

Regression for #29. KRX prices/index 자동 증분 빌드는 장중에는 직전 거래 가능
평일(T-1), 장마감 이후 평일에는 당일(T-0)을 최신 확정 대상으로 삼아야 한다.
"""

from __future__ import annotations

import importlib.util
from datetime import date, datetime, time
from pathlib import Path

import polars as pl
import pytest

_ROOT = Path(__file__).resolve().parents[1]


def _load_build_script(name: str):
    path = _ROOT / "scripts" / "build" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(params=["buildKrxData", "buildKrxIndexData"])
def krx_build_module(request):
    return _load_build_script(request.param)


@pytest.mark.unit
@pytest.mark.parametrize(
    ("today", "current_time", "expected"),
    [
        (date(2026, 4, 30), time(9, 0), date(2026, 4, 29)),
        (date(2026, 4, 30), time(17, 0), date(2026, 4, 30)),
        (date(2026, 4, 30), time(20, 0), date(2026, 4, 30)),
        (date(2026, 5, 3), time(20, 0), date(2026, 5, 1)),
        (date(2026, 5, 4), time(9, 0), date(2026, 5, 1)),
        (date(2026, 5, 4), time(17, 0), date(2026, 5, 4)),
    ],
)
def test_krx_incremental_target_follows_market_close(krx_build_module, today, current_time, expected):
    """Regression for #29: 장중은 T-1, 장마감 이후 평일은 T-0이다."""
    assert krx_build_module._latestFetchableDate(today, current_time) == expected


@pytest.mark.unit
@pytest.mark.parametrize(
    ("today", "current_time", "requestedEnd", "expected"),
    [
        (date(2026, 4, 30), time(9, 0), date(2026, 4, 30), date(2026, 4, 29)),
        (date(2026, 4, 30), time(17, 0), date(2026, 4, 30), date(2026, 4, 30)),
        (date(2026, 5, 4), time(9, 0), date(2026, 5, 4), date(2026, 5, 1)),
        (date(2026, 5, 4), time(17, 0), date(2026, 5, 4), date(2026, 5, 4)),
        (date(2026, 5, 4), time(17, 0), date(2026, 4, 29), date(2026, 4, 29)),
    ],
)
def test_krx_freshness_validation_uses_same_market_close_policy(
    krx_build_module,
    today,
    current_time,
    requestedEnd,
    expected,
):
    """Regression for #29: 검증도 fetch target 과 같은 장마감 정책을 쓴다."""
    assert krx_build_module._requiredLatestDate(requestedEnd, today=today, currentTime=current_time) == expected


@pytest.mark.unit
def test_krx_freshness_accepts_today_after_market_close(krx_build_module, monkeypatch):
    """Regression for #29: 장마감 이후 당일 데이터가 있으면 정상이다."""
    monkeypatch.setattr(krx_build_module, "_requiredLatestDate", lambda endD: date(2026, 4, 30))
    df = pl.DataFrame({"BAS_DD": ["20260430"]})

    krx_build_module._validateFreshFetch(
        df,
        startD=date(2026, 4, 30),
        endD=date(2026, 4, 30),
        context="regression",
    )


@pytest.mark.unit
def test_krx_freshness_rejects_missing_today_after_market_close(krx_build_module, monkeypatch):
    """Regression for #29: 장마감 이후 당일 누락은 success 로 삼키지 않는다."""
    monkeypatch.setattr(krx_build_module, "_requiredLatestDate", lambda endD: date(2026, 4, 30))
    df = pl.DataFrame({"BAS_DD": ["20260429"]})

    with pytest.raises(RuntimeError, match="required>=2026-04-30"):
        krx_build_module._validateFreshFetch(
            df,
            startD=date(2026, 4, 29),
            endD=date(2026, 4, 30),
            context="regression",
        )


@pytest.mark.unit
@pytest.mark.parametrize(
    ("bas_dd", "now", "expected"),
    [
        ("20260430", datetime(2026, 4, 30, 9, 0), False),
        ("20260430", datetime(2026, 4, 30, 17, 0), True),
        ("20260429", datetime(2026, 4, 30, 9, 0), True),
        ("20260501", datetime(2026, 4, 30, 17, 0), False),
        ("20260503", datetime(2026, 5, 3, 17, 0), False),
    ],
)
def test_krx_direct_api_finalized_guard_follows_market_close(bas_dd, now, expected):
    """Regression for #29: 직접 API 내부 가드도 장마감 이후 당일을 막지 않는다."""
    from dartlab.gather.krxApi import _KST, _isFinalized

    assert _isFinalized(bas_dd, now=now.replace(tzinfo=_KST)) is expected
