---
id: engines.analysis.governanceAudit
title: 지배구조와 감사 리스크 점검
kind: recipe
scope: builtin
status: unverified
category: engines
purpose: 감사의견, 내부통제, 특수관계자, 지배구조 신호를 지배구조 + 이익품질 + 재무정합성 + 공시변화 4 축의 결합으로 점검하는 다단 응용.
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
  - Company.analysis
  - Company.disclosure
  - Company.readFiling
toolRefs:
  - search_reference
  - run_python
  - finalize_answer
knowledgeRefs:
  - engines.analysis
  - engines.analysis.governance
  - engines.analysis.earningsQuality
  - engines.analysis.financialConsistency
  - engines.analysis.disclosureChange
linkedSkills:
  - engines.analysis.governance
  - engines.analysis.earningsQuality
  - engines.analysis.financialConsistency
  - engines.analysis.disclosureChange
recipeSteps:
  - skillId: engines.analysis.governance
    note: 이사회 독립성, 지배력 집중, 특수관계자 지표.
  - skillId: engines.analysis.earningsQuality
    note: 이익이 진짜인지 (accruals, OCF/순이익 비교).
  - skillId: engines.analysis.financialConsistency
    note: 재무제표 간 정합성 (BS-PL-CF 합치).
  - skillId: engines.analysis.disclosureChange
    note: 공시 변경 추적 — 회계 기준 / 정책 변경 신호.
sourceRefs:
  - dartlab://skills/engines.analysis.governanceAudit
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
  type: manual_skill
  format: markdown
lastUpdated: '2026-05-07'
---

## 엔진 역할

본 skill 은 단일 axis 응용이 아니라 지배구조 + 이익품질 + 재무정합성 + 공시변화 4 축을 묶는 **recipe** 다. 각 axis 호출은 base SKILL `engines.analysis` 와 자식 응용 skill 에서 한다. 본 skill 은 묶음 절차와 판정 게이트만 제공한다.

## 연계 절차

1. engines.analysis.governance — 이사회 독립성, 지배력 집중, 특수관계자 지표 확인.
2. engines.analysis.earningsQuality — accruals, OCF/순이익 비교로 이익의 진위 점검.
3. engines.analysis.financialConsistency — BS-PL-CF 정합성 검산.
4. engines.analysis.disclosureChange — 공시 변경 추적 (회계 기준·정책 변경 신호).

## 판정 게이트

- 단일 신호 (감사의견 한 줄 / 일회성 정정공시) 로 분식 단정 금지. 4 축 신호가 일관될 때만 risk claim.
- 본문 미조회 상태에서는 제목·프리빌드 기준 위험 신호로 제한 — 그 한계를 답변에 명시.
- 위험 신호 ↔ 확정 사실 구분 — 리스크 thesis 에는 반대 근거도 같이 남긴다.

## 기본 검증

claim 은 기간·metric·값·source 를 포함하며 각 claim 은 해당 axis 결과의 `tableRef` / `valueRef` / `dateRef` 에 직접 묶는다. 본 recipe 는 자식 axis skill 의 호출 방식·반환 키가 변경되면 같은 변경에서 갱신한다.
