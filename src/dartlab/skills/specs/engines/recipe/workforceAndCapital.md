---
id: engines.recipe.workforceAndCapital
title: 인력·자본 사이클 (workforce + capital + 자본배분)
category: engines
kind: recipe
scope: builtin
status: unverified
purpose: 회사의 인력 (직원수·인건비·생산성) 과 자본 (배당·자사주·신주) 사이클을 결합해 자원 배분 전략을 분석하는 절차.
whenToUse:
  - 인력 분석
  - 직원 수
  - 인건비
  - 자본 사이클
  - 자본 배분
  - 자사주 신주
  - workforce
  - capital allocation
linkedSkills:
  - engines.company.researchStarter
  - engines.scan.workforce
  - engines.scan.capital
  - engines.analysis.capitalAllocation
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
      - browser 안에서는 docs 일부 한정
lastUpdated: '2026-05-06'
---

## 공개 호출 방식

```python
import dartlab

c = dartlab.Company("005930")

workforce = c.workforce()
capital = c.capital()
allocation = c.analysis("financial", "자본배분")
```

## 호출 동작

인력 변화 + 자본 변동 + 자본배분 의지 종합. 인력 효율성 (매출/직원수) + 자본 효율성 (CAPEX/매출) 양쪽 확인.

1. 회사 진입
2. workforce() — 직원 수 + 인건비 시계열
3. capital() — 자본 변동 (자사주 / 신주 / 배당)
4. analysis("financial", "자본배분") — 자본배분 우선순위

## 대표 반환 형태

- `tableRef` 3 개 (workforce + capital + allocation)
- `valueRef` 4+ (직원수 / 매출당 직원 / CAPEX / FCF)
- `dateRef` 1 개

## 연계 절차

1. engines.company.researchStarter — 회사 진입
2. engines.scan.workforce — 인력 횡단
3. engines.scan.capital — 자본 변동 횡단
4. engines.analysis.capitalAllocation — 배분 의지

## 기본 검증

- 인력 효율성 = 매출 / 직원수 (시계열).
- 자본 사이클 = CAPEX vs FCF 균형.
- "효율적" 단정 X — peer 평균 + 산업 표준 함께.
