"""MarketBackend Protocol — 다시장 facade dispatch 인터페이스.

facade(`company.py`)는 이 Protocol 만 안다. 새 시장 추가 = `filings/{market}/`
패키지가 본 Protocol 을 구현 + bridge seed 추가. facade·core 무변경.

LLM Specifications:
    AntiPatterns:
        - facade 가 시장별 구체 모듈 직접 import 금지 — Protocol 으로만 dispatch.
        - build 를 Protocol 에 넣지 마라 — build 는 per-market CLI/CI (runtime 밖).
    OutputSchema:
        - ``MarketBackend`` Protocol (marketNs + ensureData/classify/statementWide/reportTopic).
    Prerequisites:
        - polars.
    TargetMarkets:
        - KR(DartBackend) / US(EdgarBackend) / JP(EdinetBackend).
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

import polars as pl


@runtime_checkable
class MarketBackend(Protocol):
    """시장별 백엔드 인터페이스 — facade 가 marketNs 로 dispatch.

    구현체: ``filings.dart.DartBackend`` 등. sections read 는 core 공통이라
    Protocol 밖 (facade 가 직접 core.sections 호출).
    """

    marketNs: str

    def ensureData(self, code: str) -> None:
        """로컬 데이터(sections/finance/report) 없으면 HF 다운로드."""
        ...

    def classify(self, key: str) -> tuple[str, dict]:
        """key → ("finance"|"report"|"sections", params) 분류 + alias resolve."""
        ...

    def statementWide(self, code: str, sjDiv: str, *, scope: str = "consolidated") -> pl.DataFrame | None:
        """재무제표 정규화 wide 표 (account × period). finance 분기에서 호출."""
        ...

    def reportTopic(self, code: str, key: str, *, period: str | None = None) -> pl.DataFrame | None:
        """report 항목(apiType) shaping. report 분기에서 호출."""
        ...
