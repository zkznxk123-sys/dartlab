"""EDGAR report XBRL loader — 10-K/companyfacts.parquet 에서 태그 추출.

`edgar/report/*.py` 가 공용으로 사용하는 path 헬퍼 + XBRL filter loader.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import polars as pl

if TYPE_CHECKING:
    from dartlab.providers.edgar.company import Company


def edgarFinancePath(cik: str) -> Path:
    """EDGAR finance parquet 경로. 전체 report/notes에서 공용.

    Args:
        cik: SEC CIK (zero-padded 10 자리 또는 일반 정수 문자열).

    Returns:
        Path 객체 (실제 존재 여부는 별도 검사).

    Raises:
        없음.

    Example:
        >>> edgarFinancePath("0000320193")

    SeeAlso:
        - <TODO: 관련 함수/엔진>

    Requires:
        - polars
    """
    from dartlab.core.dataLoader import _getDataRoot

    return _getDataRoot() / "edgar" / "finance" / f"{cik}.parquet"


def loadXbrlTags(
    company: "Company",
    tagPattern: str,
    forms: list[str] | None = None,
    unitFilter: str | None = None,
) -> pl.DataFrame | None:
    """CIK parquet 에서 태그 패턴으로 XBRL 데이터를 로드.

    Args:
        company: EdgarCompany 인스턴스 (cik 속성 필요).
        tagPattern: ``pl.col("tag").str.contains()`` 에 전달할 정규식.
        forms: 필터할 form 유형. 기본 ``["10-K", "20-F"]``.
        unitFilter: unit 컬럼 정규식 필터. 예: ``"(?i)USD"``.

    Returns:
        매칭된 행. 없으면 None.

    Raises:
        없음 (parquet 부재·읽기 실패 시 None 반환).

    SeeAlso:
        - <TODO: 관련 함수/엔진>

    Requires:
        - polars
    """
    cik = getattr(company, "cik", None)
    if not cik:
        return None

    path = edgarFinancePath(cik)
    if not path.exists():
        return None

    if forms is None:
        forms = ["10-K", "20-F"]

    try:
        expr = pl.col("tag").str.contains(tagPattern) & pl.col("form").is_in(forms)
        if unitFilter:
            expr = expr & pl.col("unit").str.contains(unitFilter)
        df = pl.scan_parquet(path).filter(expr).collect(engine="streaming")
        return df if not df.is_empty() else None
    except (pl.exceptions.ComputeError, OSError):
        return None
