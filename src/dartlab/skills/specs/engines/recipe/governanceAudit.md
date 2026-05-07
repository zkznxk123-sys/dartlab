---
id: engines.recipe.governanceAudit
title: 지배구조 audit (이사회 + 지분구조 + 감사 신호)
category: engines
kind: recipe
scope: builtin
status: unverified
purpose: 회사의 지배구조 위험을 이사회 독립성 + 지배력 집중 + 감사 신호 + 분식 가능성 4 축으로 종합 점검하는 절차. 트리거 — '지배구조 위험', '이사회 독립성', '감사 신호', '분식 가능성'.
whenToUse:
  - 지배구조 audit
  - 이사회 점검
  - 지분 구조
  - 감사 위험
  - 분식 회계 가능성
  - 지배력 집중
  - 거버넌스 분석
linkedSkills:
  - engines.company.researchStarter
  - engines.analysis.governanceAudit
  - engines.analysis.governance
  - engines.scan.governance
  - engines.scan.audit
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
      - browser 안에서는 governance topic 단일 호출 한정
lastUpdated: '2026-05-07'
---

## 공개 호출 방식

```python
import dartlab

c = dartlab.Company("005930")

gov = c.analysis("financial", "지배구조")
gov_audit = c.analysis("financial", "지배구조감사")
gov_scan = dartlab.scan("governance")
audit_scan = dartlab.scan("audit")
major = c.show("majorHolder")
```

## 호출 동작

지배구조 종합 → 감사 신호 (분식 회계 가능성) → peer 횡단 거버넌스 → 주요주주 / 최대주주 raw 데이터.

1. 회사 진입
2. analysis("financial", "지배구조") — 이사회 독립성 + 지배력 집중 점수
3. analysis("financial", "지배구조감사") — 감사 신호 + 분식 가능성
4. scan("governance") — peer 횡단 거버넌스 점수
5. scan("audit") — peer 횡단 감사 위험
6. show("majorHolder") — 최대주주 / 주요주주 raw

## 대표 반환 형태

- `tableRef` 4+ (governance + audit + peer scan 2 + majorHolder)
- `valueRef` 4+ (이사회 독립성 / 지배력 집중률 / 감사 신호 / 분식 가능성 점수)
- `dateRef` 1 개

## 연계 절차

1. engines.company.researchStarter — 회사 진입
2. engines.analysis.governance — 지배구조 종합
3. engines.analysis.governanceAudit — 감사 신호 + 분식 가능성
4. engines.scan.governance — peer 횡단 거버넌스 점수
5. engines.scan.audit — peer 횡단 감사 위험

## 기본 검증

- "분식 가능성" 같은 무거운 단정 X — 점수 + 시나리오 + 출처 (감사보고서 주석) 명시.
- 지배력 집중률 (%) + 최대주주 + 우호 지분 합계 함께.
- 이사회 독립성 점수는 사외이사 비율 + 위원회 독립성 함께 표시.
