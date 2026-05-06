---
id: engines.recipe.creditDeepDive
title: 신용 위험 deep-dive (credit + 재무 안정성 + 매크로 금리)
category: engines
kind: recipe
scope: builtin
status: unverified
purpose: 단일 회사의 신용 위험을 dCR 등급 + 재무 안정성/현금흐름 분해 + 매크로 금리 환경 3 단으로 종합 평가하는 절차.
whenToUse:
  - 신용 위험 분석
  - 부도 가능성 평가
  - dCR 등급 종합
  - 채권 투자 검토
  - 부채 상환 능력
  - 신용 등급 변화 점검
linkedSkills:
  - engines.company.researchStarter
  - engines.credit.creditRisk
  - engines.analysis.stability
  - engines.analysis.cashflow
  - engines.macro.rates
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
      - browser 안에서는 macro 시계열 일부 한정
lastUpdated: '2026-05-06'
---

## 공개 호출 방식

```python
import dartlab

c = dartlab.Company("005930")

credit = c.credit(detail=True)
stability = c.analysis("financial", "안정성")
cashflow = c.analysis("financial", "현금흐름")
rates = dartlab.macro("rates")
```

## 호출 동작

dCR 등급 + 7 축 위험 점수 → 안정성 + 현금흐름 분해 → 매크로 금리 환경 3 층 결합으로 종합 신용 의견. 매크로 금리 변동 시 sensitivity 도 같이 본다.

1. 회사 진입
2. credit(detail=True) — dCR 등급 + 7 축 분해 + metricsHistory
3. analysis("financial", "안정성") — 부채비율·이자보상배율·유동비율
4. analysis("financial", "현금흐름") — CFO·FCF·OCF/부채 비율
5. macro("rates") — 현재 금리 환경

## 대표 반환 형태

- `tableRef` 4 개 (credit metricsHistory + 안정성 표 + 현금흐름 표 + 금리 시계열)
- `valueRef` 5+ (dCR grade + 7 축 점수 + ICR + OCF/부채 + 시나리오스트레스)
- `dateRef` 1 개 (분석 기준 시점)

## 연계 절차

1. engines.company.researchStarter — 회사 진입
2. engines.credit.creditRisk — dCR 종합 + 7 축 (detail=True)
3. engines.analysis.stability — 안정성 분해
4. engines.analysis.cashflow — 현금흐름 quality
5. engines.macro.rates — 금리 환경 + 회사 elasticity

## 기본 검증

- dCR 등급 명시 (예: dCR-AA / dCR-BBB) + 점수 (0~10) 함께.
- 시나리오 스트레스 (overrides 적용) 결과는 가정 명시.
- 금리 +100bp 시 ICR 변동 추정 — historic 데이터 뒷받침 필수.
