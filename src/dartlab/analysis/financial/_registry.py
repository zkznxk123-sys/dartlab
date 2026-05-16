"""Analysis financial 축 레지스트리 — 14축 + 그룹 + alias + axis 해석.

내부 모듈. 외부는 `dartlab.analysis.financial.Analysis` 만 import.

분리 이유: financial/__init__.py 가 1325 줄. 14축 레지스트리 + GROUPS + ALIASES
가 670 줄 차지. facade (Analysis class) 와 데이터 정의를 분리해 진입점 모듈을
가볍게 유지한다.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# ── 분석 항목 레지스트리 ──


@dataclass(frozen=True)
class _CalcEntry:
    """개별 calc* 함수 메타."""

    fn: str
    module: str
    blockKey: str
    label: str


@dataclass(frozen=True)
class _AxisEntry:
    """분석 축 메타."""

    section: str
    partId: str
    description: str
    example: str
    calcs: tuple[_CalcEntry, ...] = field(default_factory=tuple)


# ── 15축 레지스트리 ──
# catalog.py SECTIONS + _BLOCKS + registry.py buildBlocks()에서 매핑.

_AXIS_REGISTRY: dict[str, _AxisEntry] = {
    "수익구조": _AxisEntry(
        section="수익구조",
        partId="1-1",
        description="이 회사는 무엇으로 돈을 버는가",
        example='analysis("financial", "수익구조")',
        calcs=(
            _CalcEntry("calcCompanyProfile", "dartlab.analysis.financial.revenue", "profile", "기업 개요"),
            _CalcEntry(
                "calcSegmentComposition", "dartlab.analysis.financial.revenue", "segmentComposition", "부문별 매출 구성"
            ),
            _CalcEntry("calcSegmentTrend", "dartlab.analysis.financial.revenue", "segmentTrend", "부문별 매출 추이"),
            _CalcEntry("calcRevenueGrowth", "dartlab.analysis.financial.revenue", "growth", "매출 성장률"),
            _CalcEntry(
                "calcGrowthContribution", "dartlab.analysis.financial.revenue", "growthContribution", "성장 기여 분해"
            ),
            _CalcEntry("calcConcentration", "dartlab.analysis.financial.revenue", "concentration", "매출 집중도"),
            _CalcEntry("calcRevenueQuality", "dartlab.analysis.financial.revenue", "revenueQuality", "매출 품질"),
            _CalcEntry("calcFlags", "dartlab.analysis.financial.revenue", "revenueFlags", "수익구조 플래그"),
        ),
    ),
    "자금조달": _AxisEntry(
        section="자금조달",
        partId="1-2",
        description="돈을 어디서 조달하는가",
        example='analysis("financial", "자금조달")',
        calcs=(
            _CalcEntry("calcFundingSources", "dartlab.analysis.financial.capital", "fundingSources", "자금 원천 구성"),
            _CalcEntry(
                "calcCapitalOverview", "dartlab.analysis.financial.capital", "capitalOverview", "자본 구조 개요"
            ),
            _CalcEntry(
                "calcCapitalTimeline", "dartlab.analysis.financial.capital", "capitalTimeline", "자본 구조 추이"
            ),
            _CalcEntry("calcDebtTimeline", "dartlab.analysis.financial.capital", "debtTimeline", "부채 추이"),
            _CalcEntry("calcInterestBurden", "dartlab.analysis.financial.capital", "interestBurden", "이자 부담"),
            _CalcEntry("calcLiquidity", "dartlab.analysis.financial.capital", "liquidity", "유동성"),
            _CalcEntry(
                "calcCashFlowStructure", "dartlab.analysis.financial.capital", "cashFlowStructure", "자금흐름 구조"
            ),
            _CalcEntry(
                "calcDistressIndicators", "dartlab.analysis.financial.capital", "distressIndicators", "재무 위험 지표"
            ),
            _CalcEntry("calcCapitalFlags", "dartlab.analysis.financial.capital", "capitalFlags", "자금조달 플래그"),
        ),
    ),
    "자산구조": _AxisEntry(
        section="자산구조",
        partId="1-3",
        description="조달한 돈으로 뭘 준비했는가",
        example='analysis("financial", "자산구조")',
        calcs=(
            _CalcEntry("calcAssetStructure", "dartlab.analysis.financial.asset", "assetStructure", "자산 재분류"),
            _CalcEntry("calcWorkingCapital", "dartlab.analysis.financial.asset", "workingCapital", "운전자본 순환"),
            _CalcEntry("calcCapexPattern", "dartlab.analysis.financial.asset", "capexPattern", "CAPEX 패턴"),
            _CalcEntry("calcAssetFlags", "dartlab.analysis.financial.asset", "assetFlags", "자산구조 플래그"),
        ),
    ),
    "현금흐름": _AxisEntry(
        section="현금흐름",
        partId="1-4",
        description="실제로 현금은 어떻게 흘렀는가",
        example='analysis("financial", "현금흐름")',
        calcs=(
            _CalcEntry(
                "calcCashFlowOverview", "dartlab.analysis.financial.cashflow", "cashFlowOverview", "현금흐름 종합"
            ),
            _CalcEntry("calcCashQuality", "dartlab.analysis.financial.cashflow", "cashQuality", "이익의 현금 전환"),
            _CalcEntry("calcCashFlowFlags", "dartlab.analysis.financial.cashflow", "cashFlowFlags", "현금흐름 플래그"),
            _CalcEntry(
                "calcOcfDecomposition",
                "dartlab.analysis.financial.cashflow",
                "ocfDecomposition",
                "영업CF 분해 (NI+감가+운전자본)",
            ),
        ),
    ),
    "수익성": _AxisEntry(
        section="수익성",
        partId="2-1",
        description="이 회사는 얼마나 잘 벌고 있는가",
        example='analysis("financial", "수익성")',
        calcs=(
            _CalcEntry("calcMarginTrend", "dartlab.analysis.financial.profitability", "marginTrend", "마진 추이"),
            _CalcEntry(
                "calcReturnTrend", "dartlab.analysis.financial.profitability", "returnTrend", "ROE 분해 (듀퐁 5요소)"
            ),
            _CalcEntry(
                "calcMarginWaterfall", "dartlab.analysis.financial.profitability", "marginWaterfall", "마진 워터폴"
            ),
            _CalcEntry(
                "calcProfitabilityFlags",
                "dartlab.analysis.financial.profitability",
                "profitabilityFlags",
                "수익성 플래그",
            ),
            _CalcEntry(
                "calcPenmanDecomposition",
                "dartlab.analysis.financial.profitability",
                "penmanDecomposition",
                "Penman 분해 (RNOA vs 레버리지)",
            ),
            _CalcEntry(
                "calcRoicTree",
                "dartlab.analysis.financial.profitability",
                "roicTree",
                "ROIC Tree (마진×회전 분해)",
            ),
        ),
    ),
    "성장성": _AxisEntry(
        section="성장성",
        partId="2-2",
        description="이 회사는 얼마나 빨리 성장하는가",
        example='analysis("financial", "성장성")',
        calcs=(
            _CalcEntry("calcGrowthTrend", "dartlab.analysis.financial.growthAnalysis", "growthTrend", "성장률 추이"),
            _CalcEntry("calcGrowthQuality", "dartlab.analysis.financial.growthAnalysis", "growthQuality", "성장 품질"),
            _CalcEntry(
                "calcSustainableGrowthRate",
                "dartlab.analysis.financial.growthAnalysis",
                "sustainableGrowthRate",
                "지속가능성장률",
            ),
            _CalcEntry("calcGrowthFlags", "dartlab.analysis.financial.growthAnalysis", "growthFlags", "성장성 플래그"),
            _CalcEntry(
                "calcCagrComparison",
                "dartlab.analysis.financial.growthAnalysis",
                "cagrComparison",
                "CAGR 비교 (구조적 변화 감지)",
            ),
        ),
    ),
    "안정성": _AxisEntry(
        section="안정성",
        partId="2-3",
        description="이 회사는 망하지 않는가",
        example='analysis("financial", "안정성")',
        calcs=(
            _CalcEntry("calcLeverageTrend", "dartlab.analysis.financial.stability", "leverageTrend", "레버리지 추이"),
            _CalcEntry("calcCoverageTrend", "dartlab.analysis.financial.stability", "coverageTrend", "이자보상 추이"),
            _CalcEntry("calcDistressScore", "dartlab.analysis.financial.stability", "distressScore", "부실 판별"),
            _CalcEntry(
                "calcDistressEnsemble", "dartlab.analysis.financial.stability", "distressEnsemble", "부실예측 앙상블"
            ),
            _CalcEntry("calcDebtMaturity", "dartlab.analysis.financial.stability", "debtMaturity", "부채 만기 구조"),
            _CalcEntry("calcStabilityFlags", "dartlab.analysis.financial.stability", "stabilityFlags", "안정성 플래그"),
        ),
    ),
    "효율성": _AxisEntry(
        section="효율성",
        partId="2-4",
        description="이 회사는 자산을 잘 굴리는가",
        example='analysis("financial", "효율성")',
        calcs=(
            _CalcEntry(
                "calcTurnoverTrend", "dartlab.analysis.financial.efficiency", "turnoverTrend", "회전율 + CCC 추이"
            ),
            _CalcEntry(
                "calcEfficiencyFlags", "dartlab.analysis.financial.efficiency", "efficiencyFlags", "효율성 플래그"
            ),
        ),
    ),
    "종합평가": _AxisEntry(
        section="종합평가",
        partId="2-5",
        description="재무 상태를 한마디로",
        example='analysis("financial", "종합평가")',
        calcs=(
            _CalcEntry("calcScorecard", "dartlab.analysis.financial.scorecard", "scorecard", "재무 스코어카드"),
            _CalcEntry("calcPiotroskiDetail", "dartlab.analysis.financial.scorecard", "piotroski", "Piotroski F-Score"),
            _CalcEntry("calcSummaryFlags", "dartlab.analysis.financial.scorecard", "summaryFlags", "종합 플래그"),
        ),
    ),
    "이익품질": _AxisEntry(
        section="이익품질",
        partId="3-1",
        description="이익이 진짜인가",
        example='analysis("financial", "이익품질")',
        calcs=(
            _CalcEntry(
                "calcAccrualAnalysis", "dartlab.analysis.financial.earningsQuality", "accrualAnalysis", "발생액 분석"
            ),
            _CalcEntry(
                "calcEarningsPersistence",
                "dartlab.analysis.financial.earningsQuality",
                "earningsPersistence",
                "이익 지속성",
            ),
            _CalcEntry(
                "calcBeneishTimeline", "dartlab.analysis.financial.earningsQuality", "beneishMScore", "Beneish M-Score"
            ),
            _CalcEntry(
                "calcEarningsQualityFlags",
                "dartlab.analysis.financial.earningsQuality",
                "earningsQualityFlags",
                "이익품질 플래그",
            ),
            _CalcEntry(
                "calcQualityAnomalies",
                "dartlab.analysis.financial.earningsQuality",
                "qualityAnomalies",
                "Phase 7 — Damodaran Ch.4 회계 품질 이상치 (Beneish + Sloan + 5 카테고리 + 감사보고서 docs)",
            ),
            _CalcEntry(
                "calcRichardsonAccrual",
                "dartlab.analysis.financial.earningsQuality",
                "richardsonAccrual",
                "Richardson 3계층 발생액",
            ),
            _CalcEntry(
                "calcNonOperatingBreakdown",
                "dartlab.analysis.financial.earningsQuality",
                "nonOperatingBreakdown",
                "영업외손익 분해",
            ),
        ),
    ),
    "비용구조": _AxisEntry(
        section="비용구조",
        partId="3-2",
        description="비용이 어떻게 움직이는가",
        example='analysis("financial", "비용구조")',
        calcs=(
            _CalcEntry(
                "calcCostBreakdown", "dartlab.analysis.financial.costStructure", "costBreakdown", "비용 비중 분해"
            ),
            _CalcEntry(
                "calcOperatingLeverage", "dartlab.analysis.financial.costStructure", "operatingLeverage", "영업레버리지"
            ),
            _CalcEntry(
                "calcBreakevenEstimate", "dartlab.analysis.financial.costStructure", "breakevenEstimate", "손익분기점"
            ),
            _CalcEntry(
                "calcRawMaterialBreakdown",
                "dartlab.analysis.financial.costStructure",
                "rawMaterialBreakdown",
                "원재료 매입 비중",
            ),
            _CalcEntry(
                "calcCostStructureFlags",
                "dartlab.analysis.financial.costStructure",
                "costStructureFlags",
                "비용구조 플래그",
            ),
        ),
    ),
    "자본배분": _AxisEntry(
        section="자본배분",
        partId="3-3",
        description="번 돈을 어디에 쓰는가",
        example='analysis("financial", "자본배분")',
        calcs=(
            _CalcEntry(
                "calcDividendPolicy", "dartlab.analysis.financial.capitalAllocation", "dividendPolicy", "배당 정책"
            ),
            _CalcEntry(
                "calcShareholderReturn", "dartlab.analysis.financial.capitalAllocation", "shareholderReturn", "주주환원"
            ),
            _CalcEntry("calcReinvestment", "dartlab.analysis.financial.capitalAllocation", "reinvestment", "재투자"),
            _CalcEntry("calcFcfUsage", "dartlab.analysis.financial.capitalAllocation", "fcfUsage", "FCF 사용처"),
            _CalcEntry(
                "calcDividendDocs", "dartlab.analysis.financial.capitalAllocation", "dividendDocs", "배당 서술 (docs)"
            ),
            _CalcEntry(
                "calcTreasuryStockStatus",
                "dartlab.analysis.financial.capitalAllocation",
                "treasuryStockStatus",
                "자사주 현황",
            ),
            _CalcEntry(
                "calcCapitalAllocationFlags",
                "dartlab.analysis.financial.capitalAllocation",
                "capitalAllocationFlags",
                "자본배분 플래그",
            ),
        ),
    ),
    "투자효율": _AxisEntry(
        section="투자효율",
        partId="3-4",
        description="투자가 가치를 만드는가",
        example='analysis("financial", "투자효율")',
        calcs=(
            _CalcEntry(
                "calcRoicTimeline", "dartlab.analysis.financial.investmentAnalysis", "roicTimeline", "ROIC 시계열"
            ),
            _CalcEntry(
                "calcInvestmentIntensity",
                "dartlab.analysis.financial.investmentAnalysis",
                "investmentIntensity",
                "투자 강도",
            ),
            _CalcEntry(
                "calcEvaTimeline", "dartlab.analysis.financial.investmentAnalysis", "evaTimeline", "NOPAT + 투하자본"
            ),
            _CalcEntry(
                "calcInvestmentInOther",
                "dartlab.analysis.financial.investmentAnalysis",
                "investmentInOther",
                "타법인 출자 현황",
            ),
            _CalcEntry(
                "calcInvestmentFlags",
                "dartlab.analysis.financial.investmentAnalysis",
                "investmentFlags",
                "투자효율 플래그",
            ),
        ),
    ),
    "재무정합성": _AxisEntry(
        section="재무정합성",
        partId="3-5",
        description="재무제표가 서로 맞는가",
        example='analysis("financial", "재무정합성")',
        calcs=(
            _CalcEntry(
                "calcIsCfDivergence", "dartlab.analysis.financial.crossStatement", "isCfDivergence", "IS-CF 괴리"
            ),
            _CalcEntry(
                "calcIsBsDivergence", "dartlab.analysis.financial.crossStatement", "isBsDivergence", "IS-BS 괴리"
            ),
            _CalcEntry("calcAnomalyScore", "dartlab.analysis.financial.crossStatement", "anomalyScore", "이상 점수"),
            _CalcEntry(
                "calcEffectiveTaxRate", "dartlab.analysis.financial.taxAnalysis", "effectiveTaxRate", "유효세율"
            ),
            _CalcEntry("calcDeferredTax", "dartlab.analysis.financial.taxAnalysis", "deferredTax", "이연법인세"),
            _CalcEntry(
                "calcArticulationCheck",
                "dartlab.analysis.financial.crossStatement",
                "articulationCheck",
                "BS-CF 정합성 검증",
            ),
        ),
    ),
    # 신용평가는 독립 엔진 (c.credit()) — analysis 축에서 제거
    # ── 4부: 가치평가 ──
    "가치평가": _AxisEntry(
        section="가치평가",
        partId="4-1",
        description="이 회사의 적정 가치는 얼마인가",
        example='analysis("valuation", "가치평가")',
        calcs=(
            _CalcEntry("calcDcf", "dartlab.analysis.financial.valuation", "dcfValuation", "DCF 밸류에이션"),
            _CalcEntry("calcDdm", "dartlab.analysis.financial.valuation", "ddmValuation", "DDM 밸류에이션"),
            _CalcEntry(
                "calcRelativeValuation",
                "dartlab.analysis.financial.valuation",
                "relativeValuation",
                "상대가치 (PER/PBR/EV-EBITDA/PSR/PEG)",
            ),
            _CalcEntry(
                "calcResidualIncome", "dartlab.analysis.financial.valuation", "residualIncome", "RIM (잔여이익모델)"
            ),
            _CalcEntry("calcPriceTarget", "dartlab.analysis.financial.valuation", "priceTarget", "확률 가중 목표주가"),
            _CalcEntry("calcReverseImplied", "dartlab.analysis.financial.valuation", "reverseImplied", "역내재성장률"),
            _CalcEntry("calcSensitivity", "dartlab.analysis.financial.valuation", "sensitivity", "민감도 분석"),
            _CalcEntry(
                "calcValuationSynthesis",
                "dartlab.analysis.financial.valuation",
                "valuationSynthesis",
                "종합 적정가치",
            ),
            _CalcEntry(
                "calcValuationFlags", "dartlab.analysis.financial.valuation", "valuationFlags", "가치평가 플래그"
            ),
            _CalcEntry(
                "calcLifeCycle",
                "dartlab.analysis.financial.lifeCycle",
                "lifeCycle",
                "Damodaran 생애주기 단계 판별 (earlyGrowth/highGrowth/matureGrowth/matureStable/decline/turnaround)",
            ),
            _CalcEntry(
                "calcCashFlowConsistency",
                "dartlab.analysis.valuation.consistency",
                "cashFlowConsistency",
                "Damodaran CF 정합성 검증 (g vs reinvest, TV weight, tax)",
            ),
            _CalcEntry(
                "calcStoryPrecedents",
                "dartlab.analysis.financial.storyValidation",
                "storyPrecedents",
                "Possible Test — 과거 유사 기업 사례",
            ),
            _CalcEntry(
                "calcPlausibilityBand",
                "dartlab.analysis.financial.storyValidation",
                "plausibilityBand",
                "Plausible Test — 섹터 피어 분포 대비 위치",
            ),
            _CalcEntry(
                "calcValuationSins",
                "dartlab.analysis.financial.storyValidation",
                "valuationSins",
                "Probable Test — 밸류에이션 정합성 규칙 검증",
            ),
        ),
    ),
    # ── 5부: 비재무 심화 ──
    "지배구조": _AxisEntry(
        section="지배구조",
        partId="5-1",
        description="이 회사의 주인은 누구이며 감시는 작동하는가",
        example='analysis("governance", "지배구조")',
        calcs=(
            _CalcEntry(
                "calcOwnershipTrend", "dartlab.analysis.financial.governance", "ownershipTrend", "최대주주 지분 추이"
            ),
            _CalcEntry(
                "calcBoardComposition", "dartlab.analysis.financial.governance", "boardComposition", "이사회 구성"
            ),
            _CalcEntry(
                "calcAuditOpinionTrend",
                "dartlab.analysis.financial.governance",
                "auditOpinionTrend",
                "감사의견 시계열",
            ),
            _CalcEntry(
                "calcGovernanceFlags", "dartlab.analysis.financial.governance", "governanceFlags", "지배구조 플래그"
            ),
            _CalcEntry(
                "calcLegalEventRisk",
                "dartlab.analysis.financial.governance",
                "legalEventRisk",
                "법적 이벤트 리스크 (제재·소송·채무보증)",
            ),
            _CalcEntry(
                "calcOwnerConcentration",
                "dartlab.analysis.financial.governance",
                "ownerConcentration",
                "오너 집중도 (본인/특수관계 분리)",
            ),
            _CalcEntry(
                "calcRelatedPartyIntensity",
                "dartlab.analysis.financial.governance",
                "relatedPartyIntensity",
                "특수관계자 거래 집중도 (매출·매입·보증)",
            ),
            _CalcEntry(
                "calcCEOTurnover",
                "dartlab.analysis.financial.governance",
                "ceoTurnover",
                "대표이사 교체 시계열",
            ),
        ),
    ),
    "공시변화": _AxisEntry(
        section="공시변화",
        partId="5-2",
        description="이 회사의 공시가 뭐가 달라졌는가",
        example='analysis("governance", "공시변화")',
        calcs=(
            _CalcEntry(
                "calcDisclosureChangeSummary",
                "dartlab.analysis.financial.disclosureDelta",
                "disclosureChangeSummary",
                "공시변화 종합",
            ),
            _CalcEntry(
                "calcKeyTopicChanges",
                "dartlab.analysis.financial.disclosureDelta",
                "keyTopicChanges",
                "핵심 공시 변화",
            ),
            _CalcEntry(
                "calcChangeIntensity",
                "dartlab.analysis.financial.disclosureDelta",
                "changeIntensity",
                "변화 크기 분석",
            ),
            _CalcEntry(
                "calcDisclosureDeltaFlags",
                "dartlab.analysis.financial.disclosureDelta",
                "disclosureDeltaFlags",
                "공시변화 플래그",
            ),
        ),
    ),
    "비교분석": _AxisEntry(
        section="비교분석",
        partId="5-3",
        description="이 회사는 시장에서 어디에 서 있는가",
        example='analysis("governance", "비교분석")',
        calcs=(
            _CalcEntry(
                "calcPeerRanking", "dartlab.analysis.financial.peerBenchmark", "peerRanking", "시장 내 백분위 순위"
            ),
            _CalcEntry(
                "calcRiskReturnPosition",
                "dartlab.analysis.financial.peerBenchmark",
                "riskReturnPosition",
                "수익-위험 포지션",
            ),
            _CalcEntry(
                "calcPeerBenchmarkFlags",
                "dartlab.analysis.financial.peerBenchmark",
                "peerBenchmarkFlags",
                "비교분석 플래그",
            ),
        ),
    ),
    # ── 6부: 전망분석 ──
    "매출전망": _AxisEntry(
        section="매출전망",
        partId="6-1",
        description="이 회사의 매출은 어디로 가며 재무는 어떻게 변하는가",
        example='analysis("forecast", "매출전망")',
        calcs=(
            _CalcEntry(
                "calcRevenueForecast", "dartlab.analysis.financial.forecastCalcs", "revenueForecast", "매출 예측"
            ),
            _CalcEntry(
                "calcSegmentForecast", "dartlab.analysis.financial.forecastCalcs", "segmentForecast", "세그먼트별 전망"
            ),
            _CalcEntry(
                "calcProFormaHighlights",
                "dartlab.analysis.financial.forecastCalcs",
                "proFormaHighlights",
                "Pro-Forma 전망",
            ),
            _CalcEntry(
                "calcScenarioImpact", "dartlab.analysis.financial.forecastCalcs", "scenarioImpact", "시나리오 영향"
            ),
            _CalcEntry(
                "calcForecastMethodology",
                "dartlab.analysis.financial.forecastCalcs",
                "forecastMethodology",
                "예측 방법론",
            ),
            _CalcEntry(
                "calcHistoricalRatios", "dartlab.analysis.financial.forecastCalcs", "historicalRatios", "과거 구조 비율"
            ),
            _CalcEntry(
                "calcForecastFlags", "dartlab.analysis.financial.forecastCalcs", "forecastFlags", "매출전망 플래그"
            ),
            _CalcEntry(
                "calcScenarioSimulation",
                "dartlab.analysis.financial.forecastCalcs",
                "scenarioSimulation",
                "시나리오 시뮬레이션",
            ),
        ),
    ),
    "예측신호": _AxisEntry(
        section="예측신호",
        partId="6-2",
        description="이 회사의 실적은 어디로 향하는가",
        example='analysis("forecast", "예측신호")',
        calcs=(
            _CalcEntry(
                "calcEarningsMomentum",
                "dartlab.analysis.financial.predictionSignals",
                "earningsMomentum",
                "이익 모멘텀",
            ),
            _CalcEntry(
                "calcPeerPrediction",
                "dartlab.analysis.financial.predictionSignals",
                "peerPrediction",
                "횡단면 피어 예측",
            ),
            _CalcEntry(
                "calcStructuralBreak",
                "dartlab.analysis.financial.predictionSignals",
                "structuralBreak",
                "구조변화 감지",
            ),
            _CalcEntry(
                "calcMacroSensitivity",
                "dartlab.analysis.financial.predictionSignals",
                "macroSensitivity",
                "거시경제 민감도",
            ),
            _CalcEntry(
                "calcMacroRegression",
                "dartlab.analysis.financial.predictionSignals",
                "macroRegression",
                "거시-재무 동적 회귀",
            ),
            _CalcEntry(
                "calcEventImpact",
                "dartlab.analysis.financial.predictionSignals",
                "eventImpact",
                "이벤트 충격 분석",
            ),
            _CalcEntry(
                "calcDisclosureDelta",
                "dartlab.analysis.financial.predictionSignals",
                "disclosureDelta",
                "공시 변화 신호",
            ),
            _CalcEntry(
                "calcInventoryDivergence",
                "dartlab.analysis.financial.predictionSignals",
                "inventoryDivergence",
                "재고/매출채권 괴리",
            ),
            _CalcEntry(
                "calcAnnouncementTiming",
                "dartlab.analysis.financial.predictionSignals",
                "announcementTiming",
                "동종업계 공시 타이밍",
            ),
            _CalcEntry(
                "calcSupplyChainSignal",
                "dartlab.analysis.financial.predictionSignals",
                "supplyChainSignal",
                "공급망 모멘텀",
            ),
            _CalcEntry(
                "calcConsensusDirection",
                "dartlab.analysis.financial.predictionSignals",
                "consensusDirection",
                "컨센서스 매출 방향",
            ),
            _CalcEntry(
                "calcFlowDirection",
                "dartlab.analysis.financial.predictionSignals",
                "flowDirection",
                "수급 누적 방향",
            ),
            _CalcEntry(
                "calcRevenueDirection",
                "dartlab.analysis.financial.predictionSignals",
                "revenueDirection",
                "매출 모멘텀 방향",
            ),
            _CalcEntry(
                "calcPredictionSynthesis",
                "dartlab.analysis.financial.predictionSignals",
                "predictionSynthesis",
                "예측 신호 종합",
            ),
            _CalcEntry(
                "calcPredictionFlags",
                "dartlab.analysis.financial.predictionSignals",
                "predictionFlags",
                "예측신호 플래그",
            ),
        ),
    ),
    # ── 6부: 매크로 (기업-매크로 연결만 — 시장 자체 분석은 dartlab.macro() 엔진) ──
    "매크로민감도": _AxisEntry(
        section="매크로민감도",
        partId="6-1",
        description="이 회사의 매출은 어떤 매크로 변수에 민감한가",
        example='analysis("macro", "매크로민감도")',
        calcs=(
            _CalcEntry(
                "calcMacroSensitivity",
                "dartlab.analysis.financial.macroExposure",
                "macroSensitivity",
                "외생변수 회귀 + 매출 방향",
            ),
        ),
    ),
    "밸류에이션밴드": _AxisEntry(
        section="밸류에이션밴드",
        partId="6-2",
        description="PER/PBR이 과거 대비 어디에 있는가",
        example='analysis("macro", "밸류에이션밴드")',
        calcs=(
            _CalcEntry(
                "calcValuationBand",
                "dartlab.analysis.financial.macroExposure",
                "valuationBand",
                "멀티플 정규분포 밴드",
            ),
        ),
    ),
}


# ── Alias ──

# ── 그룹 정의 — analysis("그룹", "하위") 2단계 호출 ──

_GROUPS: dict[str, list[str]] = {
    "financial": [
        "수익구조",
        "자금조달",
        "자산구조",
        "현금흐름",
        "수익성",
        "성장성",
        "안정성",
        "효율성",
        "종합평가",
        "이익품질",
        "비용구조",
        "자본배분",
        "투자효율",
        "재무정합성",
    ],
    "valuation": ["가치평가"],
    "governance": ["지배구조", "공시변화", "비교분석"],
    "forecast": ["매출전망", "예측신호"],
    "macro": ["매크로민감도", "밸류에이션밴드"],
}

# 역매핑: 축 → 소속 그룹
_AXIS_TO_GROUP: dict[str, str] = {}
for _g, _axes in _GROUPS.items():
    for _a in _axes:
        _AXIS_TO_GROUP[_a] = _g

# ── alias — 한글↔영문 양방향 ──

_ALIASES: dict[str, str] = {
    # 영문 → 한글 (축 이름)
    "revenue": "수익구조",
    "revenueStructure": "수익구조",
    "capital": "자금조달",
    "funding": "자금조달",
    "asset": "자산구조",
    "assetStructure": "자산구조",
    "cashflow": "현금흐름",
    "profitability": "수익성",
    "growth": "성장성",
    "stability": "안정성",
    "efficiency": "효율성",
    "scorecard": "종합평가",
    "earningsQuality": "이익품질",
    "costStructure": "비용구조",
    "capitalAllocation": "자본배분",
    "investment": "투자효율",
    "investmentEfficiency": "투자효율",
    "crossStatement": "재무정합성",
    "financialConsistency": "재무정합성",
    "valuation": "가치평가",
    "governance": "지배구조",
    "disclosureDelta": "공시변화",
    "disclosureChange": "공시변화",
    "peerBenchmark": "비교분석",
    "peerComparison": "비교분석",
    "forecast": "매출전망",
    "전망": "매출전망",
    "prediction": "예측신호",
    "predictionSignals": "예측신호",
    "전망신호": "예측신호",
    # macro 그룹 (기업-매크로 연결만 — 시장 분석은 dartlab.macro())
    "macroSensitivity": "매크로민감도",
    "valuationBand": "밸류에이션밴드",
    "민감도": "매크로민감도",
    "멀티플밴드": "밸류에이션밴드",
    # 그룹 alias (한글)
    "재무": "financial",
    "재무분석": "financial",
    "가치": "valuation",
    "지배": "governance",
    "전망분석": "forecast",
    "매크로": "macro",
    "매크로분석": "macro",
}


def _resolveAxis(axis: str) -> str:
    """축 이름 또는 명시 alias → 정규 축 이름.

    consistency_no_alias 원칙: case-insensitive 매칭 ``axis.lower()`` 는 silent
    alias 라 인정하지 않는다. 사용자는 정식 표기 (한글 정식 또는 _ALIASES 의
    명시 매핑) 를 정확히 사용해야 한다.
    """
    if axis in _AXIS_REGISTRY:
        return axis
    if axis in _ALIASES:
        return _ALIASES[axis]
    available = ", ".join(sorted(_AXIS_REGISTRY))
    raise ValueError(
        f"알 수 없는 분석 축: '{axis}'. 가용 축: {available}\n  사용법: c.analysis() 로 전체 축 가이드를 확인하세요."
    )
