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
