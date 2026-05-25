---
id: engines.scan.undervaluedQuality
title: Scan — 저평가 + 수익성 결합 (undervaluedQuality)
kind: curated
scope: builtin
status: observed
category: engines
purpose: scan engine 의 결합 recipe — *valuation 분위* + *수익성/안정성/효율성 점수* 동시 충족 종목 횡단면 추출. 가치투자 entry 의 quick filter.
whenToUse:
  - undervaluedQuality
  - 저평가 수익성 동시 scan
  - quality + value 결합 screening
runtimeCompatibility:
  pyodide:
    status: supported
  server:
    status: supported
  localPython:
    status: supported
  mcp:
    status: supported
  webAi:
    status: supported
capabilityRefs:
  - scan
---

# Scan — 저평가 + 수익성 결합 (undervaluedQuality)

본 spec 은 `scan("undervaluedQuality")` recipe 의 구조와 의미를 서술. scan engine 의 22 axis 중 결합 axis 의 핵심 entry.

## 공개 호출 방식

```python
import dartlab

result = dartlab.scan("undervaluedQuality", universe="kospi200", limit=20)
# → ScanResult with df: stockCode × (perValuation, perQuality, scoreCombined)
```

## 호출 동작

1. universe 종목 set 가져옴 (kospi200 / kospi / kosdaq200).
2. valuation axis (PER · PBR · EV/EBITDA percentile) + quality axis (ROE · 영업이익률 · 부채비율 점수) 동시 산출.
3. 두 점수 결합 (가중 평균 또는 lexicographic ranking).
4. top N 반환 (default 20).

## 대표 반환 형태

```python
ScanResult(
  df=pl.DataFrame({
    "stockCode": ["005930", ...],
    "perValuation": [0.85, ...],   # 분위 (1 = 가장 저평가)
    "perQuality":   [0.78, ...],
    "scoreCombined": [0.82, ...],
  }),
  meta={"universe": "kospi200", "axis": "undervaluedQuality"},
)
```

## 기본 검증

- df 의 stockCode 컬럼 length == limit (또는 universe 크기 미만).
- perValuation / perQuality / scoreCombined 0-1 범위.
- scoreCombined desc 정렬.

## 관련

- [engines.scan](/skills/engines.scan) — 전체 scan axis
- [engines.analysis](/skills/engines.analysis) — 단일 기업 quality 점수
- [engines.quant](/skills/engines.quant) — quant factor 와 결합
