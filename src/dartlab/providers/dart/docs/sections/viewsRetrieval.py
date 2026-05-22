"""sections retrieval 뷰 — _buildSemanticExpr / _buildDetailExpr / retrievalBlocks.

views.py 1175 LoC 분할 (룰 3 LoC 임계 회피). 본 모듈은 sections 블록을 의미적
topic 분류 + 검색용 우선순위 부여한 DataFrame 으로 빌드.
"""

from __future__ import annotations

import polars as pl

from dartlab.providers.dart.docs.sections.mapper import mapSectionTitle
from dartlab.providers.dart.docs.sections.pipeline import iterPeriodSubsets
from dartlab.providers.dart.docs.sections.sectionsBase import periodOrderValue

_BOILERPLATE_SET = [
    "사업보고서",
    "분기보고서",
    "반기보고서",
    "정정신고(보고)",
    "ceoConfirmation",
]
_PLACEHOLDER_PHRASES = [
    "분기보고서에 기재하지 않습니다",
    "반기보고서에 기재하지 않습니다",
    "반기ㆍ사업보고서에 기재 예정",
    "반기·사업보고서에 기재 예정",
    "기업공시서식 작성기준에 따라 분기보고서에 기재하지 않습니다",
]


def _buildSemanticExpr() -> pl.Expr:
    """semanticTopicForBlock → Polars when/then 체인."""
    joined = pl.concat_str([pl.col("topic"), pl.lit("\n"), pl.col("blockLabel"), pl.lit("\n"), pl.col("blockText")])
    expr = (
        pl.when((pl.col("topic") == "audit") & joined.str.contains("감사의견|감사인|검토절차"))
        .then(pl.lit("audit"))
        .when((pl.col("topic") == "auditSystem") & joined.str.contains("감사위원회|내부감사|내부회계|준법지원인"))
        .then(pl.lit("auditSystem"))
        .when((pl.col("topic") == "majorHolder") & joined.str.contains("최대주주|주식소유|5%이상"))
        .then(pl.lit("majorHolder"))
        .when((pl.col("topic") == "environmentRegulation") & joined.str.contains("환경|배출권|규제|녹색경영"))
        .then(pl.lit("environmentRegulation"))
        .when((pl.col("topic") == "majorContractsAndRnd") & joined.str.contains("연구개발|R&D|주요계약"))
        .then(pl.lit("majorContractsAndRnd"))
        .otherwise(pl.lit(None))
    )
    return expr


def _buildDetailExpr() -> pl.Expr:
    """detailTopicForBlock → Polars when/then 체인."""
    hay = pl.concat_str([pl.col("rawTitle"), pl.lit("\n"), pl.col("blockLabel"), pl.lit("\n"), pl.col("blockText")])
    expr = (
        pl.when((pl.col("topic") == "productService") & hay.str.contains("신탁업무\\(상세\\)", literal=False))
        .then(pl.lit("trustBusinessDetail"))
        .when(
            (pl.col("topic") == "productService")
            & hay.str.contains("예금업무\\(상세\\)|예금상품\\(상세\\)", literal=False)
        )
        .then(pl.lit("bankDepositProductDetail"))
        .when(
            (pl.col("topic") == "productService")
            & hay.str.contains("대출업무\\(상세\\)|대출상품\\(상세\\)", literal=False)
        )
        .then(pl.lit("bankLoanProductDetail"))
        .when((pl.col("topic") == "productService") & hay.str.contains("신용카드상품\\(상세\\)", literal=False))
        .then(pl.lit("cardProductDetail"))
        .when((pl.col("topic") == "productService") & hay.str.contains("상품및서비스개요\\(상세\\)", literal=False))
        .then(pl.lit("financialProductOverviewDetail"))
        .when(
            (pl.col("topic") == "riskDerivative")
            & hay.str.contains("장내파생상품거래현황\\(상세\\)|신용파생상품상세명세\\(상세\\)", literal=False)
        )
        .then(pl.lit("derivativeProductDetail"))
        .when(
            (pl.col("topic") == "intellectualProperty")
            & hay.str.contains("지적재산권보유현황|주요지적재산권현황", literal=False)
        )
        .then(pl.lit("ipPortfolioDetail"))
        .when((pl.col("topic") == "majorContractsAndRnd") & hay.str.contains("연구개발실적\\(", literal=False))
        .then(pl.lit("rndPortfolioDetail"))
        .when(
            (pl.col("topic") == "salesOrder") & hay.str.contains("수주상황\\(상세\\)|수주현황\\(상세\\)", literal=False)
        )
        .then(pl.lit("orderBacklogDetail"))
        .when(
            (pl.col("topic") == "majorContractsAndRnd")
            & hay.str.contains("경영상의주요계약\\(상세\\)|경영상의주요계약\\[상세\\]", literal=False)
        )
        .then(pl.lit("majorContractDetail"))
        .when(
            (pl.col("topic") == "affiliateGroupDetail")
            & hay.str.contains("기업집단에소속된회사\\(상세\\)", literal=False)
        )
        .then(pl.lit("affiliateCompanyDetail"))
        .when((pl.col("topic") == "financialNotes") & hay.str.contains("재고자산|inventory", literal=False))
        .then(pl.lit("noteInventoryDetail"))
        .when((pl.col("topic") == "financialNotes") & hay.str.contains("감가상각|depreciation", literal=False))
        .then(pl.lit("noteDepreciationDetail"))
        .when((pl.col("topic") == "financialNotes") & hay.str.contains("제조원가|manufacturing", literal=False))
        .then(pl.lit("noteManufacturingCostDetail"))
        .when((pl.col("topic") == "financialNotes") & hay.str.contains("법인세|세무|tax", literal=False))
        .then(pl.lit("noteTaxDetail"))
        .when((pl.col("topic") == "financialNotes") & hay.str.contains("유가증권|securities", literal=False))
        .then(pl.lit("noteSecuritiesDetail"))
        .when((pl.col("topic") == "financialNotes") & hay.str.contains("채권|매출채권|receivables", literal=False))
        .then(pl.lit("noteReceivablesDetail"))
        .when(
            (pl.col("topic") == "financialNotes") & hay.str.contains("차입금|사채|채무|debt|borrowings", literal=False)
        )
        .then(pl.lit("noteDebtDetail"))
        .when((pl.col("topic") == "financialNotes") & hay.str.contains("예금|현금|cash", literal=False))
        .then(pl.lit("noteCashDetail"))
        .when((pl.col("topic") == "audit") & hay.str.contains("감사보수|보수|비감사용역", literal=False))
        .then(pl.lit("auditFeeDetail"))
        .otherwise(pl.lit(None))
    )
    return expr


def retrievalBlocks(stockCode: str) -> pl.DataFrame:
    """종목의 전 기간 블록을 semantic/detail topic과 우선순위가 부여된 검색용 DataFrame으로 생성한다.

    Args:
        stockCode: 인자.

    Raises:
        없음.

    Example:
        >>> retrievalBlocks(...)

    Returns:
        pl.DataFrame — retrievalBlocks 결과.

    SeeAlso:
        - ``views.py`` / ``viewsContext`` — 분할 모듈.

    Requires:
        - dartlab
        - polars

    Capabilities:
        - sections retrieval 뷰 빌더 — semantic topic + detail expr + retrievalBlocks DataFrame.

    Guide:
        - 사용자 API 는 ``c.retrievalBlocks`` — 본 모듈 직접 호출 X.

    AIContext:
        internal retrieval view — AI 직접 호출 X.

    LLM Specifications:
        AntiPatterns:
            - 본 모듈 직접 호출 X — sections retrievalBlocks 분리.
        OutputSchema:
            - pl.DataFrame / pl.Expr — 함수별.
        Prerequisites:
            - sections wide DataFrame.
        Freshness:
            - sections 갱신 시점.
        Dataflow:
            - sections → semantic topic 분류 + 우선순위 → retrievalBlocks DataFrame.
        TargetMarkets:
            - KR (DART) retrieval 뷰.
    """
    # 1단계: Python에서 split까지 처리 → 컬럼별 리스트 (가장 빠른 경로)
    cPeriod: list[str] = []
    cPeriodOrder: list[int] = []
    cSectionOrder: list[int] = []
    cRawTitle: list[str] = []
    cTopic: list[str] = []
    cBlockIdx: list[int] = []
    cBlockType: list[str] = []
    cBlockLabel: list[str] = []
    cBlockText: list[str] = []
    cTableLines: list[int] = []

    # 순환 import 회피 — views.py 의 normalizeTitle/splitMarkdownBlocks 를 retrieval 진입 시 lazy.
    from dartlab.providers.dart.docs.sections.views import normalizeTitle, splitMarkdownBlocks

    for period, _reportKind, ccol, subset in iterPeriodSubsets(stockCode):
        pOrder = periodOrderValue(period)
        for record in subset.to_dicts():
            rawTitle = normalizeTitle(str(record["section_title"] or ""))
            if not rawTitle:
                continue
            topic = mapSectionTitle(rawTitle)
            content = str(record[ccol] or "")
            sOrder = int(record["section_order"])
            for block in splitMarkdownBlocks(content):
                cPeriod.append(period)
                cPeriodOrder.append(pOrder)
                cSectionOrder.append(sOrder)
                cRawTitle.append(rawTitle)
                cTopic.append(topic)
                cBlockIdx.append(int(block["blockIdx"]))
                cBlockType.append(str(block["blockType"]))
                cBlockLabel.append(str(block["blockLabel"]))
                cBlockText.append(str(block["blockText"]))
                cTableLines.append(int(block["tableLines"]))

    if not cPeriod:
        return pl.DataFrame()

    # 2단계: DataFrame 생성 + 벡터 연산만 (Polars 네이티브)
    df = pl.DataFrame(
        {
            "stockCode": pl.Series([stockCode] * len(cPeriod), dtype=pl.Utf8),
            "period": cPeriod,
            "periodOrder": cPeriodOrder,
            "sectionOrder": cSectionOrder,
            "rawTitle": cRawTitle,
            "topic": cTopic,
            "blockIdx": cBlockIdx,
            "blockType": cBlockType,
            "blockLabel": cBlockLabel,
            "blockText": cBlockText,
            "tableLines": cTableLines,
        }
    )

    # 벡터 연산
    df = df.with_columns(
        [
            pl.col("rawTitle").alias("sourceTopic"),
            pl.concat_str([pl.lit(stockCode + ":"), pl.col("period"), pl.lit(":"), pl.col("topic")]).alias("cellKey"),
            pl.col("blockText").str.len_chars().alias("chars"),
            pl.col("topic").is_in(_BOILERPLATE_SET).alias("isBoilerplate"),
        ]
    )

    phExpr = pl.lit(False)
    for phrase in _PLACEHOLDER_PHRASES:
        phExpr = phExpr | pl.col("blockText").str.contains(phrase, literal=True)
    df = df.with_columns(phExpr.alias("isPlaceholder"))

    df = df.with_columns(
        [
            _buildSemanticExpr().alias("semanticTopic"),
            _buildDetailExpr().alias("detailTopic"),
        ]
    )

    df = df.with_columns(
        pl.when(pl.col("isBoilerplate") | pl.col("isPlaceholder"))
        .then(0)
        .when(pl.col("detailTopic").is_not_null())
        .then(5)
        .when(pl.col("semanticTopic").is_not_null())
        .then(4)
        .when(pl.col("blockType") == "text")
        .then(3)
        .when(pl.col("blockType") == "heading")
        .then(2)
        .otherwise(1)
        .alias("blockPriority"),
    )

    return df.select(
        [
            "stockCode",
            "period",
            "periodOrder",
            "sectionOrder",
            "rawTitle",
            "topic",
            "sourceTopic",
            "cellKey",
            "blockIdx",
            "blockType",
            "blockLabel",
            "blockText",
            "chars",
            "tableLines",
            "semanticTopic",
            "detailTopic",
            "isBoilerplate",
            "isPlaceholder",
            "blockPriority",
        ]
    ).sort(
        ["periodOrder", "blockPriority", "sectionOrder", "blockIdx"],
        descending=[True, True, False, False],
    )
