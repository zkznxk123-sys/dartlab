---
id: engines.analysis.governanceAudit
title: 지배구조와 감사 리스크 점검
kind: curated
scope: builtin
status: unverified
category: engines
purpose: 감사의견, 내부통제, 특수관계자, 지배구조 신호를 공시와 scan 근거로 점검한다.
whenToUse:
  - 지배구조 리스크
  - 감사 리스크
  - 내부통제와 감사의견
  - 분식회계 가능성 점검
inputs:
  - 기업명 또는 종목코드
outputs:
  - governance risk thesis
  - 감사/공시 근거
  - 한계
capabilityRefs:
  - Company.audit
  - Company.disclosure
  - Company.readFiling
  - scan.audit
  - scan.governance
toolRefs:
  - search_reference
  - run_python
  - finalize_answer
knowledgeRefs:
  - auditRiskConcepts
  - governanceConcepts
requiredEvidence:
  - target
  - period
  - table
  - basis
expectedOutputs:
  - risk thesis
  - 공시 근거
  - 반대 근거
  - 한계
visualGuidance:
  - 연도별 감사/지배구조 신호 표가 있을 때만 chart를 만든다.
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
      - HuggingFace dartlab-data dart/report/{stockCode}.parquet
      - HuggingFace dartlab-data dart/scan/finance-lite.parquet
    requiredSetup:
      - 감사/공시 snapshot 또는 scan prebuild를 먼저 확인한다.
    limitations:
      - 본문 미조회 상태에서는 제목/프리빌드 기준 위험 신호로만 제한한다.
failureModes:
  - 감사의견 하나로 분식 단정
  - 본문 근거 없이 내부통제 문제 단정
  - 리스크 신호와 확정 사실 혼동
forbidden:
  - 분식회계 단정
  - 본문 근거 없는 지배구조 비난
examples:
  - 지배구조 리스크 점검해줘
  - 감사 리스크와 내부통제 이슈 봐줘
source:
  type: curated_markdown
  owner: dartlab
lastUpdated: "2026-05-02"
---

## 절차

- Company.audit, disclosure, scan.audit, scan.governance capability를 확인한다.
- 감사의견, 내부통제, 특수관계자, 지배구조 신호를 기간별 근거로 분리한다.
- 위험 신호와 확정 사실을 구분하고 반대 근거가 있으면 함께 남긴다.
- 본문 조회가 없으면 제목/프리빌드 기준 한계를 명시한다.

## 공개 호출 방식

- `c = dartlab.Company("005930")`
- `c.analysis()`
- `c.analysis("financial", "수익성")`
- `dartlab.analysis(c, axis="financial", sub="수익성")`

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


