---
id: engines.credit.creditRisk
title: 신용위험 분석 (Company.credit 응용)
category: engines
kind: curated
status: observed
purpose: Company.credit + 재무 snapshot 으로 신용 위험 정량 산출 — leverage / interestCoverage / cashflowBuffer / riskFlags 7 축.
sourceRefs:
  - dartlab://skills/engines.credit.creditRisk
knowledgeRefs:
  - engines.credit
runtimeCompatibility:
  server:
    status: supported
  localPython:
    status: supported
  mcp:
    status: supported
  webAi:
    status: limited
  pyodide:
    status: limited
whenToUse:
  - credit risk grading
  - leverage / interest coverage / cashflow buffer
  - Company.credit 응용
---

## 절차

- Company.credit와 재무 안정성 관련 capability를 확인한다.
- 부채, 이자보상, 영업현금흐름, 유동성 지표를 같은 기간 기준으로 만든다.
- 위험 요인과 완화 요인을 별도 ref로 구분한다.
- 금융업이면 일반 부채비율 해석 한계를 남긴다.

## 공개 호출 방식

```python
import dartlab

c = dartlab.Company("005930")
# 1. 무인자 — 가이드 DataFrame (axis × 7)
credit_guide = c.credit()
# 2. 신용 위험 측정 — 7 축 (leverage / interestCoverage / cashflowBuffer / ...)
credit_score = c.credit("종합")
# 3. dartlab.credit(c) — 동일 entry
dartlab.credit(c)
```


- `c = dartlab.Company("005930")`
- `c.credit()`
- `dartlab.credit(c)`

## 호출 동작

- Company 재무 snapshot에서 차입, 현금흐름, 이자보상, 유동성 지표를 읽어 신용 위험을 계산한다. analysis와 상호 import하지 않고 필요한 데이터는 Company/core에서 직접 가져온다.
- 실행 전에 target, period/date, metric, source 또는 universe를 확인한다.
- 데이터가 없거나 runtime 제한이 있으면 값을 추정하지 않고 한계와 필요한 다음 수집 경로를 말한다.

## 대표 반환 형태

- dict 또는 DataFrame 형태의 신용 지표를 반환한다. 핵심 키는 grade/score, leverage, interestCoverage, cashflowBuffer, riskFlags, basis이며 비율은 %, 배수는 배 단위다.
- 전체 세부 필드는 공개 docstring/capability와 동기화한다. 코드/API 변경으로 이 설명이 오래되면 skill 갱신 누락으로 본다.

## 기본 검증

- 실행 결과는 tableRef, valueRef, dateRef, executionRef 중 필요한 근거로 남긴다.
- 최종 판단의 숫자 claim은 해당 table/value ref에 직접 묶는다.
- 스킬과 실제 공개 API의 호출 방식, 대표 반환 형태, 오류/제한 동작이 다르면 같은 변경에서 스킬을 갱신한다.
