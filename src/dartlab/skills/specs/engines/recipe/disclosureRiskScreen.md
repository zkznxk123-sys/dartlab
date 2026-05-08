---
id: engines.recipe.disclosureRiskScreen
title: 공시 위험 스크린 (전종목 disclosure 위험 + 정정 신호)
category: engines
kind: recipe
scope: builtin
status: unverified
purpose: 전종목 횡단으로 공시 위험 신호 (정정 빈도, 자기자본 변동, 영업환경 변경 등) 가 높은 종목 후보를 추출하는 절차. 트리거 — '공시 위험 스캔', '정정 빈도 횡단', '공시 위험 후보'.
whenToUse:
  - 공시 위험
  - 정정 공시
  - disclosure 위험
  - 공시 위험 스크린
  - 정정 빈도
  - 위험 신호 종목
linkedSkills:
  - engines.scan.disclosureRisk
  - engines.scan.crossSectionStockScreen
  - engines.analysis.disclosureChange
toolRefs:
  - EngineCall
  - RunPython
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
      - browser 안에서는 전종목 스캔 메모리 부담
lastUpdated: '2026-05-07'
---

## 공개 호출 방식

```python
import dartlab

risk_scan = dartlab.scan("disclosureRisk")
top_risks = risk_scan.head(10)
# 상위 위험 종목 각각의 정정 공시 검사 (sequential)
```

## 호출 동작

전종목 disclosure 위험 점수 → 상위 N 추출 → 각 종목의 정정 공시 / 자기자본 변동 / 임원 변경 패턴 점검.

1. scan("disclosureRisk") — 전종목 위험 점수
2. crossSectionStockScreen — 매출 규모 + 시가총액 필터
3. 상위 10 후보 추출
4. 각 후보의 disclosureEvent (sequential) — 정정 공시 검증

## 대표 반환 형태

- `tableRef` 2 개 (위험 스캔 + 상위 후보)
- `dateRef` 1 개
- 답변 본문 markdown table — 위험 후보 10 행 (위험 점수 + 정정 빈도 + 비고)

## 연계 절차

1. engines.scan.disclosureRisk — 전종목 위험 점수
2. engines.scan.crossSectionStockScreen — 필터
3. engines.analysis.disclosureChange — 변화 신호 분석

## 기본 검증

- 위험 점수 + 정정 빈도 + 사유 함께.
- "분식 가능성" 단정 X — 위험 신호일 뿐 결과 아님.
- 상위 후보의 산업·시가총액 분포 확인.
