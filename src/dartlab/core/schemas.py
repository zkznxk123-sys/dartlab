"""dartlab 데이터 프레임 계약 — Pandera polars schema SSOT.

Capabilities:
    DART/EDGAR/EDINET 의 raw finance/report/docs parquet 가 *런타임 schema drift*
    를 일으키지 않도록 컬럼 이름·필수 존재·타입을 명시. Pandera 0.31+ 의 polars
    네이티브 백엔드 사용. silent None 누락 · 의도 외 컬럼 삭제 · DART 응답 schema
    변경 같은 데이터 회귀를 *gather 끝점* 에서 즉시 차단한다.

Guide:
    - 본 schema 는 **최소 보장 (minimum-spec)** 정책 — 핵심 컬럼 존재만 강제,
      도메인 정규식·not-null 같은 강한 제약은 fixture 다양성 (24 null row 등)
      때문에 단계적 도입.
    - validate(df, lazy=True) 권장 (모든 위반을 한 번에 모아서 raise).
    - 향후 단계: account_id null 허용율 monitoring → strict null check 격상.

Example:
    >>> import polars as pl
    >>> from dartlab.core.schemas import FinanceSchema
    >>> df = pl.read_parquet("tests/fixtures/005930.finance.parquet")
    >>> FinanceSchema.validate(df, lazy=True)

AIContext:
    raw 끝점 (gather/dart/finance.fetchFinance 등) 의 결과를 *데이터 계약* 으로
    못박는다. dartlabGuard (코드 구조 계약) 와 직교 — 본 schema 는 *데이터* 계약.

SeeAlso:
    - dartlab.gather.dart.finance — fetchFinance 의 validate 호출 지점.
    - tests/_schemas/test_finance_schema.py — fixture 12 종 + hypothesis fuzz.
    - operation.code — 데이터 계약 SSOT 위치 룰.

Requires:
    pandera[polars] >= 0.29. dev dependency (production wheel 영향 없음).

LLM Specifications:
    AntiPatterns:
        - schema 없이 raw fetch → silent None / 잘못된 컬럼 누락.
        - validate 결과 무시 (lazy=False 인데 except 로 삼킴).
    OutputSchema:
        DataFrameModel 인스턴스 — pandera Schema 객체.
    Prerequisites:
        polars >= 1.x. pandera >= 0.29.
    Freshness:
        DART API 응답 schema 변경 시 즉시 갱신 필요.
    Dataflow:
        raw fetch → Schema.validate(df) → 통과 시 caller 반환, 실패 시 예외.
    TargetMarkets:
        KR (DART finance/report/docs), US (EDGAR), JP (EDINET).
"""

from __future__ import annotations

import pandera.polars as pa
from pandera.typing.polars import Series


class FinanceSchema(pa.DataFrameModel):
    """DART finance raw parquet 계약 — 핵심 컬럼 존재 검증.

    Capabilities: finance fixture 10 종 + raw fetch 결과의 12 핵심 컬럼이 *존재*
    하는지 보장. 값 도메인 제약 (정규식) 은 향후 단계.
    Args: 없음 (class-level).
    Returns: pandera Schema (validate / strategy 메서드 노출).
    Example:
        >>> FinanceSchema.validate(df, lazy=True)
    Guide: raw 끝점 직후 호출 권장. 24 row 가 null 인 fixture (207940 등) 존재로
        nullable=True 정책.
    SeeAlso: ReportSchema · DocsSchema.
    Requires: pandera[polars] >= 0.29.
    AIContext: silent drift 차단의 1 차 방어선 — 컬럼 *이름 변경* / *삭제* 즉시 탐지.
    Raises: pandera.errors.SchemaError — 컬럼 누락.
    """

    rcept_no: Series[str] = pa.Field(nullable=True)
    reprt_code: Series[str] = pa.Field(nullable=True)
    bsns_year: Series[str] = pa.Field(nullable=True)
    corp_code: Series[str] = pa.Field(nullable=True)
    sj_div: Series[str] = pa.Field(nullable=True)
    sj_nm: Series[str] = pa.Field(nullable=True)
    account_id: Series[str] = pa.Field(nullable=True)
    account_nm: Series[str] = pa.Field(nullable=True)
    thstrm_amount: Series[str] = pa.Field(nullable=True)
    corp_name: Series[str] = pa.Field(nullable=True)
    stock_code: Series[str] = pa.Field(nullable=True)
    fs_div: Series[str] = pa.Field(nullable=True)

    class Config:
        """strict=False (추가 컬럼 허용), coerce=False — 타입 강제 변환 안 함."""

        strict = False
        coerce = False


class ReportSchema(pa.DataFrameModel):
    """DART report raw 계약 — 핵심 메타 4 컬럼.

    Capabilities: report fixture (005930) + raw fetch 결과의 식별 컬럼 4 종 검증.
    report 본문 컬럼 (thstrm/frmtrm/lwfr 등) 은 카테고리별 (사업/반기/분기) 차이
    있어 본 schema 에 포함하지 않음.
    Args: 없음.
    Returns: pandera Schema.
    Example:
        >>> ReportSchema.validate(df, lazy=True)
    Guide: docs 와 다름 — report 는 보고서 본문 표, docs 는 첨부 (zip 압축).
    SeeAlso: FinanceSchema · DocsSchema.
    Requires: pandera[polars] >= 0.29.
    AIContext: report 본문 키워드 검색 (BM25) 의 입력 검증.
    Raises: pandera.errors.SchemaError.
    """

    rcept_no: Series[str] = pa.Field(nullable=True)
    corp_code: Series[str] = pa.Field(nullable=True)
    corp_name: Series[str] = pa.Field(nullable=True)
    bsns_year: Series[str] = pa.Field(nullable=True)

    class Config:
        """strict=False — DART report 의 카테고리별 추가 컬럼 허용."""

        strict = False
        coerce = False


class DocsSchema(pa.DataFrameModel):
    """DART docs (zip 안 HTML 섹션 텍스트) raw 계약.

    Capabilities: docs fixture (005930.docs.parquet) + ZipDocsCollector 결과의
    section 단위 핵심 컬럼 검증.
    Args: 없음.
    Returns: pandera Schema.
    Example:
        >>> DocsSchema.validate(df, lazy=True)
    Guide: section_content 가 길어 메모리 주의 — heavy marker 부착.
    SeeAlso: FinanceSchema · ReportSchema.
    Requires: pandera[polars] >= 0.29.
    AIContext: docs 본문 BM25 색인 (ngramIndex/fieldIndex) 의 입력 검증.
    Raises: pandera.errors.SchemaError.
    """

    rcept_no: Series[str] = pa.Field(nullable=True)
    corp_code: Series[str] = pa.Field(nullable=True)
    corp_name: Series[str] = pa.Field(nullable=True)
    section_title: Series[str] = pa.Field(nullable=True)
    section_content: Series[str] = pa.Field(nullable=True)

    class Config:
        """strict=False — section_order/section_url 등 보조 컬럼 허용."""

        strict = False
        coerce = False


__all__ = ["DocsSchema", "FinanceSchema", "ReportSchema"]
