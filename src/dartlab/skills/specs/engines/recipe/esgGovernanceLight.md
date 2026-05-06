---
id: engines.recipe.esgGovernanceLight
title: ESG light 점검 (지배구조 + 감사 + 종업원 + 환경 신호)
category: engines
kind: recipe
scope: builtin
status: unverified
purpose: 정식 ESG 데이터 부재 시 dartlab 보유 신호 (지배구조 + 감사 + 종업원 + 자본배분 일관성) 만으로 가벼운 ESG audit 을 만드는 절차.
whenToUse:
  - ESG 분석
  - 지속가능성
  - 사회 책임
  - light ESG
  - ESG 점검
  - 비재무 audit
linkedSkills:
  - engines.company.researchStarter
  - engines.analysis.governance
  - engines.analysis.governanceAudit
  - engines.scan.workforce
  - engines.analysis.financialConsistency
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
      - browser 안에서는 docs/finance 일부 한정
lastUpdated: '2026-05-06'
---

## 공개 호출 방식

```python
import dartlab

c = dartlab.Company("005930")

governance = c.analysis("financial", "지배구조")
gov_audit = c.analysis("financial", "지배구조감사")
workforce = c.workforce()
consistency = c.analysis("financial", "재무정합성")
```

## 호출 동작

지배구조 + 감사 신호 + 종업원 (인력 안정성·인건비 비중) + 재무 정합성 4 축. 정식 ESG 데이터 부재 — 보조 신호로 light audit.

1. 회사 진입
2. analysis("financial", "지배구조") — G 영역
3. analysis("financial", "지배구조감사") — G 보조 (감사·분식 신호)
4. workforce() — S 영역 보조 (인력 변화·인건비)
5. analysis("financial", "재무정합성") — 일관성

## 대표 반환 형태

- `tableRef` 3+ 개
- `valueRef` 5+ (지배구조 점수 / 감사 신호 / 인력 변화 / 일관성)
- `dateRef` 1 개

## 연계 절차

1. engines.company.researchStarter — 회사 진입
2. engines.analysis.governance — G 종합
3. engines.analysis.governanceAudit — 감사 신호
4. engines.scan.workforce — S 보조 (인력)
5. engines.analysis.financialConsistency — 일관성

## 기본 검증

- "ESG 우수" 단정 X — light audit 임을 명시.
- 환경 (E) 영역은 dartlab 직접 데이터 없음 — 명시.
- G 종합 점수 + 보조 신호 (감사·인력) 함께.
