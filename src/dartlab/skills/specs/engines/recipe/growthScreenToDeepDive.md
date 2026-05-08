---
id: engines.recipe.growthScreenToDeepDive
title: 성장 스캔 → 상위 후보 → 각 회사 분석
category: engines
kind: recipe
scope: builtin
status: unverified
purpose: 전종목 성장 스캔으로 후보를 추리고 상위 N 종에 대해 회사별 깊이 분석을 진행하는 절차. 트리거 — '성장 스캔 후 깊이 분석', '상위 N 깊이 분석'.
whenToUse:
  - 성장하는 회사 찾기
  - 성장주 후보
  - growth screen
  - 후보 분석
  - 상위 종목 분석
  - 성장성 스크리닝
linkedSkills:
  - engines.scan.growth
  - engines.scan.crossSectionStockScreen
  - engines.company.researchStarter
  - engines.analysis.growth
  - engines.analysis.earningsQuality
toolRefs:
  - EngineCall
  - RunPython
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
      - browser 안에서는 scan dataset snapshot 한정
lastUpdated: '2026-05-07'
---

## 공개 호출 방식

```python
import dartlab

# 1) 전종목 성장 스캔 (CAGR 기준)
candidates = dartlab.scan("growth")  # tableRef

# 2) 상위 5 종 (사용자가 결정)
top_codes = candidates.head(5)["stockCode"].to_list()

# 3) 각 회사 sequential 분석 (CLAUDE.md 메모리 안전)
for code in top_codes:
    c = dartlab.Company(code)
    bs = c.show("BS")
    growth = c.analysis("financial", "성장성")
    quality = c.analysis("financial", "이익품질")
```

## 호출 동작

성장 스캔은 매출·영업이익·순이익 CAGR 기준 후보를 만든다. 상위 N 종 (보통 3~5) 에 대해 sequential 깊이 분석.

1. `dartlab.scan("growth")` — 전종목 (~2,000) 성장성 스코어
2. 상위 N 후보 추출 (단, 매출 규모·기간 필터 통과 조건 명시)
3. 각 회사 sequential 진입 + show("IS") + 분해

## 대표 반환 형태

- `tableRef` 1+5 개 (스캔 결과 + 5 회사 IS)
- `valueRef` 회사당 3~5 개 (매출/영업이익/순이익 CAGR + quality)
- `dateRef` 1 개 (스캔 기준 시점)
- 답변 본문 안 markdown evidence table — 후보 5 행 (회사 / 매출 CAGR / OP CAGR / NI CAGR / quality)

## 연계 절차

1. engines.scan.growth — 전종목 성장성 스코어 (CAGR 기준)
2. engines.scan.crossSectionStockScreen — 매출 규모·기간 필터로 상위 후보
3. engines.company.researchStarter — 각 회사 진입
4. engines.analysis.growth — 회사별 성장 분해 (P×Q × Mix)
5. engines.analysis.earningsQuality — 회사별 이익 quality 점검

## 기본 검증

- 후보 답변은 bullet 만 X — `입력 / 유니버스 / 필터 / 계산식 / 결과` 4 단 + evidence table.
- CAGR 기준 기간 명시 (3 년·5 년·10 년).
- 매출 규모 하한 (예: 매출 1000 억 이상) 으로 micro-cap 잡음 제거.
- 후보 회사별 quality 등급 함께 — 성장 quality 가 매출 채권 급증·일회성에 의존하면 표시.
