---
id: engines.recipe.dividendThesis
title: 배당 thesis (자본배분 + 현금흐름 quality + 배당 정책)
category: engines
kind: recipe
scope: builtin
status: unverified
purpose: 회사의 배당 매력도를 자본배분 의지 + 현금흐름 quality + 과거 배당 정책 3 축으로 평가하는 절차.
whenToUse:
  - 배당 매력 평가
  - 배당주 분석
  - 주주환원 thesis
  - 자사주 매입 분석
  - 배당 지속 가능성
  - 배당 성장률
linkedSkills:
  - engines.company.researchStarter
  - engines.analysis.dividendCapitalReturn
  - engines.analysis.cashflow
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
      - browser 안에서는 dividend topic 단일 호출만
lastUpdated: '2026-05-06'
---

## 공개 호출 방식

```python
import dartlab

c = dartlab.Company("005930")

dividend = c.show("dividend")
capital = c.analysis("financial", "자본배분")
cashflow = c.analysis("financial", "현금흐름")
return_axis = c.analysis("financial", "배당주주환원")
```

## 호출 동작

배당 정책 raw 데이터 → 자본배분 우선순위 (배당 vs CAPEX vs 자사주) → 현금흐름 quality (FCF / 배당 충당 비율) → 주주환원 시계열 종합.

1. 회사 진입
2. show("dividend") — 과거 배당 정책 시계열 + 배당성향
3. analysis("financial", "자본배분") — 자본배분 의지 점수
4. analysis("financial", "현금흐름") — FCF / 배당 충당 비율
5. analysis("financial", "배당주주환원") — 주주환원 종합 (있으면)

## 대표 반환 형태

- `tableRef` 3+ 개 (dividend 정책 + 자본배분 + 현금흐름)
- `valueRef` 4+ (배당성향 % / FCF / 배당지급액 / payout ratio / DPS 성장률)
- `dateRef` 1 개

## 연계 절차

1. engines.company.researchStarter — 회사 진입
2. engines.analysis.dividendCapitalReturn — 배당·자사주 종합
3. engines.analysis.capitalAllocation — 자본배분 의지
4. engines.analysis.cashflow — FCF 가 배당 충당 가능 여부

## 기본 검증

- 배당성향 (%) + DPS 성장률 (%) 명시.
- FCF 가 배당 지급액의 몇 배인지 (충당 배수) 명시.
- 자사주 매입이 있으면 배당 + 자사주 합산 주주환원율 함께.
- "배당 지속 가능" 같은 단정 X — 과거 N 년 + 가정 + 시나리오 명시.
