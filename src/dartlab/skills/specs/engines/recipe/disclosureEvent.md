---
id: engines.recipe.disclosureEvent
title: 공시 이벤트 분석 (목록 + 원문 + 변화 추적)
category: engines
kind: recipe
scope: builtin
status: unverified
purpose: 단일 회사의 최근 공시 이벤트를 목록 + 원문 + 기간간 변화 3 축으로 분석하는 절차. 신규 공시/주요사항 발생 시 thesis 영향 평가.
whenToUse:
  - 최근 공시 분석
  - 공시 이벤트 평가
  - 공시 변화 추적
  - 주요사항 보고서
  - 자사주 매입 공시
  - 신규 공시 영향
  - 공시 원문 확인
linkedSkills:
  - engines.company.researchStarter
  - engines.company.disclosureEvent
  - engines.analysis.disclosureChange
  - engines.scan.disclosureRisk
toolRefs:
  - engine_call
  - run_python
requiredEvidence:
  - skillRef
  - tableRef
  - dateRef
runtimeCompatibility:
  server:
    status: supported
  localPython:
    status: supported
  pyodide:
    status: limited
    limitations:
      - browser 안에서는 readFiling 본문 길이 한정
lastUpdated: '2026-05-06'
---

## 공개 호출 방식

```python
import dartlab

c = dartlab.Company("005930")

recent = c.disclosure(days=30)
top_filing = recent.head(1)
detail = c.readFiling(top_filing["rceptNo"][0])
diff = c.diff()
change = c.analysis("financial", "공시변화")
```

## 호출 동작

최근 N 일 공시 목록 → 가장 최근 1 건 원문 read → 기간간 diff → 공시변화 분석. 새 주요사항 (자사주, M&A, 유상증자 등) 발생 시 thesis 영향 평가.

1. 회사 진입
2. disclosure(days=30) — 최근 30 일 공시 목록
3. readFiling(rceptNo) — 가장 최근 공시 원문
4. diff() — 기간간 텍스트 변화
5. analysis("financial", "공시변화") — 변화 신호 종합

## 대표 반환 형태

- `tableRef` 2 개 (disclosure 목록 + diff 결과)
- `dateRef` 2 개 (최근 공시 일자 + 분석 기준 시점)
- 답변 본문에 markdown evidence table (rceptNo / filedAt / title / formType)

## 연계 절차

1. engines.company.researchStarter — 회사 진입
2. engines.company.disclosureEvent — 공시 이벤트 종합
3. engines.analysis.disclosureChange — 변화 신호
4. engines.scan.disclosureRisk — 동종 횡단 공시 위험

## 기본 검증

- 공시 일자 (filedAt) 명시 — 사건 시점.
- "주요사항" 분류 명시 (자사주 매입 / M&A / 유상증자 / 무상증자 / 합병 등).
- readFiling 결과 원문 100~500 자 발췌 본문에 인용.
- thesis 영향 평가는 가정·시나리오 분리 (단정 X).
