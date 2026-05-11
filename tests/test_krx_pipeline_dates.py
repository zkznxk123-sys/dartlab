"""KRX 데이터 파이프라인 날짜 정책 회귀 테스트.

KRX prices/index 자동 증분 빌드는 매 실행마다 어제와 오늘을 실제 API로
재조회한다. 이미 저장된 일자도 응답이 있으면 upsert 하며, 휴장일/미확정일의
빈 응답은 최신 필수 일자 누락으로 실패시키지 않는다.
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
    ("today", "expected"),
    [
        (date(2026, 4, 30), (date(2026, 4, 29), date(2026, 4, 30))),
        (date(2026, 5, 1), (date(2026, 4, 30), date(2026, 5, 1))),
        (date(2026, 5, 4), (date(2026, 5, 3), date(2026, 5, 4))),
    ],
)
def test_krx_incremental_range_always_checks_yesterday_and_today(krx_build_module, today, expected):
    """incremental 은 휴장/주말 추정 없이 어제와 오늘을 직접 확인한다."""
    assert krx_build_module._incrementalRange(today) == expected


@pytest.mark.unit
@pytest.mark.parametrize(
    ("today", "current_time", "requestedEnd"),
    [
        (date(2026, 4, 30), time(9, 0), date(2026, 4, 30)),
        (date(2026, 4, 30), time(17, 0), date(2026, 4, 30)),
        (date(2026, 5, 4), time(9, 0), date(2026, 5, 4)),
        (date(2026, 5, 4), time(17, 0), date(2026, 5, 4)),
        (date(2026, 5, 4), time(17, 0), date(2026, 4, 29)),
    ],
)
def test_krx_freshness_validation_does_not_require_empty_latest_date(
    krx_build_module,
    today,
    current_time,
    requestedEnd,
):
    """휴장/미확정 빈 응답 가능성을 최신 필수 일자로 강제하지 않는다."""
    assert krx_build_module._requiredLatestDate(requestedEnd, today=today, currentTime=current_time) is None


@pytest.mark.unit
def test_krx_freshness_accepts_empty_yesterday_today_response(krx_build_module):
    """어제~오늘이 모두 휴장/미확정이면 empty 로 성공 종료할 수 있어야 한다."""
    krx_build_module._validateFreshFetch(
        pl.DataFrame(),
        startD=date(2026, 5, 3),
        endD=date(2026, 5, 4),
        context="regression",
    )


@pytest.mark.unit
@pytest.mark.parametrize(
    ("bas_dd", "now", "expected"),
    [
        ("20260430", datetime(2026, 4, 30, 9, 0), True),
        ("20260430", datetime(2026, 4, 30, 17, 0), True),
        ("20260429", datetime(2026, 4, 30, 9, 0), True),
        ("20260501", datetime(2026, 4, 30, 17, 0), False),
        ("20260503", datetime(2026, 5, 3, 17, 0), True),
    ],
)
def test_krx_direct_api_guard_only_blocks_future_dates(bas_dd, now, expected):
    """직접 API 내부 가드는 미래 날짜만 막고 오늘은 실제 응답을 확인한다."""
    from dartlab.gather.krx.krxApi import _KST, _isFinalized

    assert _isFinalized(bas_dd, now=now.replace(tzinfo=_KST)) is expected


@pytest.mark.unit
@pytest.mark.asyncio
async def test_krx_price_range_calls_weekend_days(monkeypatch):
    """가격 range 는 어제/오늘이 주말이어도 API 를 직접 호출한다."""
    from dartlab.gather.krx import krxApi

    calls: list[tuple[str, str]] = []

    async def fake_fetch(basDd, *, market, apiKey, client):
        calls.append((basDd, market))
        return pl.DataFrame()

    monkeypatch.setattr(krxApi, "fetchKrxBydd", fake_fetch)

    await krxApi.fetchKrxRange("2026-05-03", "2026-05-04", market="STK", apiKey="KEY", sleepSec=0)

    assert calls == [("20260504", "STK"), ("20260503", "STK")]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_krx_index_range_calls_weekend_days(monkeypatch):
    """지수 range 도 어제/오늘이 주말이어도 API 를 직접 호출한다."""
    from dartlab.gather.krx import krxIndex

    calls: list[tuple[str, str]] = []

    async def fake_fetch(basDd, *, market, apiKey, client):
        calls.append((basDd, market))
        return pl.DataFrame()

    monkeypatch.setattr(krxIndex, "fetchKrxIndexBydd", fake_fetch)

    await krxIndex.fetchKrxIndexRange(
        "2026-05-03",
        "2026-05-04",
        market="KOSPI",
        apiKey="KEY",
        concurrency=1,
    )

    assert calls == [("20260503", "KOSPI"), ("20260504", "KOSPI")]
