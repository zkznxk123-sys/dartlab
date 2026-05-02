---
id: governanceAuditReview
title: 지배구조와 감사 리스크 점검
kind: curated
scope: builtin
status: unverified
category: finance
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
