---
id: engines.recipe.earningsQualityCheck
title: 이익 quality 점검 (발생주의 + 현금흐름 + 재무정합성)
category: engines
kind: recipe
scope: builtin
status: unverified
purpose: 회사 발표 이익의 quality 를 발생주의 vs 현금흐름 괴리 + 재무 항목 정합성 + 일회성 비중 3 축으로 점검하는 절차.
whenToUse:
  - 이익 quality
  - 분식 회계 가능성
  - 일회성 손익
  - 발생주의 현금주의 괴리
  - 재무 정합성
  - 매출채권 급증
  - 영업이익 신뢰성
linkedSkills:
  - engines.company.researchStarter
  - engines.analysis.earningsQuality
  - engines.analysis.cashflow
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
      - browser 안에서는 분기별 시계열 일부 한정
lastUpdated: '2026-05-06'
---

## 공개 호출 방식

```python
import dartlab

c = dartlab.Company("005930")

quality = c.analysis("financial", "이익품질")
cashflow = c.analysis("financial", "현금흐름")
consistency = c.analysis("financial", "재무정합성")
bs = c.show("BS")
is_df = c.show("IS")
```

## 호출 동작

발표 이익 → 일회성 vs 경상 분리 → 매출채권·재고 변동률 vs 매출 성장 → 영업이익 vs CFO 괴리 → 재무 항목 시계열 정합성 종합.

1. 회사 진입
2. analysis("financial", "이익품질") — 일회성 비중 + 발생주의 신호
3. analysis("financial", "현금흐름") — CFO / 영업이익 비율
4. analysis("financial", "재무정합성") — BS·IS·CF 시계열 일관성
5. show("BS") + show("IS") — 매출채권·재고·매출 raw

## 대표 반환 형태

- `tableRef` 3 개 (quality 표 + cashflow 표 + consistency 표)
- `valueRef` 5+ (일회성 비중 % / CFO/OP / 매출채권 회전율 / 재고 회전율 / quality 점수)
- `dateRef` 1 개

## 연계 절차

1. engines.company.researchStarter — 회사 진입
2. engines.analysis.earningsQuality — 일회성·발생주의
3. engines.analysis.cashflow — CFO·FCF·배당 충당
4. engines.analysis.financialConsistency — 시계열 정합성

## 기본 검증

- 일회성 손익 비중 (%) 명시 — 자산매각·평가이익·환산이익·소송충당 분리.
- CFO / 영업이익 비율이 0.7 이하면 quality 의심 신호 명시.
- 매출채권 급증 + 매출 성장 &lt; 매출채권 성장 패턴 점검.
- "분식 가능성" 단정 X — 점수 + 시나리오 + 출처.
