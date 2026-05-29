"""DART 데이터 보장 — 로컬 없으면 HF 단건 다운로드 (core.loader 사용).

finance/report 는 single-file (즉시 fetch). sections 는 period-sharded multi-file
이라 단건 fetch 불가 — 로컬 BUILD 또는 별도 HF snapshot 전제 (없으면 facade 가
None 처리).

LLM Specifications:
    AntiPatterns:
        - dartlab.core.dataLoader import 금지 — filings 독립 (core.loader 만).
    OutputSchema:
        - ``ensureData(code) -> None``.
    Prerequisites:
        - core.loader, dart.config.
    TargetMarkets:
        - KR (DART).
"""

from __future__ import annotations

from dartlab.filings.core.loader import downloadIfMissing
from dartlab.filings.dart import config


def ensureData(code: str, *, refresh: bool = False) -> None:
    """finance/report parquet 로컬 보장 (없으면 HF 다운로드).

    Args:
        code: 종목코드.
        refresh: True 면 존재해도 재다운로드.
    """
    downloadIfMissing(config.financePath(code), config.hfUrl("finance", code), refresh=refresh)
    downloadIfMissing(config.reportPath(code), config.hfUrl("report", code), refresh=refresh)
    # sections: period-sharded → 로컬 BUILD 전제. 단건 fetch 안 함.
