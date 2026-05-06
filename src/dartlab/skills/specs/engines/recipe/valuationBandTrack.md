---
id: engines.recipe.valuationBandTrack
title: valuation band 추적 (역사 평균 ±σ vs 현재가)
category: engines
kind: recipe
scope: builtin
status: unverified
purpose: 회사 valuation multiple (PER/PBR/EV/EBITDA) 의 역사 평균 ±σ 밴드 안 현재 위치를 추적하는 절차. 단순 스냅샷이 아닌 시계열 추적.
whenToUse:
  - valuation 밴드
  - PER 밴드
  - PBR 밴드
  - 역사 평균 비교
  - valuation 추적
  - 현재가 적정 여부
linkedSkills:
  - engines.company.researchStarter
  - engines.analysis.valuationBand
  - engines.quant.value
  - engines.scan.valuation
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
      - browser 안에서는 historic 시계열 일부 한정
lastUpdated: '2026-05-06'
---

## 공개 호출 방식

```python
import dartlab

c = dartlab.Company("005930")

band = c.analysis("financial", "밸류에이션밴드")
qval = c.quant("가치")
peer_band = dartlab.scan("valuation")
```

## 호출 동작

회사 valuation multiple 시계열 → 역사 평균 + σ → 현재 위치 (- 1σ / 평균 / + 1σ 등) → peer 횡단 비교.

1. 회사 진입
2. analysis("financial", "밸류에이션밴드") — 시계열 + 역사 평균 ±σ
3. quant("가치") — 기술적 가치 신호 (역사 평균 대비)
4. scan("valuation") — peer 횡단 멀티플

## 대표 반환 형태

- `tableRef` 3 개 (band 시계열 + qvalue + peer)
- `valueRef` 4+ (현재 PER / 5 년 평균 / σ 위치 / peer median)
- `dateRef` 1 개

## 연계 절차

1. engines.company.researchStarter — 회사 진입
2. engines.analysis.valuationBand — 역사 ±σ 밴드
3. engines.quant.value — 기술적 가치 신호
4. engines.scan.valuation — peer 횡단

## 기본 검증

- 시계열 N 년 (3/5/10) 명시.
- "현재 저평가" 단정 X — σ 위치 + 가정 (역사 평균 = 적정 여부) 함께.
- peer median 과 함께 — 단일 회사 시계열 만으로는 부족.
