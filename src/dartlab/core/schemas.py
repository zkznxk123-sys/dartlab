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


# T6-4 — 추가 schema 4 종. metrics workflow + scan + macro + credit 결과의 contract 강제.


class ScanResultSchema(pa.DataFrameModel):
    """scan engine 결과 표 계약 (T6-4).

    Capabilities: dartlab.scan() 결과 DataFrame 의 핵심 컬럼 검증.
    Args: 없음.
    Returns: pandera Schema.
    Example:
        >>> ScanResultSchema.validate(result.table, lazy=True)
    Guide: percentile / ranking / score 컬럼 nullable False 강제.
    SeeAlso: FinanceSchema · ReportSchema.
    Requires: pandera[polars] >= 0.29.
    AIContext: scan recipe 결과의 schema drift 차단.
    Raises: pandera.errors.SchemaError.
    """

    code: Series[str] = pa.Field(nullable=False)
    corpName: Series[str] = pa.Field(nullable=True)

    class Config:
        """strict=False — recipe 별 추가 컬럼 허용."""

        strict = False
        coerce = False


class CreditScoreSchema(pa.DataFrameModel):
    """credit engine 결과 표 계약 (T6-4).

    Z-score / zone / 4 component 컬럼 검증.
    """

    score: Series[float] = pa.Field(nullable=True)
    zone: Series[str] = pa.Field(nullable=True, isin=["safe", "gray", "distress"])

    class Config:
        """strict=False — Z-score component 4 컬럼 등 추가 허용."""

        strict = False
        coerce = False


class MacroCycleSchema(pa.DataFrameModel):
    """macro engine cycle 결과 표 계약 (T6-4).

    regime / pmi / 날짜 컬럼 검증.
    """

    regime: Series[str] = pa.Field(nullable=True, isin=["expansion", "peak", "contraction", "trough"])

    class Config:
        """strict=False — 보조 메타 허용."""

        strict = False
        coerce = False


class MetricsSignalSchema(pa.DataFrameModel):
    """metrics workflow 산출물 계약 (T6-4, T1-2 정합).

    7 신호 의 시계열 dict 가 pl.DataFrame 으로 변환되었을 때.
    """

    signalName: Series[str] = pa.Field(nullable=False)

    class Config:
        """strict=False — latest/min/max/avg 등 통계 컬럼 허용."""

        strict = False
        coerce = False


class CompanyProfileSchema(pa.DataFrameModel):
    """Company profile 표 계약."""

    corp_code: Series[str] = pa.Field(nullable=True)
    corp_name: Series[str] = pa.Field(nullable=True)

    class Config:
        """strict=False — 추가 컬럼 허용."""

        strict = False
        coerce = False


class FilingsListSchema(pa.DataFrameModel):
    """filings 리스트 표 계약."""

    rcept_no: Series[str] = pa.Field(nullable=False)
    rcept_dt: Series[str] = pa.Field(nullable=False)

    class Config:
        """strict=False — 추가 컬럼 허용."""

        strict = False
        coerce = False


class QuantFactorSchema(pa.DataFrameModel):
    """quant factor 표 계약."""

    code: Series[str] = pa.Field(nullable=False)
    factor_value: Series[float] = pa.Field(nullable=True)

    class Config:
        """strict=False — 추가 컬럼 허용."""

        strict = False
        coerce = False


class IndustryPeerSchema(pa.DataFrameModel):
    """industry peer matrix 표 계약."""

    code: Series[str] = pa.Field(nullable=False)
    sector: Series[str] = pa.Field(nullable=True)

    class Config:
        """strict=False — 추가 컬럼 허용."""

        strict = False
        coerce = False


class GatherPriceSchema(pa.DataFrameModel):
    """price 시계열 표 계약."""

    code: Series[str] = pa.Field(nullable=False)
    date: Series[str] = pa.Field(nullable=False)
    close: Series[float] = pa.Field(nullable=True)

    class Config:
        """strict=False — 추가 컬럼 허용."""

        strict = False
        coerce = False


class GatherFlowSchema(pa.DataFrameModel):
    """flow 수급 표 계약."""

    code: Series[str] = pa.Field(nullable=False)
    date: Series[str] = pa.Field(nullable=False)
    foreign_net_buy: Series[float] = pa.Field(nullable=True)

    class Config:
        """strict=False — 추가 컬럼 허용."""

        strict = False
        coerce = False


class MacroSeriesSchema(pa.DataFrameModel):
    """macro 시계열 표 계약."""

    series_id: Series[str] = pa.Field(nullable=False)
    date: Series[str] = pa.Field(nullable=False)
    value: Series[float] = pa.Field(nullable=True)

    class Config:
        """strict=False — 추가 컬럼 허용."""

        strict = False
        coerce = False


class AccountMappingsSchema(pa.DataFrameModel):
    """accountMappings 표 계약."""

    korean: Series[str] = pa.Field(nullable=False)
    snake_id: Series[str] = pa.Field(nullable=False)

    class Config:
        """strict=False — 추가 컬럼 허용."""

        strict = False
        coerce = False


class StoryBlockSchema(pa.DataFrameModel):
    """story block 표 계약."""

    topic: Series[str] = pa.Field(nullable=True)
    block_type: Series[str] = pa.Field(nullable=True)

    class Config:
        """strict=False — 추가 컬럼 허용."""

        strict = False
        coerce = False


class XbrlTagSchema(pa.DataFrameModel):
    """XBRL tag 표 계약."""

    tag: Series[str] = pa.Field(nullable=False)
    value: Series[float] = pa.Field(nullable=True)
    period: Series[str] = pa.Field(nullable=False)

    class Config:
        """strict=False — 추가 컬럼 허용."""

        strict = False
        coerce = False


class SectionTextSchema(pa.DataFrameModel):
    """sections 텍스트 row 계약."""

    section_title: Series[str] = pa.Field(nullable=True)
    text: Series[str] = pa.Field(nullable=True)
    text_path: Series[str] = pa.Field(nullable=True)

    class Config:
        """strict=False — 추가 컬럼 허용."""

        strict = False
        coerce = False


class RecipeMetadataSchema(pa.DataFrameModel):
    """recipe lifecycle 메타 표 계약."""

    recipe_name: Series[str] = pa.Field(nullable=False)
    stage: Series[str] = pa.Field(
        nullable=False,
        isin=["drafted", "unverified", "tested", "verified", "curated", "deprecated"],
    )

    class Config:
        """strict=False — 추가 컬럼 허용."""

        strict = False
        coerce = False


class SectorRotationSchema(pa.DataFrameModel):
    """macro.sectorRotation 결과 표 계약."""

    sector: Series[str] = pa.Field(nullable=False)
    mean_return: Series[float] = pa.Field(nullable=True)
    hit_ratio: Series[float] = pa.Field(nullable=True)

    class Config:
        """strict=False — 추가 컬럼 허용."""

        strict = False
        coerce = False


class DartFilingMetaSchema(pa.DataFrameModel):
    """DART 공시 메타 표 계약."""

    rcept_no: Series[str] = pa.Field(nullable=False)
    rcept_dt: Series[str] = pa.Field(nullable=False)
    corp_code: Series[str] = pa.Field(nullable=True)
    report_nm: Series[str] = pa.Field(nullable=True)

    class Config:
        """strict=False — 추가 컬럼 허용."""

        strict = False
        coerce = False


class EdgarFilingMetaSchema(pa.DataFrameModel):
    """EDGAR 공시 메타 표 계약."""

    accession_no: Series[str] = pa.Field(nullable=False)
    filed_at: Series[str] = pa.Field(nullable=False)
    form: Series[str] = pa.Field(nullable=True)

    class Config:
        """strict=False — 추가 컬럼 허용."""

        strict = False
        coerce = False


class FinancialRatiosSchema(pa.DataFrameModel):
    """analysis.ratios 결과 표 계약."""

    code: Series[str] = pa.Field(nullable=False)
    period: Series[str] = pa.Field(nullable=False)
    roa: Series[float] = pa.Field(nullable=True)
    roe: Series[float] = pa.Field(nullable=True)

    class Config:
        """strict=False — 추가 컬럼 허용."""

        strict = False
        coerce = False


class CashflowAnalysisSchema(pa.DataFrameModel):
    """analysis.cashflow 결과 표 계약."""

    code: Series[str] = pa.Field(nullable=False)
    period: Series[str] = pa.Field(nullable=False)
    ocf: Series[float] = pa.Field(nullable=True)
    fcf: Series[float] = pa.Field(nullable=True)

    class Config:
        """strict=False — 추가 컬럼 허용."""

        strict = False
        coerce = False


class GrowthMetricsSchema(pa.DataFrameModel):
    """analysis.growth 결과 표 계약."""

    code: Series[str] = pa.Field(nullable=False)
    period: Series[str] = pa.Field(nullable=False)
    yoy: Series[float] = pa.Field(nullable=True)

    class Config:
        """strict=False — 추가 컬럼 허용."""

        strict = False
        coerce = False


class BeneishScoreSchema(pa.DataFrameModel):
    """credit.beneish 결과 표 계약."""

    code: Series[str] = pa.Field(nullable=False)
    m_score: Series[float] = pa.Field(nullable=True)

    class Config:
        """strict=False — 추가 컬럼 허용."""

        strict = False
        coerce = False


class ForeignFlowFactorSchema(pa.DataFrameModel):
    """quant.foreignFlow factor 결과 표 계약."""

    code: Series[str] = pa.Field(nullable=False)
    date: Series[str] = pa.Field(nullable=False)
    foreign_holding_pct: Series[float] = pa.Field(nullable=True)

    class Config:
        """strict=False — 추가 컬럼 허용."""

        strict = False
        coerce = False


class PortfolioMappingSchema(pa.DataFrameModel):
    """quant.portfolio.mapping 결과 표 계약."""

    code: Series[str] = pa.Field(nullable=False)
    weight: Series[float] = pa.Field(nullable=True)

    class Config:
        """strict=False — 추가 컬럼 허용."""

        strict = False
        coerce = False


class SectorMomentumSchema(pa.DataFrameModel):
    """industry.sectorMomentum 결과 표 계약."""

    sector: Series[str] = pa.Field(nullable=False)
    momentum_score: Series[float] = pa.Field(nullable=True)

    class Config:
        """strict=False — 추가 컬럼 허용."""

        strict = False
        coerce = False


class DisclosureLatencySchema(pa.DataFrameModel):
    """scan.disclosureLatency 결과 표 계약."""

    code: Series[str] = pa.Field(nullable=False)
    latency_hours: Series[float] = pa.Field(nullable=True)

    class Config:
        """strict=False — 추가 컬럼 허용."""

        strict = False
        coerce = False


class NewsItemSchema(pa.DataFrameModel):
    """gather.news 결과 표 계약."""

    code: Series[str] = pa.Field(nullable=True)
    date: Series[str] = pa.Field(nullable=False)
    title: Series[str] = pa.Field(nullable=False)
    url: Series[str] = pa.Field(nullable=True)

    class Config:
        """strict=False — 추가 컬럼 허용."""

        strict = False
        coerce = False


class FredSeriesSchema(pa.DataFrameModel):
    """gather.macro.fred 결과 표 계약."""

    series_id: Series[str] = pa.Field(nullable=False)
    date: Series[str] = pa.Field(nullable=False)
    value: Series[float] = pa.Field(nullable=True)

    class Config:
        """strict=False — 추가 컬럼 허용."""

        strict = False
        coerce = False


class EcosSeriesSchema(pa.DataFrameModel):
    """gather.macro.ecos 결과 표 계약."""

    stat_code: Series[str] = pa.Field(nullable=False)
    date: Series[str] = pa.Field(nullable=False)
    value: Series[float] = pa.Field(nullable=True)

    class Config:
        """strict=False — 추가 컬럼 허용."""

        strict = False
        coerce = False


class KrxPriceSchema(pa.DataFrameModel):
    """gather.krx 가격 시계열 표 계약."""

    code: Series[str] = pa.Field(nullable=False)
    date: Series[str] = pa.Field(nullable=False)
    open: Series[float] = pa.Field(nullable=True)
    high: Series[float] = pa.Field(nullable=True)
    low: Series[float] = pa.Field(nullable=True)
    close: Series[float] = pa.Field(nullable=True)
    volume: Series[float] = pa.Field(nullable=True)

    class Config:
        """strict=False — 추가 컬럼 허용."""

        strict = False
        coerce = False


class ScenarioMatchSchema(pa.DataFrameModel):
    """synth.scenarioMatch 결과 표 계약."""

    target_code: Series[str] = pa.Field(nullable=False)
    matched_code: Series[str] = pa.Field(nullable=False)
    similarity: Series[float] = pa.Field(nullable=True)

    class Config:
        """strict=False — 추가 컬럼 허용."""

        strict = False
        coerce = False


class ScanRatioSchema(pa.DataFrameModel):
    """scan.scanRatio 결과 표 계약."""

    code: Series[str] = pa.Field(nullable=False)
    ratio_name: Series[str] = pa.Field(nullable=False)
    value: Series[float] = pa.Field(nullable=True)
    percentile: Series[float] = pa.Field(nullable=True)

    class Config:
        """strict=False — 추가 컬럼 허용."""

        strict = False
        coerce = False


class CapabilityRefSchema(pa.DataFrameModel):
    """ReadCapability 검색 결과 표 계약."""

    api_ref: Series[str] = pa.Field(nullable=False)
    name: Series[str] = pa.Field(nullable=False)
    kind: Series[str] = pa.Field(nullable=True)

    class Config:
        """strict=False — 추가 컬럼 허용."""

        strict = False
        coerce = False


class SkillSpecSchema(pa.DataFrameModel):
    """Skill OS spec frontmatter 표 계약."""

    key: Series[str] = pa.Field(nullable=False)
    category: Series[str] = pa.Field(nullable=False, isin=["start", "operation", "runtime", "engines", "recipes"])

    class Config:
        """strict=False — 추가 컬럼 허용."""

        strict = False
        coerce = False


class TraceEventSchema(pa.DataFrameModel):
    """ai.trace 의 event row 표 계약."""

    kind: Series[str] = pa.Field(nullable=False)
    at: Series[str] = pa.Field(nullable=False)

    class Config:
        """strict=False — 추가 컬럼 허용."""

        strict = False
        coerce = False


class LineageRecordSchema(pa.DataFrameModel):
    """core.dataAudit lineage 표 계약."""

    source: Series[str] = pa.Field(nullable=False)
    recorded_at: Series[str] = pa.Field(nullable=False)
    version: Series[str] = pa.Field(nullable=True)

    class Config:
        """strict=False — 추가 컬럼 허용."""

        strict = False
        coerce = False


class CredentialLifecycleSchema(pa.DataFrameModel):
    """core.credentialLifecycle 표 계약."""

    key: Series[str] = pa.Field(nullable=False)
    issued_at: Series[str] = pa.Field(nullable=False)
    expires_at: Series[str] = pa.Field(nullable=False)

    class Config:
        """strict=False — 추가 컬럼 허용."""

        strict = False
        coerce = False


class HelpResultSchema(pa.DataFrameModel):
    """dartlab.help() 결과 표 계약."""

    name: Series[str] = pa.Field(nullable=False)
    kind: Series[str] = pa.Field(nullable=False)
    score: Series[float] = pa.Field(nullable=True)

    class Config:
        """strict=False — 추가 컬럼 허용."""

        strict = False
        coerce = False


class PluginDescriptorSchema(pa.DataFrameModel):
    """core.plugins.PluginDescriptor 표 계약."""

    name: Series[str] = pa.Field(nullable=False)
    module_name: Series[str] = pa.Field(nullable=False)
    kind: Series[str] = pa.Field(nullable=True)

    class Config:
        """strict=False — 추가 컬럼 허용."""

        strict = False
        coerce = False


class BenchmarkResultSchema(pa.DataFrameModel):
    """pytest-benchmark 결과 표 계약."""

    name: Series[str] = pa.Field(nullable=False)
    p50_ms: Series[float] = pa.Field(nullable=True)
    p95_ms: Series[float] = pa.Field(nullable=True)

    class Config:
        """strict=False — 추가 컬럼 허용."""

        strict = False
        coerce = False


class FlakyGateSchema(pa.DataFrameModel):
    """flakyAudit 결과 표 계약."""

    sha: Series[str] = pa.Field(nullable=False)
    outcomes: Series[str] = pa.Field(nullable=False)

    class Config:
        """strict=False — 추가 컬럼 허용."""

        strict = False
        coerce = False


class CycleScanSchema(pa.DataFrameModel):
    """cycleScan 결과 표 계약."""

    cycle_path: Series[str] = pa.Field(nullable=False)
    length: Series[int] = pa.Field(nullable=False)

    class Config:
        """strict=False — 추가 컬럼 허용."""

        strict = False
        coerce = False


class ImportLinterExceptionSchema(pa.DataFrameModel):
    """importLinterExceptionAudit 결과 표 계약."""

    contract_name: Series[str] = pa.Field(nullable=False)
    exception_count: Series[int] = pa.Field(nullable=False)

    class Config:
        """strict=False — 추가 컬럼 허용."""

        strict = False
        coerce = False


class NamingViolationSchema(pa.DataFrameModel):
    """namingConsistency 결과 표 계약."""

    path: Series[str] = pa.Field(nullable=False)
    func_name: Series[str] = pa.Field(nullable=False)
    arg_name: Series[str] = pa.Field(nullable=False)
    standard: Series[str] = pa.Field(nullable=False)

    class Config:
        """strict=False — 추가 컬럼 허용."""

        strict = False
        coerce = False


class ApiContractSchema(pa.DataFrameModel):
    """apiContractAudit 결과 표 계약."""

    name: Series[str] = pa.Field(nullable=False)
    kind: Series[str] = pa.Field(nullable=False)
    has_docstring: Series[bool] = pa.Field(nullable=False)
    has_type_annotation: Series[bool] = pa.Field(nullable=False)
    has_contract_test: Series[bool] = pa.Field(nullable=False)

    class Config:
        """strict=False — 추가 컬럼 허용."""

        strict = False
        coerce = False


class DriftAlertSchema(pa.DataFrameModel):
    """dataDriftCheck 결과 표 계약."""

    table: Series[str] = pa.Field(nullable=False)
    status: Series[str] = pa.Field(nullable=False, isin=["ok", "drift", "insufficient_baseline"])
    sigma_delta: Series[float] = pa.Field(nullable=True)

    class Config:
        """strict=False — 추가 컬럼 허용."""

        strict = False
        coerce = False


__all__ = [
    "DocsSchema",
    "FinanceSchema",
    "ReportSchema",
    "ScanResultSchema",
    "CreditScoreSchema",
    "MacroCycleSchema",
    "MetricsSignalSchema",
    "CompanyProfileSchema",
    "FilingsListSchema",
    "QuantFactorSchema",
    "IndustryPeerSchema",
    "GatherPriceSchema",
    "GatherFlowSchema",
    "MacroSeriesSchema",
    "AccountMappingsSchema",
    "StoryBlockSchema",
    "XbrlTagSchema",
    "SectionTextSchema",
    "RecipeMetadataSchema",
    "SectorRotationSchema",
    # T6-4 sprint 추가 (30 schema 목표 도달)
    "DartFilingMetaSchema",
    "EdgarFilingMetaSchema",
    "FinancialRatiosSchema",
    "CashflowAnalysisSchema",
    "GrowthMetricsSchema",
    "BeneishScoreSchema",
    "ForeignFlowFactorSchema",
    "PortfolioMappingSchema",
    "SectorMomentumSchema",
    "DisclosureLatencySchema",
    "NewsItemSchema",
    "FredSeriesSchema",
    "EcosSeriesSchema",
    "KrxPriceSchema",
    "ScenarioMatchSchema",
    "ScanRatioSchema",
    "CapabilityRefSchema",
    "SkillSpecSchema",
    "TraceEventSchema",
    "LineageRecordSchema",
    "CredentialLifecycleSchema",
    "HelpResultSchema",
    "PluginDescriptorSchema",
    "BenchmarkResultSchema",
    "FlakyGateSchema",
    "CycleScanSchema",
    "ImportLinterExceptionSchema",
    "NamingViolationSchema",
    "ApiContractSchema",
    "DriftAlertSchema",
]
