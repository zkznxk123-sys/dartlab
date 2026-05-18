---
id: "engines.analysis.valuation"
title: "Analysis - 가치평가"
kind: curated
scope: builtin
status: observed
category: engines
purpose: "analysis 엔진의 가치평가 축 응용 — 이 회사의 적정 가치는 얼마인가."
whenToUse:
  - 가치평가
  - valuation
  - 적정가
  - 목표가
  - DCF
  - DDM
  - RIM
  - PER
  - PBR
  - PSR
  - 멀티플
  - 적정 시가총액
  - relative value
inputs:
  - Company 또는 종목코드
  - 기준 기간
  - 할인율 / 성장률 가정 (overrides)
outputs:
  - 축별 dict (valuationSummary · targetPrice · relativeValue · dcf · ddm · rim · sensitivity)
  - evidence refs
  - 가정 표 (할인율 · 성장률 · 베타 · 영구성장률)
  - 민감도 표
capabilityRefs:
  - "analysis"
  - "Company.analysis"
knowledgeRefs:
  - "engines.analysis"
  - "engines.company"
  - "engines.data.foundation"
sourceRefs:
  - "dartlab://skills/engines.analysis.valuation"
requiredEvidence:
  - "target"
  - "period"
  - "metric"
  - "tableRef"
  - "valueRef"
  - "dateRef"
  - "executionRef"
expectedOutputs:
  - "공개 호출"
  - "대표 반환 형태"
  - "검증 결과"
runtimeCompatibility:
  server:
    status: supported
  localPython:
    status: supported
  mcp:
    status: supported
  webAi:
    status: supported
  pyodide:
    status: limited
forbidden:
  - 근거 없는 숫자를 만들지 않는다.
  - 결손값을 0 으로 채우지 않는다.
  - 단일 axis 결과를 최종 투자 결론으로 제시하지 않는다.
  - DCF 할인율·성장률·영구성장률 가정 ref 없이 적정가 단정 금지.
  - 산업별 멀티플 차이 무시 금지 (제조 PER 평균 vs 금융 PBR 평균 vs 바이오 PSR 평균).
  - 단일 멀티플 (PER) 만으로 적정가 결론 금지 — DCF + 멀티플 + RIM 교차 검증.
failureModes:
  - 가정 (할인율 · 성장률) ref 없이 DCF 결과 인용
  - peer 멀티플 비교 시 같은 산업 분기 미적용 (제조사 vs 금융사 PER 단순 비교)
  - 바이오/플랫폼 같은 적자 회사에 PER 적용 (PSR 또는 EV/Sales 권장)
  - 지주회사에 단일 회사 DCF 적용 (NAV 기반 SOTP 권장)
  - 영구성장률 g 가 명목 GDP 성장률 초과 (수학적으로 비현실적)
  - sensitivity 표 없이 단일 적정가 — 가정 한 변수 흔들림에 취약
examples:
  - 삼성전자 적정 가치 산출
  - DCF 가치평가 + 민감도
  - PER PBR 멀티플 비교
  - 산업 평균 PER 대비 위치
  - 신한지주 PBR 기반 평가 (금융사 — PER 아님)
  - 영구성장률 가정에 따른 적정가 변동
linkedSkills:
  - engines.quant.damodaranValuation
  - engines.analysis.valuationBand
  - engines.analysis.profitability
  - engines.analysis.growth
  - engines.scan.valuation
source:
  type: manual_skill
  format: markdown
lastUpdated: '2026-05-07'
---

## 엔진 역할

analysis 엔진의 가치평가 축 응용 skill — 이 회사의 적정 가치는 얼마인가. SSOT 는 `_AXIS_REGISTRY` (`src/dartlab/analysis/financial/__init__.py`).

## 공개 호출 방식

```python
import dartlab

c = dartlab.Company("005930")

# 1. 가이드 확인 (선택)
c.analysis()

# 2. 실제 axis 실행
result = c.analysis("valuation", "가치평가")

# 3. 모듈 함수형 (대안)
result = dartlab.analysis("valuation", "가치평가", company=c)
```

## 호출 동작

Company 의 finance/disclosure/market snapshot 을 읽어 가치평가 축 계산 항목을 산출한다. 결손 값은 0 으로 채우지 않고 `flags`, `assumptions`, `dataAsOf`, 빈 history, null 로 표현한다. 자세한 동작은 base SKILL `engines.analysis` 의 `## 호출 동작` 참조.

## 대표 반환 형태 — 14 top-level keys

`c.analysis("valuation", "가치평가")` 1 회 호출 결과 dict 의 핵심 키 (값 그대로 답변에 인용 — 추가 호출 불필요):

| key | 의미 | 답변 활용 |
| --- | --- | --- |
| `dcfValuation` | DCF 결과 (`perShareValue` · `enterpriseValue` · `discountRate` · `growthRateInitial` · `terminalGrowth` · `fcfProjections[5]` · `marginOfSafety`) | DCF 적정가 단일값 + 가정 |
| `relativeValuation` | 멀티플 결과 (`sectorMultiples` · `currentMultiples` · `impliedValues` · `premiumDiscount` · `consensusValue` · `warnings`) | PER/PBR/EV-EBITDA/PSR 비교 표 |
| `residualIncome` | RIM (`perShareValue` · `bps` · `costOfEquity`) | 잔여이익 적정가 |
| `ddmValuation` | DDM (`perShareValue` · `dps` · `dividendGrowth` · `discountRate`) | 배당할인 적정가 |
| `priceTarget` | 시나리오 가격 (`weightedTarget` · `percentiles` p10/p25/p50/p75/p90 · `expectedValue` · `upside` · `signal` (strong_sell/sell/hold/buy/strong_buy) · `scenarios[]`) | 시나리오 가격 목표 + 신호 |
| `valuationSynthesis` | 종합 가중 (`fairValueRange` · `verdict` (고평가/저평가/적정) · `weightedFairValue` · `modelWeights` · `estimates[]` · `companyType` (growth/cyclical/value/...)) | 결론 1 줄 + 4 방법론 가중 표 |
| `plausibilityBand` | peer 그룹 위치 (`growthPercentile` · `marginPercentile` · `band` (within/above/below) · `peerStats`) | 적정가 신뢰성 sanity check |
| `lifeCycle` | 라이프사이클 (`phase` (matureGrowth/matureStable/decline/...) · `phaseConfidence` · `modelHint` (dcf/ddm/relative)) | 어느 방법론이 가장 적합한지 힌트 |
| `sensitivity` | WACC × 영구성장률 표 | DCF 가정 민감도 |
| `reverseImplied` | 역산 (`impliedGrowthRate`) | 현재가가 함의하는 성장률 |
| `cashFlowConsistency` | OCF/순이익 비율 | 이익품질 sanity |
| `valuationFlags` · `valuationSins` | 가치평가 경고 | 답변 한계 섹션 |
| `storyPrecedents` | 유사 종목 선례 | peer 인사이트 |
| `assumptions` | 가정 dict (`wacc` · `terminalGrowth` · `growthRates` · `confidence` · `primaryModel`) | 답변 본문에 가정 명시 |

공통 evidence: `tableRef` / `valueRef` / `dateRef` / `executionRef`.

## 답변 양식 (4 방법론 + 시나리오 + 종합)

답변 구조:

1. **결론** (1 문장) — `valuationSynthesis.verdict` + `weightedFairValue` + 현재가 비교 (`signal`).
2. **4 방법론 표** — DCF / 상대가치 / RIM / DDM 적정가 + 비중 (`modelWeights`) + 핵심 가정 (DCF=WACC·g·FCF / 멀티플=배수 / RIM=COE·BPS / DDM=DPS·growth).
3. **시나리오 가격 목표** — `priceTarget.percentiles` p10/p50/p90 + `expectedValue` + `signal`.
4. **DCF 정규화 경고** — `relativeValuation.warnings` 또는 `valuationFlags` ("최근 대비 기준 FCF 가 N 배 괴리" 류) 그대로 인용. 사이클 기업은 mid-cycle FCF 사용 사실 명시.
5. **plausibility band** — `band` (within/above/below) + peer percentile 로 적정가 sanity check.
6. **lifeCycle modelHint** — 어느 방법론에 가중치 더 줄지 (예: matureGrowth → DCF 우위 / growth → 상대가치 우위).
7. **반례·한계** — `assumptions.confidence` + `valuationFlags` + 현재가 snapshot 기준 (실시간 시장가 비교 별도 필요 명시).

## 기본 실행 순서

1. 대상 (종목코드) 확정.
2. `Company.show("IS")` 1 회 → 헤더 chip (dcrBadge + industryBadge) + dataAsOf 확보.
3. `c.analysis("valuation", "가치평가")` 1 회 → 14 keys 결과 — **이 1 회로 4 방법론 + 시나리오 + 가중 적정가 + plausibility band 다 답 가능**. 추가 EngineCall 금지 (DCF/멀티플 별도 호출 안 됨).
4. `assumptions.confidence` 가 `low` 면 valuationFlags 한계 강화.
5. 답변 본문에 14 keys 의 값 그대로 인용 + 4 방법론 표 + priceTarget 시나리오.

## 기본 검증

이 skill 은 공개 실행 문서다. 본 axis 호출 방식, 대표 반환 키, 오류/제한 동작이 변경되면 같은 변경에서 본 파일을 갱신한다. SSOT 는 `_AXIS_REGISTRY` (`src/dartlab/analysis/financial/__init__.py`).
