---
id: recipes.meta.screen.macroRegimeAlignedScreen
title: Macro Regime × Sector Momentum Aligned Screen
category: recipes
kind: recipe
scope: builtin
status: drafted
purpose: 현재 macro regime × 그 regime 에서 historically outperform sector 의 momentum z-rank top 종목 스크리닝 — 5 regime × sector 매핑 학술 + 모멘텀 결합. 트리거 — 'regime aligned', 'macro screen', 'regime sector', '국면 종목', '사이클 모멘텀'.
whenToUse:
  - regime aligned
  - macro screen
  - regime sector
  - 국면 종목
  - 사이클 모멘텀
  - sector rotation
  - regime rotation
linkedSkills:
  - engines.scan
  - engines.macro
  - engines.industry
  - engines.quant
toolRefs:
  - EngineCall
  - RunPython
requiredEvidence:
  - skillRef
  - tableRef
  - valueRef
  - dateRef
  - executionRef
  - sourceRef
visualRefs:
  - engines.viz.tableBackedChart
  - engines.viz.peerMatrix
visualGuidance:
  - "regime × sector 매핑 표는 engines.viz.tableBackedChart, 현재 regime row 강조."
  - "sector momentum z-rank 는 engines.viz.peerMatrix — top quartile (z > 1) green."
gap:
  primary:
    - macro
    - industry
testUniverse:
  market: KR
  stockCodes:
    - "005930"
    - "000660"
    - "035720"
    - "207940"
    - "035420"
  asOfPolicy: latest
falsifier:
  description: 현재 regime 분류 confidence < 0.5 면 본 screen 신뢰 한계 — universe 추천 보류. 또는 sector momentum z 계산 0 sector = 데이터 수집 실패.
  pythonCheck: |
    assert regime_confidence >= 0.5 and n_sectors > 0
expectedNovelty:
  - regime
  - sector
  - momentumZ
  - alignedSector
forbidden:
  - regime 분류 = 확정 X (engines.macro.regimes confidence 동행).
  - sector momentum z > 1 = 절대 alpha X — regime 정합 추가 신호 결합 후만 universe.
  - 5 regime × sector 학술 매핑은 US 시장 기반 (1956-2012) — KR 시장 일치성 검증 필요.
failureModes:
  - regime 전환 시점 lag — HMM 분류는 1-3 개월 후행.
  - sector momentum 60M rolling — regime shift 시 momentum 평균 lag.
  - 단일 sector 우세 시 universe 1-2 sector 종목만 (concentration).
examples:
  - 현재 regime expansion + 학술 정합 sector + momentum z top 10
  - regime 전환 (slowdown → recovery) 시점 universe 변동
lastUpdated: '2026-05-28'
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
---

## 공개 호출 방식

```python
import dartlab
import polars as pl

# 1. 현재 macro regime (5 enum)
cycle = dartlab.macro("cycle", market="KR")
regime = cycle.get("regime", "unknown") if isinstance(cycle, dict) else "unknown"
regime_confidence = cycle.get("confidence", 0)

# 2. regime ↔ sector 학술 매핑 (Frazzini-Pedersen + 사이클 sector rotation)
REGIME_SECTORS = {
    "expansion":    ["technology", "industrials", "consumer_discretionary", "financials"],
    "slowdown":     ["healthcare", "consumer_staples", "utilities"],
    "contraction":  ["utilities", "consumer_staples", "healthcare"],
    "recovery":     ["financials", "industrials", "real_estate", "materials"],
    "crisis":       ["consumer_staples", "utilities", "gold"],
}
aligned_sectors = REGIME_SECTORS.get(regime, [])

# 3. sector momentum z (60M rolling sector index return z-score)
sector_momentum = dartlab.quant("sectorMomentum", market="KR")
# → DataFrame: sector · momentumZ

# 4. 정합 sector 안 top momentum z 종목
aligned_universe = (
    sector_momentum.filter(pl.col("sector").is_in(aligned_sectors))
    .sort("momentumZ", descending=True)
    .head(20)
)

emit_result(
    table=aligned_universe,
    values={"regime": regime, "regime_confidence": regime_confidence, "n_sectors": len(aligned_sectors)},
    date="2026-05-28",
    sources=["dartlab://macro/cycle", "dartlab://quant/sectorMomentum"],
)
```

## 호출 동작

### 1. 결론 도출

현재 macro regime 에서 학술 outperform sector × momentum z-rank top universe — regime × momentum 결합 priority.

### 2. 핵심 근거 수집

- `dartlab.macro("cycle")` — 현재 regime + confidence (engines.macro.regimes 5 enum SSOT)
- `dartlab.quant("sectorMomentum")` — sector 별 60M rolling momentum z
- regime ↔ sector 학술 매핑 (Frazzini-Pedersen + sector rotation 정통)

### 3. 메커니즘 분석

```
3 source 결합
   regime (engines.macro.regimes 5 enum + confidence)
   학술 매핑 (regime → aligned_sectors)
   sector momentum z (engines.quant.sectorMomentum)
   ↓
aligned_sectors filter → sector universe
   ↓
sector 안 momentum z desc top 20
   ↓
regime × momentum 동시 신호 universe
```

### 4. 반례·한계

- regime 분류 lag (HMM 1-3 개월 후행).
- 학술 매핑 US 시장 기반 (1956-2012) — KR 일치성 검증 필요.
- sector momentum 60M rolling — regime shift 시 lag.
- 단일 sector 우세 시 universe concentration (5 종목 모두 같은 sector).

### 5. 후속 모니터링

- universe 종목 → 개별 deep dive (`recipes.fundamental.valuation.damodaran.deepDive`).
- regime 전환 (engines.macro.regimes status 변화) → universe 재산출.
- sector momentum z 상위 sector → `recipes.industry.sectorMomentumLeadership` 결합.
- 월 1 회 재실행 + regime 전환 alert.

## 대표 반환 형태

`pl.DataFrame` — 컬럼:
- `sector : str`
- `momentumZ : float`
- `stockCode : str` · `corpName : str` (top 종목)
- `regime : str` (모든 row 동일, header context)
- `alignedSector : bool` (참고)

## 연계 절차

1. 본 recipe → regime × sector momentum universe.
2. universe top → `recipes.fundamental.valuation.damodaran.deepDive` 개별.
3. quality 결합 → `recipes.meta.screen.qualityValueScreen` (good × cheap × regime aligned triple).
4. regime 전환 시점 → `engines.macro.regimes` status 변화 alert.
5. 월 1 회 재실행 + regime check.
