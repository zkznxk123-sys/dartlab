"""_AXIS_REGISTRY 부분 B — 4~6 부 (가치평가 ~ 밸류에이션밴드)."""

from __future__ import annotations

from dartlab.analysis.financial._registryTypes import _AxisEntry, _CalcEntry

_AXES_B: dict[str, _AxisEntry] = {
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
