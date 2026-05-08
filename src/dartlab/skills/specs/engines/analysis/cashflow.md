---
id: engines.analysis.cashflow
title: 현금흐름 분석
kind: curated
scope: builtin
status: unverified
category: engines
purpose: 영업현금흐름, 투자, 재무활동, 이익의 현금 전환을 점검한다.
whenToUse:
  - 현금흐름 분석
  - 이익은 나는데 현금이 부족한지
  - FCF와 운전자본 변화
inputs:
  - 기업명 또는 종목코드
outputs:
  - cashflow thesis
  - 현금흐름 표
  - 품질 판단
capabilityRefs:
  - Company.analysis
  - Company.show
  - scan.cashflow
  - scan.quality
  - Company.credit
toolRefs:
  - search_reference
  - RunPython
  - finalize_answer
knowledgeRefs:
  - cashflowConcepts
  - financialStatementConcepts
requiredEvidence:
  - target
  - period
  - metric
  - table
expectedOutputs:
  - cashflow thesis
  - CF 근거 표
  - 이익 품질
  - 한계
visualGuidance:
  - OCF, capex, FCF, 순이익 비교 표가 있을 때만 chart를 만든다.
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
    dataSources:
      - HuggingFace dartlab-data dart/finance/{stockCode}.parquet
      - HuggingFace dartlab-data edgar/finance/{ticker}.parquet
      - HuggingFace dartlab-data dart/scan/finance-lite.parquet
    requiredSetup:
      - 현금흐름표가 포함된 Company finance snapshot을 확인한다.
    limitations:
      - 세부 운전자본 주석이 없는 snapshot에서는 원인 판단을 제한한다.
failureModes:
  - 순이익만 보고 현금흐름 판단
  - 투자현금흐름 지출을 모두 부정적으로 단정
  - 일회성 운전자본 변동을 구조 변화로 단정
forbidden:
  - CF 표 없이 현금 창출력 단정
  - 결손값을 0으로 대체
examples:
  - 삼양식품 현금흐름 분석해줘
  - 이익의 질이 좋은지 현금흐름으로 봐줘
source:
  type: curated_markdown
  owner: dartlab
lastUpdated: "2026-05-02"
---

## 절차

- CF, IS, BS 관련 capability를 확인하고 같은 기간 기준으로 묶는다.
- OCF, capex, FCF, 순이익 또는 운전자본 변동을 표로 만든다.
- 현금흐름 품질 claim은 이익과 현금의 차이를 보여주는 ref에 묶는다.
- 세부 주석이 없으면 원인 판단을 제한한다.

## 공개 호출 방식

```python
import dartlab

c = dartlab.Company("005930")

# 1. 가이드 확인 (선택)
c.analysis()

# 2. 실제 axis 실행
result = c.analysis("financial", "현금흐름")

# 3. 모듈 함수형 (대안)
result = dartlab.analysis("financial", "현금흐름", company=c)
```

## 호출 동작

- Company 재무 snapshot과 표준 계정 매핑을 읽어 단일 기업의 재무 축을 계산한다. 인자 없이 호출하면 사용 가능한 axis/subaxis 가이드 DataFrame을 반환한다. 데이터가 없으면 값을 만들지 않고 None 또는 데이터 부재 메시지로 제한한다.
- 실행 전에 target, period/date, metric, source 또는 universe를 확인한다.
- 데이터가 없거나 runtime 제한이 있으면 값을 추정하지 않고 한계와 필요한 다음 수집 경로를 말한다.

## 대표 반환 형태

- 주로 DataFrame 또는 dict-like 결과를 반환한다. 핵심 컬럼/키는 period, metric/account, value, unit, basis, comment이며 금액 단위는 원/백만원, 비율은 % 또는 배수다.
- 전체 세부 필드는 공개 docstring/capability와 동기화한다. 코드/API 변경으로 이 설명이 오래되면 skill 갱신 누락으로 본다.

## 기본 검증

- 실행 결과는 tableRef, valueRef, dateRef, executionRef 중 필요한 근거로 남긴다.
- 최종 판단의 숫자 claim은 해당 table/value ref에 직접 묶는다.
- 스킬과 실제 공개 API의 호출 방식, 대표 반환 형태, 오류/제한 동작이 다르면 같은 변경에서 스킬을 갱신한다.


