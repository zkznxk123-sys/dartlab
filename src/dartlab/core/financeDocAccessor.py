"""재무공시 doc 단발 호출 추상화 — DIP (정공법 B).

analysis/financial 의 governance/predictionSignals/valuation 가 providers/dart/docs/finance/X
및 providers/dart/report/pivot 의 단발 함수 (sanction/contingentLiability/executive/
relatedPartyTx/pivotDividend) 를 직접 호출. 그게 analysis ↔ providers cycle 의 원인.

FinanceDocAccessor Protocol 을 core 에 두고 providers/dart 가 register.
analysis 는 core import 만 — provider 직접 의존 0.

CredentialProvider/LoaderProvider/ListingResolver/DisclosureFetcher 와 동일 패턴.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class FinanceDocAccessor(Protocol):
    """재무공시 doc 단발 호출 추상화 — analysis 가 사용."""

    def sanction(self, stockCode: str) -> Any | None:
        """제재 공시 doc — 실패 시 None."""
        ...

    def contingentLiability(self, stockCode: str) -> Any | None:
        """우발부채 doc — 실패 시 None."""
        ...

    def executive(self, stockCode: str) -> Any | None:
        """임원 보수/이력 doc — 실패 시 None."""
        ...

    def relatedPartyTx(self, stockCode: str) -> Any | None:
        """특수관계자 거래 doc — 실패 시 None."""
        ...

    def pivotDividend(self, stockCode: str) -> Any | None:
        """배당 pivot — 실패 시 None."""
        ...

    def buildAnnual(self, stockCode: str) -> Any | None:
        """연간 시리즈 (aSeries, aYears) 빌드 — finance/pivot 위임. 실패 시 None."""
        ...

    def buildTimeseries(self, stockCode: str) -> Any | None:
        """분기 시리즈 (qSeries, qPeriods) 빌드 — finance/pivot 위임. 실패 시 None."""
        ...

    def accountLabels(self) -> dict[str, str]:
        """계정 코드 → 한글 라벨 사전 — finance/mapper 위임. 미설치/실패 시 빈 dict."""
        ...

    def exportModules(self) -> list[tuple[str, str]]:
        """Export 가능한 모듈 (prop, label) 리스트 — provider company 위임. 미설치 시 빈 list."""
        ...


_ACCESSOR: FinanceDocAccessor | None = None

_KNOWN_ACCESSOR_MODULES: tuple[str, ...] = ("dartlab.providers.dart.accessor.financeDocAccessor",)
_DISCOVERED = False


def _discover() -> None:
    """알려진 FinanceDocAccessor 모듈을 한 번만 lazy import — register 트리거."""
    global _DISCOVERED
    if _DISCOVERED:
        return
    import importlib

    for modPath in _KNOWN_ACCESSOR_MODULES:
        try:
            importlib.import_module(modPath)
        except ImportError:
            continue
    _DISCOVERED = True


def registerFinanceDocAccessor(accessor: FinanceDocAccessor) -> None:
    """FinanceDocAccessor 등록 — providers 가 import 시점에 호출."""
    global _ACCESSOR
    _ACCESSOR = accessor


def getFinanceDocAccessor() -> FinanceDocAccessor | None:
    """현재 등록된 FinanceDocAccessor 반환. 미등록이면 None. auto-discovery 트리거."""
    _discover()
    return _ACCESSOR
