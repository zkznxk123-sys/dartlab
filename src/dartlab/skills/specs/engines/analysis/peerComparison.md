---
id: engines.analysis.peerComparison
title: 동종 기업 비교 분석
kind: curated
scope: builtin
status: unverified
category: engines
purpose: 둘 이상의 기업을 같은 metric, 같은 기간, 같은 기준으로 비교해 상대 우위와 한계를 판단한다.
whenToUse:
  - 삼성전자와 SK하이닉스 비교
  - 두 기업 경쟁력 비교
inputs:
  - 비교 대상 목록
  - 비교 축 또는 metric
capabilityRefs:
  - Company.analysis
  - Company.show
  - Company.quant
  - scan
toolRefs:
  - search_reference
  - EngineCall
  - RunPython
  - CompileVisual
  - finalize_answer
knowledgeRefs:
  - financialStatementConcepts
visualRefs:
  - comparisonChart
requiredEvidence:
  - target
  - period
  - metric
  - table
expectedOutputs:
  - 동일축 비교표
  - 우위/열위 판단
  - 데이터 누락 한계
visualGuidance:
  - 같은 metric을 대상별로 나란히 비교하는 chart만 허용한다.
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
      - HuggingFace dartlab-data dart/docs/{stockCode}.parquet
      - HuggingFace dartlab-data dart/finance/{stockCode}.parquet
      - HuggingFace dartlab-data dart/report/{stockCode}.parquet
    requiredSetup:
      - 비교 대상별로 await dartlab.prefetch(stockCode)를 먼저 수행한다.
    limitations:
      - 여러 종목 parquet를 브라우저 메모리에 올리므로 대상 수를 작게 유지한다.
      - live market/macro 보강은 서버 환경에서만 한다.
failureModes:
  - partial comparison — peer 그룹 일부만 보고 우열 단정
  - 서로 다른 기간/metric 혼합 — 같은 분기 / 같은 통화 / 같은 scope (연결 vs 별도)
  - peer 산업 분기 무시 — 같은 industryHint 그룹 한정 권장
  - 일회성 손익 (M&A · 매각) 영향 미보정 → 정상화 (normalized) 후 비교
  - 외환 매출 비중 다른 회사 비교 시 환율 영향 미분리
  - 시가총액 격차 큰 (1조 vs 10조) 회사 비교 — 같은 size bucket 권장
forbidden:
  - 한쪽 수치만으로 우열 단정 금지.
  - peer 산업 분기 무시한 cross-industry 비교 금지.
  - 같은 기간 / 같은 scope / 같은 통화 정렬 없이 답변 금지.
examples:
  - 삼성전자 vs SK하이닉스 (같은 산업)
  - 신한 KB 하나 우리 (4 대 금융지주)
  - 시가총액 같은 bucket 비교
  - 일회성 손익 정상화 후 비교
  - 외화 매출 비중 다른 회사 환율 영향 분리
linkedSkills:
  - engines.analysis.profitability
  - engines.analysis.growth
  - engines.analysis.valuation
  - engines.scan
  - engines.industry
source:
  type: curated_markdown
  owner: dartlab
lastUpdated: "2026-05-02"
---

## 절차

- 각 대상의 식별 결과를 확인한다.
- 같은 metric과 기간을 가진 evidence를 대상별로 만든다.
- 한쪽만 있는 수치로 강한 비교 결론을 내지 않는다.
- 비교 표가 있으면 visual을 만든다.

## 공개 호출 방식

```python
import dartlab

c = dartlab.Company("005930")

# 1. 가이드 확인 (선택)
c.analysis()

# 2. 실제 axis 실행
result = c.analysis("governance", "비교분석")

# 3. 모듈 함수형 (대안)
result = dartlab.analysis("governance", "비교분석", company=c)
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


