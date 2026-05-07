---
id: engines.recipe.companyDeepAnalysis
title: 회사 종합 분석 (매크로 → 산업 → 회사 → 분해 → quality → valuation)
category: engines
kind: recipe
scope: builtin
status: unverified
purpose: 단일 회사의 깊이 있는 분석을 매크로 환경, 산업 위치, 회사 본질, ROE 분해, 회계 quality, 가치평가 6 단으로 엮는 절차. 마지막 valuation 단계 누락 시 종합 분석 미완료. 트리거 — '기업 깊이 분석', '6 막 종합', '단일 종목 deep dive'.
whenToUse:
  - 회사 종합 분석
  - 깊이 있는 회사 분석
  - 매크로와 회사를 같이 보고 싶을 때
  - 회사 분석 종합 보고서
  - 종목 깊이 분석
linkedSkills:
  - engines.macro.marketReview
  - engines.analysis.peerComparison
  - engines.scan.profitability
  - engines.company.researchStarter
  - engines.analysis.profitability
  - engines.analysis.earningsQuality
  - engines.analysis.valuation
  - engines.analysis.valuationBand
toolRefs:
  - engine_call
  - run_python
requiredEvidence:
  - skillRef
  - tableRef
  - valueRef
  - dateRef
runtimeCompatibility:
  server:
    status: supported
  localPython:
    status: supported
  pyodide:
    status: limited
    limitations:
      - browser 안에서는 macro/scan dataset snapshot 범위 한정
lastUpdated: '2026-05-07'
---

## 공개 호출 방식

```python
import dartlab

# 회사 진입
c = dartlab.Company("005930")

# 6 단 절차: 매크로 → peer → 회사 → 분해 → quality → valuation
macro = dartlab.macro()
peers = dartlab.scan("profitability")
bs = c.show("BS")
ratios = c.ratios
roe_decomp = c.analysis("financial", "수익성")
quality = c.analysis("financial", "이익품질")
valuation = c.analysis("가치평가", "가치평가")
```

## 호출 동작

각 step 은 독립 capability 호출이며 실패해도 다음 step 은 진행한다. 단계마다 ref 가 누적된다.

1. `dartlab.macro()` — 금리·환율·경기 사이클 한 시점 (datasetRef + tableRef)
2. `dartlab.scan("profitability")` — peer 5~10 후보 (tableRef)
3. `Company(code).show("BS")`/`show("IS")` — 재무제표 시계열 (tableRef + dateRef)
4. `Company.analysis("financial", "수익성")` — ROE DuPont 분해 (valueRef × N)
5. `Company.analysis("financial", "이익품질")` — 회계 quality (valueRef × N)
6. `Company.analysis("가치평가", "가치평가")` — PER·PBR·EV/EBITDA peer 비교 (valueRef × N + tableRef). 종합 분석에서 가치평가 단계 누락 = 미완료. peer 비교 없는 절대값 단독 노출 금지.

## 대표 반환 형태

총 ref:
- `tableRef` 5 개 (macro snapshot, peer scan, BS, IS, valuation peer multiple)
- `valueRef` 9+ 개 (ROE, 마진, 회전, 레버리지, 현금흐름 quality, 일회성 비중, PER, PBR, EV/EBITDA)
- `dateRef` 1 개 (분기 기준일)

## 연계 절차

1. engines.macro.marketReview — 매크로 환경 (금리·환율·경기 사이클)
2. engines.scan.profitability — peer 후보 5~10 (수익성 축)
3. engines.company.researchStarter — 회사 진입 + show("BS") + show("IS")
4. engines.analysis.profitability — ROE DuPont 분해 (마진 × 회전 × 레버리지)
5. engines.analysis.earningsQuality — 일회성·발생주의 점검
6. engines.analysis.valuation — PER/PBR/EV-EBITDA + peer 비교 (가치평가 axis)

## 기본 검증

- 답변에 숫자가 들어가면 valueRef 또는 tableRef 묶음 필수.
- 분기 기준은 dateRef 명시.
- peer 비교는 tableRef + 답변 본문에 evidence table 동시 노출.
- "12 조" 같은 절대값 단독 노출 금지 — peer median / 5 년 평균과 함께.
