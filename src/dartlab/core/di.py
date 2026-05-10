"""DI registry — F3 Protocol DIP 의 인스턴스 lookup.

L2 엔진은 `getXxxAccessor()` 로 default 인스턴스를 받거나, 테스트는
`setXxxAccessor(mock)` 으로 override. module-level singleton.

정공법 B (Protocol DIP) + C (호출 inversion) 의 결합:
- Protocol = core.protocols (이번 phase 추가)
- impl = gather.accessors / gather.macroProvider (gather 측 default)
- caller (story/Company/CLI/test) 가 setter 로 mock 주입 가능
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from dartlab.core.protocols import (
        FinanceDataAccessor,
        IndustryDataAccessor,
        MacroDataProvider,
        QuantDataAccessor,
    )


_financeAccessor: "FinanceDataAccessor | None" = None
_quantAccessor: "QuantDataAccessor | None" = None
_industryAccessor: "IndustryDataAccessor | None" = None
_macroProvider: "MacroDataProvider | None" = None


def getFinanceAccessor() -> "FinanceDataAccessor":
    """현재 finance accessor — 미설정 시 default 생성."""
    global _financeAccessor
    if _financeAccessor is None:
        from dartlab.gather.accessors import DefaultFinanceAccessor

        _financeAccessor = DefaultFinanceAccessor()
    return _financeAccessor


def setFinanceAccessor(impl: "FinanceDataAccessor | None") -> None:
    """finance accessor override (테스트). None 전달 시 default 로 reset."""
    global _financeAccessor
    _financeAccessor = impl


def getQuantAccessor() -> "QuantDataAccessor":
    """현재 quant accessor."""
    global _quantAccessor
    if _quantAccessor is None:
        from dartlab.gather.accessors import DefaultQuantAccessor

        _quantAccessor = DefaultQuantAccessor()
    return _quantAccessor


def setQuantAccessor(impl: "QuantDataAccessor | None") -> None:
    """quant accessor override."""
    global _quantAccessor
    _quantAccessor = impl


def getIndustryAccessor() -> "IndustryDataAccessor":
    """현재 industry accessor."""
    global _industryAccessor
    if _industryAccessor is None:
        from dartlab.gather.accessors import DefaultIndustryAccessor

        _industryAccessor = DefaultIndustryAccessor()
    return _industryAccessor


def setIndustryAccessor(impl: "IndustryDataAccessor | None") -> None:
    """industry accessor override."""
    global _industryAccessor
    _industryAccessor = impl


def getMacroProvider() -> "MacroDataProvider":
    """현재 macro provider."""
    global _macroProvider
    if _macroProvider is None:
        from dartlab.gather.macroProvider import DefaultMacroProvider

        _macroProvider = DefaultMacroProvider()
    return _macroProvider


def setMacroProvider(impl: "MacroDataProvider | None") -> None:
    """macro provider override."""
    global _macroProvider
    _macroProvider = impl
