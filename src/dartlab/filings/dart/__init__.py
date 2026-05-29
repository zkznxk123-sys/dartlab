"""filings.dart — KR (DART) 시장 백엔드 (MarketBackend 구현).

facade 가 ``Company(code, "kr")`` 시 ``DART`` 인스턴스로 dispatch. sections read 는
core 공통(facade 가 직접 core.sections 호출), 본 백엔드는 finance/report/classify/
ensureData 시장-특화만 담당. build 는 ``filings.dart.build`` (CLI/CI, lxml).

구성:
    - ``config`` — paths/HF. ``finance`` — XBRL wide. ``report`` — apiType shaping.
    - ``classify`` — key 분기. ``loader`` — HF 보장. ``build/`` — zip→sections.
"""

from __future__ import annotations

import polars as pl

from dartlab.filings.dart.classify import classify as _classify
from dartlab.filings.dart.finance import statementWide as _statementWide
from dartlab.filings.dart.loader import ensureData as _ensureData
from dartlab.filings.dart.report import reportTopic as _reportTopic


class DartBackend:
    """DART(KR) MarketBackend 구현 — facade dispatch 의 KR 진입점."""

    marketNs: str = "kr"

    def ensureData(self, code: str) -> None:
        """finance/report 로컬 없으면 HF 다운로드 (sections 는 BUILD 전제)."""
        _ensureData(code)

    def classify(self, key: str) -> tuple[str, dict]:
        """key → (finance|report|sections, params) 분기 + alias resolve."""
        return _classify(key)

    def statementWide(self, code: str, sjDiv: str, *, scope: str = "consolidated") -> pl.DataFrame | None:
        """재무제표 정규화 wide 표 (account × period) — finance 분기."""
        return _statementWide(code, sjDiv, scope=scope)

    def reportTopic(self, code: str, key: str, *, period: str | None = None) -> pl.DataFrame | None:
        """report apiType 표 — report 분기."""
        return _reportTopic(code, key, period=period)


DART = DartBackend()

__all__ = ["DART", "DartBackend"]
