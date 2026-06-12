"""dartlab.gather.entry.handlers mirror 슬롯 + dispatch 검증 (G+ P-Q2.1).

룰 7 mirror 만족 + 12 axis handler 가 모두 dispatch table 에 등록됐는지 확인.
"""

from __future__ import annotations

import importlib

import pytest

pytestmark = pytest.mark.unit


def test_smoke_import() -> None:
    """``dartlab.gather.entry.handlers`` 모듈 import 가능 — 모듈 구조 회귀 차단."""
    importlib.import_module("dartlab.gather.entry.handlers")


def test_all_axes_have_handler() -> None:
    """AXIS_REGISTRY 의 12 axis 모두 _AXIS_DISPATCH 에 handler 등록."""
    from dartlab.gather.entry.dispatch import AXIS_REGISTRY
    from dartlab.gather.entry.main import _AXIS_DISPATCH

    missing = set(AXIS_REGISTRY) - set(_AXIS_DISPATCH)
    extra = set(_AXIS_DISPATCH) - set(AXIS_REGISTRY)
    assert not missing, f"AXIS_REGISTRY axis 가 _AXIS_DISPATCH 에 없음: {missing}"
    assert not extra, f"_AXIS_DISPATCH 에 registry 미등록 axis: {extra}"


def test_handlers_callable() -> None:
    """12 handler 모두 callable + uniform 시그니처 (가짜 g 로 호출 안 함)."""
    from dartlab.gather.entry import handlers

    expected = [
        "handlePrice",
        "handleFlow",
        "handleMacro",
        "handleNews",
        "handleSector",
        "handleInsider",
        "handleOwnership",
        "handlePeers",
        "handleKrx",
        "handleKrxIndex",
        "handleCalendar",
        "handleDartDoc",
    ]
    for name in expected:
        assert hasattr(handlers, name), f"handlers.{name} 누락"
        assert callable(getattr(handlers, name)), f"handlers.{name} 가 callable 아님"


def test_calendar_handler_raises() -> None:
    """handleCalendar 는 항상 ValueError — 폐기된 axis."""
    from dartlab.gather.entry.handlers import handleCalendar

    with pytest.raises(ValueError, match="0.10 부터 폐기"):
        handleCalendar(None, None, market="KR", start=None, end=None, marketExplicit=False)


def test_dartDoc_handler_requires_target() -> None:
    """handleDartDoc 는 target 없으면 ValueError."""
    from dartlab.gather.entry.handlers import handleDartDoc

    with pytest.raises(ValueError, match="rcept_no"):
        handleDartDoc(None, None, market="KR", start=None, end=None, marketExplicit=False)
    with pytest.raises(ValueError, match="rcept_no"):
        handleDartDoc(None, "", market="KR", start=None, end=None, marketExplicit=False)


def test_flow_handler_accepts_all_alias() -> None:
    """handleFlow 는 공개 kwargs all=True 를 Gather.flow(full=True) 로 변환한다."""
    from dartlab.gather.entry.handlers import handleFlow

    seen = {}

    class FakeGather:
        def flow(self, target, **kwargs):
            seen["target"] = target
            seen.update(kwargs)
            return "flow-result"

    result = handleFlow(
        FakeGather(),
        "005930",
        market="KR",
        start=None,
        end=None,
        marketExplicit=False,
        all=True,
        sleepSec=0.5,
        proxy="http://proxy.example:8080",
    )

    assert result == "flow-result"
    assert seen["target"] == "005930"
    assert seen["full"] is True
    assert seen["sleepSec"] == 0.5
    assert seen["proxy"] == "http://proxy.example:8080"


def test_gather_entry_flow_targets_parallel(monkeypatch: pytest.MonkeyPatch) -> None:
    """gather("flow", targets=[...]) 는 batch 결과에 stockCode 컬럼을 붙인다."""
    import dartlab.gather as gatherPkg
    from dartlab.gather.entry.main import GatherEntry
    from dartlab.gather.sources import flow as flowSource

    seen: list[tuple[str, dict]] = []

    class FakeGather:
        _client = object()

    async def fakeFetch(stockCode, **kwargs):
        seen.append((stockCode, kwargs))
        return [
            {
                "date": "20260611",
                "foreignNet": 1.0 if stockCode == "005930" else 2.0,
                "institutionNet": 0.0,
                "individualNet": 0.0,
                "foreignHoldingRatio": 50.0,
            }
        ]

    monkeypatch.setattr(gatherPkg, "getDefaultGather", lambda: FakeGather())
    monkeypatch.setattr(flowSource, "fetch", fakeFetch)

    df = GatherEntry()(
        "flow",
        targets=["005930", "000660"],
        start="2026-06-01",
        parallel=2,
        proxy="http://proxy.example:8080",
    )

    assert df.select("stockCode").to_series().to_list() == ["000660", "005930"]
    assert {call[0] for call in seen} == {"005930", "000660"}
    assert all(call[1]["proxy"] == "http://proxy.example:8080" for call in seen)
    assert all(call[1]["start"] == "2026-06-01" for call in seen)


def test_gather_entry_flow_targets_auto_parallel_with_proxy(monkeypatch: pytest.MonkeyPatch) -> None:
    """proxy 설정 상태에서도 targets 기본 병렬은 종목 단위로 동작한다."""
    import asyncio

    import dartlab.gather as gatherPkg
    from dartlab.gather.entry.main import GatherEntry
    from dartlab.gather.sources import flow as flowSource

    active = 0
    maxActive = 0
    seen: list[tuple[str, str | None]] = []

    class FakeGather:
        _client = object()

    async def fakeFetch(stockCode, **kwargs):
        nonlocal active, maxActive
        active += 1
        maxActive = max(maxActive, active)
        await asyncio.sleep(0.01)
        active -= 1
        seen.append((stockCode, kwargs.get("proxy")))
        return [
            {
                "date": "20260611",
                "foreignNet": 1.0,
                "institutionNet": 0.0,
                "individualNet": 0.0,
                "foreignHoldingRatio": 50.0,
            }
        ]

    monkeypatch.setattr(gatherPkg, "getDefaultGather", lambda: FakeGather())
    monkeypatch.setattr(flowSource, "fetch", fakeFetch)

    df = GatherEntry()(
        "flow",
        ["005930", "000660", "035420"],
        limit=1,
        proxy="http://proxy.example:8080",
    )

    assert df.height == 3
    assert maxActive > 1
    assert {stockCode for stockCode, _proxy in seen} == {"005930", "000660", "035420"}
    assert all(proxy == "http://proxy.example:8080" for _stockCode, proxy in seen)
