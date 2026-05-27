---
id: recipes.industry.industryStagePhase
title: 산업 단계 매핑 — ROIC-WACC spread 분포로 phase 판정
category: recipes
kind: recipe
scope: builtin
status: curated
purpose: peer set 의 ROIC-WACC spread 분포 (mean·std·skew) + 매출 CAGR 5y 결합으로 산업의 *도입 / 성장 / 성숙 / 후행* phase 판정. 단일 회사가 아닌 peer set 단면 분포가 판정 신호. industry ↔ scan 격리 메우는 조합.
whenToUse:
  - 산업 단계 매핑
  - industry stage phase
  - ROIC-WACC spread 분포
  - 도입기 후행기 판정
examples:
  - 반도체 산업이 지금 어느 phase 야 — 성장? 성숙?
  - 005930 속한 산업이 도입 / 성장 / 성숙 / 후행 중 어디
  - peer ROIC - WACC spread 분포로 산업 단계 판정해줘
expectedOutputs:
  - phase 단일 라벨 (growth / mature / decline / transition / indeterminate) + peerCount
  - peer 평균 ROIC-WACC spread + 표준편차 + 매출 5y CAGR 평균
  - peer < 4 일 때 indeterminate 표기 + 한계 명시
linkedSkills:
  - engines.industry
  - engines.scan
  - engines.company
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
  - "engines.viz.peerMatrix"
  - "engines.viz.tableBackedChart"
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
gap:
  primary:
    - industry
    - scan
testUniverse:
  market: KR
  stockCodes:
    - "005930"
    - "000660"
    - "035420"
falsifier:
  description: "peer set ≤ 3 종목이면 분포 신호 결론 X. mean ROIC-WACC spread 의 95% CI 가 0 을 포함하면 *phase 미정* 처리."
lastUpdated: "2026-05-22"
validatedAt: '2026-05-27'
---

## 공개 호출 방식

```python
import dartlab
import polars as pl
import statistics

target = "005930"
c = dartlab.Company(target)

try:
    peers = c.industry("peers").to_dicts()
except Exception:
    peers = []

spreads = []
growths = []
for p in peers:
    roic = p.get("roic") or p.get("returnOnInvestedCapital")
    wacc = p.get("wacc") or p.get("costOfCapital")
    cagr = p.get("revenueCagr5y") or p.get("salesCagr5y")
    try:
        s = float(roic) - float(wacc) if roic is not None and wacc is not None else None
    except (TypeError, ValueError):
        s = None
    if s is not None:
        spreads.append(s)
    try:
        g = float(cagr) if cagr is not None else None
    except (TypeError, ValueError):
        g = None
    if g is not None:
        growths.append(g)

if len(spreads) < 4:
    phase = "indeterminate (peer < 4)"
    mean_s = std_s = None
    mean_g = None
else:
    mean_s = statistics.mean(spreads)
    std_s = statistics.stdev(spreads) if len(spreads) > 1 else 0
    mean_g = statistics.mean(growths) if growths else None
    # phase 분류
    if mean_g is not None and mean_g > 0.15 and mean_s > 0.05:
        phase = "growth"
    elif mean_g is not None and mean_g < 0.02 and mean_s < 0:
        phase = "decline"
    elif mean_s > 0.10 and (mean_g is None or mean_g < 0.10):
        phase = "mature"
    else:
        phase = "transition"

table = pl.DataFrame([{
    "phase": phase,
    "peerCount": len(peers),
    "meanRoicWaccSpread": mean_s,
    "stdRoicWaccSpread": std_s,
    "meanRevenueCagr5y": mean_g,
}])

emit_result(
    table=table,
    values={"phase": phase, "peerCount": len(peers)},
    date=None,
    sources=["dartlab://industry/peers"],
)
```

## 호출 동작

### 1. 결론 도출

peer 분포 4 phase 단정. 예: "반도체 peer set 8 종목 — mean ROIC-WACC spread +12.3% / std 4.8% / mean CAGR 8.4% → phase=mature (spread > 10% + CAGR < 10%). 분산 4.8% 중간 — peer 간 vendor lock-in 상이 (HBM 강자 vs 범용 메모리)."

### 2. 핵심 근거 수집

- Company.industry('peers') peer set (8-15 종목)
- 각 peer × (ROIC + WACC + revenueCagr5y) 3 metric
- peer spread = ROIC - WACC, peer CAGR = 매출 5y CAGR
- mean + std + count 산출

### 3. 메커니즘 분석

```
peer set → 분포 산출
   mean(ROIC-WACC spread)  → 산업 평균 *경제적 부가가치 창출* 강도
   std(ROIC-WACC spread)   → peer 간 dispersion (winner-take-all vs 균등)
   mean(revenueCagr5y)     → 산업 성장 속도
   ↓
4 phase 매트릭스:
   growth     → CAGR > 15% + spread > 5%  (성장 + 부가가치 동시)
   mature     → spread > 10% + CAGR < 10% (성장 둔화 but 수익성 견조)
   decline    → CAGR < 2% + spread < 0    (성장 + 수익성 동시 약화)
   transition → 기타 (혼재)
   indeterminate → peer < 4 또는 95% CI 0 포함
   ↓
phase 별 투자 implication:
   growth     → multiple expansion 후보
   mature     → cash return 강점 (dividend / buyback)
   decline    → pricing power 약화 — 사양산업
   transition → phase 전환 watch (재진입 시점 후보)
```

단일 phase 영구 아님 — 분기/연 단위 전환. std 큼 = winner-take-all (mature 라도 일부 peer 만 spread 양수).

### 4. 반례·한계

- peer < 4 → 분포 신호 결론 X (indeterminate).
- ROIC/WACC 둘 다 누락 peer 비율 > 50% → coverage 한계.
- 신생 산업 (5y 미달) 은 CAGR 신호 약 — growth phase 단정 어려움.
- mature → decline 전환은 lag 2-3 년 — 단년 신호로 후행.

### 5. 후속 모니터링

- mature/decline phase → `recipes.industry.marginCompressionScan` 으로 peer 마진 압축 cluster.
- growth phase + peer dispersion 큼 → `recipes.industry.sectorMomentumLeadership` 로 leader 추출.
- phase 전환 (transition) → `recipes.industry.peerCapexWave` 로 capex 변화 추적.

## 대표 반환 형태

| column | 의미 |
|---|---|
| `phase` | growth / mature / decline / transition / indeterminate |
| `peerCount` | peer set 크기 |
| `meanRoicWaccSpread` | peer 평균 ROIC - WACC |
| `stdRoicWaccSpread` | peer ROIC-WACC 표준편차 |
| `meanRevenueCagr5y` | peer 평균 매출 5y CAGR |

## 연계 절차

1. recipes.industry.peerCapexWave - 같은 phase 의 capex 동조성 확인.
2. recipes.industry.marginCompressionScan - mature/decline phase 마진 압축 cluster.
3. recipes.meta.screen.industryStageScreen - phase 기반 종목 screen.

## 기본 검증

- peer < 4 → phase 결론 X.
- ROIC / WACC 둘 다 누락된 peer 비율 > 50% → coverage 한계 명시.
- *단일 phase* 가 영구하다는 단정 금지 — phase 전환은 분기/연 단위.
