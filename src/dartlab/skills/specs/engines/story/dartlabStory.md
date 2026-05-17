---
id: engines.story.dartlabStory
title: DartLab 스토리형 분석
kind: curated
scope: builtin
status: unverified
category: engines
purpose: 여러 엔진의 근거를 thesis, evidence, risk, limit 구조로 조립한다.
whenToUse:
  - 보고서 생성
  - 기업 이야기
  - thesis evidence risk 조립
  - dartlabStory
  - story full
  - reportType
  - executive summary
  - credit 보고서
  - valuation 보고서
capabilityRefs:
  - Company.story
  - Company.analysis
  - Company.credit
  - Company.quant
toolRefs:
  - search_reference
  - EngineCall
  - RunPython
  - finalize_answer
knowledgeRefs:
  - dartlabCausalSixActs
requiredEvidence:
  - target
  - period
  - metric
expectedOutputs:
  - thesis
  - evidence
  - risk
  - limits
visualGuidance:
  - story에는 설명 목적이 분명한 chart/table만 포함한다.
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
    status: supported
    dataSources:
      - HuggingFace dartlab-data dart/docs/{stockCode}.parquet
      - HuggingFace dartlab-data dart/finance/{stockCode}.parquet
      - HuggingFace dartlab-data dart/report/{stockCode}.parquet
    requiredSetup:
      - await dartlab.prefetch(stockCode) 후 Company(stockCode)를 생성한다.
    limitations:
      - 브라우저에서는 외부 API를 추가 호출하지 않고 prefetched parquet 기준으로만 작성한다.
failureModes:
  - 보고서 문장만 있고 수치 근거 없음 — analysis · credit · macro 결과 ref 필수
  - reportType 자동 감지 실패 — 명시 호출 (`c.story(reportType="credit")`) 권장
  - template (기업유형) 자동 감지 실패 — 신생/금융/지주 회사는 자동 분류 보수적
  - 블록 evidence 비어 있는데 thesis 만 채움 — 빈 블록은 skip 또는 limits
  - 외부 신평 (Moody's · KIS · NICE) 등급을 dartlab credit 결과처럼 인용
  - 사용자 답변에 *story 내부 분업* 노출 (단일 분석가 목소리 위반)
forbidden:
  - 검산 없는 서사형 투자판단 금지.
  - 모든 숫자·날짜·랭킹은 ref token 으로 묶음 (`<valueRef:...>` 형식).
  - story 가 직접 숫자 계산 금지 — 하위 엔진 (analysis · credit · quant · macro · industry) 결과만 인용.
  - 외부 신평 등급을 dartlab 결과처럼 단정 금지.
examples:
  - 삼성전자 종합 보고서 (full)
  - executive summary (경영자 1 페이지)
  - 신용분석 전용 (credit reportType)
  - 가치평가 전용 (valuation reportType)
  - 자유 블록 조립 (Story([blocks]))
  - markdown · html · json 출력 변환
linkedSkills:
  - engines.story
  - engines.story.companyCausal
  - engines.analysis
  - engines.credit
  - engines.industry
  - engines.macro
source:
  type: curated_markdown
  owner: dartlab
lastUpdated: "2026-05-02"
---

## 절차

- story capability가 제공하는 report type과 한계를 확인한다.
- 필요한 하위 엔진 근거를 실행 결과로 확보한다.
- narrative는 숫자/날짜 claim ref를 가진 상태에서만 작성한다.

## 공개 호출 방식

- `c = dartlab.Company("005930")`
- `c.story()`
- `dartlab.story(c)`

## 호출 동작

- analysis, credit, macro, scan, quant 결과를 thesis/evidence/risk/limit 구조로 조립한다. 숫자 계산은 하위 엔진 결과 ref에 묶는다.
- 실행 전에 target, period/date, metric, source 또는 universe를 확인한다.
- 데이터가 없거나 runtime 제한이 있으면 값을 추정하지 않고 한계와 필요한 다음 수집 경로를 말한다.

## 대표 반환 형태

- report dict 또는 block list를 반환한다. 핵심 키는 thesis, evidenceBlocks, riskBlocks, limits, sourceRefs다.
- 전체 세부 필드는 공개 docstring/capability와 동기화한다. 코드/API 변경으로 이 설명이 오래되면 skill 갱신 누락으로 본다.

## 기본 검증

- 실행 결과는 tableRef, valueRef, dateRef, executionRef 중 필요한 근거로 남긴다.
- 최종 판단의 숫자 claim은 해당 table/value ref에 직접 묶는다.
- 스킬과 실제 공개 API의 호출 방식, 대표 반환 형태, 오류/제한 동작이 다르면 같은 변경에서 스킬을 갱신한다.


