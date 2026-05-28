---
id: recipes.industry.marginCompressionScan
title: peer set 마진 압축 cluster (GP·OM·NM 동시 하락)
category: recipes
kind: recipe
scope: builtin
status: curated
purpose: peer set 의 매출총이익률·영업이익률·순이익률 3 축 동시 하락 (≥ -1σ z-score) cluster 식별. 산업 mature/decline phase 의 가장 빠른 정량 신호. industry ↔ scan ↔ analysis 조합. 트리거 — 'peer set 마진 압축 cluster (GP·OM·NM 동시 하락)', 'margin compression scan', 'marginCompressionScan'.
whenToUse:
  - 산업 마진 압축
  - margin compression cluster
  - mature decline 신호
  - peer 3 축 마진 비교
examples:
  - 반도체 peer 마진 같이 무너지고 있나
  - 매출총이익률 영업이익률 순이익률 동시 하락 종목 cluster
  - 005930 속한 산업 마진 압축 신호 정량 측정
expectedOutputs:
  - 3 축 (GP·OM·NM) 동시 -1σ 이하 회사 list
  - peer 평균 마진 + z-score 분포 표
  - 같은 방향 절반 이상이면 cluster 변별력 없음 한계 명시
linkedSkills:
  - engines.industry
  - engines.scan
  - engines.analysis
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
falsifier:
  description: "peer 모두 같은 방향 (마진 압축 또는 마진 확장) 이면 산업 전체 신호이므로 *cluster* 변별력 없음. 절반 이상이 동일 부호면 fail."
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

def margin_series(code, years_back=5):
    try:
        rows = dartlab.Company(code).analysis("profitabilityRatios").to_dicts()
        out = []
        for r in rows[-years_back:]:
            out.append({
                "year": str(r.get("year"))[:4],
                "gp": float(r.get("grossProfitMargin") or 0),
                "om": float(r.get("operatingMargin") or 0),
                "nm": float(r.get("netMargin") or 0),
            })
        return out
    except Exception:
        return []

try:
    peers_meta = c.industry("peers").to_dicts()
except Exception:
    peers_meta = []

audit = []
for p in [{"code": target}] + peers_meta[:12]:
    code = p.get("code") or p.get("stockCode")
    if not code:
        continue
    series = margin_series(code)
    if len(series) < 3:
        continue
    # baseline = 직전 3 년 평균, 최근 = 마지막 연도
    prior = series[:-1]
    cur = series[-1]
    def z(metric):
        vals = [s[metric] for s in prior]
        if len(vals) < 2:
            return None
        mu, sd = statistics.mean(vals), statistics.stdev(vals)
        return (cur[metric] - mu) / sd if sd > 0 else None
    z_gp, z_om, z_nm = z("gp"), z("om"), z("nm")
    compressed = sum(1 for z in (z_gp, z_om, z_nm) if z is not None and z <= -1.0)
    audit.append({
        "code": code,
        "zGp": z_gp,
        "zOm": z_om,
        "zNm": z_nm,
        "compressionScore": compressed,
        "year": cur["year"],
    })

table = pl.DataFrame(audit) if audit else pl.DataFrame(
    schema={"code": pl.Utf8, "zGp": pl.Float64, "zOm": pl.Float64, "zNm": pl.Float64,
            "compressionScore": pl.Int64, "year": pl.Utf8}
)

cluster_n = int((table["compressionScore"] >= 2).sum()) if table.height else 0
emit_result(
    table=table,
    values={"peerCount": table.height, "clusterN": cluster_n},
    date=table["year"].max() if table.height else None,
    sources=["dartlab://analysis/profitabilityRatios", "dartlab://industry/peers"],
)
```

## 호출 동작

### 1. 결론 도출

peer 3축 마진 압축 cluster 단정. 예: "5 peer 중 3 회사가 compressionScore ≥ 2 (GP·OM·NM 동시 -1σ) → 산업 광범위 마진 압축 cluster — mature/decline phase 진입 후보."

### 2. 핵심 근거 수집

- peer set 별 5년 IS 시계열 (Company.show IS)
- 3 마진 계산: GP (gross) = 매출총이익/매출, OM (operating) = 영업이익/매출, NM (net) = 순이익/매출
- 각 축 직전 3년 baseline mean/std → 최근 연도 z-score

### 3. 메커니즘 분석

```
peer 별 5년 IS → GP / OM / NM ratio 시계열
   ↓
직전 3년 (Y-3 ~ Y-1) baseline: mean + std
최근 연도 (Y) → z = (Y - baseline_mean) / baseline_std
   ↓
3 축 중 z ≤ -1σ 인 축 카운트 = compressionScore (0~3)
   ↓
회사별 compressionScore 집계
peer 절반 이상이 compressionScore ≥ 2  → 광범위 압축 cluster
peer 절반 이상이 양수 방향 (-1σ 미만 아님) → 변별력 없음 (falsifier 발동)
```

3 축 모두 동시 압축 = 매출 둔화 + 비용 압박 + 수익성 전반 약화 (산업 cycle 후기 신호). 단일 축 압축은 일회성.

### 4. 반례·한계

- peer 거의 모두 같은 방향 (압축 또는 확장) 이면 산업 전체 신호 — cluster 변별력 없음.
- 회계 정책 차이 (revenue recognition · COGS classification) peer raw 비교 노이즈.
- 신규 상장 (3년 baseline 부족) 측정 불가.
- 일회성 항목 (자산매각 차익 · 충당금 환입) NM z-score 왜곡.

### 5. 후속 모니터링

- 광범위 압축 cluster: `recipes.industry.industryStagePhase` 로 산업 phase 확인 (mature/decline 신호 정합).
- compression 상위 회사: `recipes.fundamental.quality.forensics.deepDive` 로 회사 specific 회계 점검.
- peer 동시 확장 (반대 방향): `recipes.industry.peerCapexWave` 로 capex cycle 진입 여부 확인.

## 대표 반환 형태

| column | 의미 |
|---|---|
| `code` | 종목코드 |
| `zGp` | 매출총이익률 z-score |
| `zOm` | 영업이익률 z-score |
| `zNm` | 순이익률 z-score |
| `compressionScore` | 압축 축 카운트 (0~3) |

## 연계 절차

1. recipes.industry.industryStagePhase - phase 와 압축 신호 정합.
2. recipes.fundamental.credit.cycleStressMap - 마진 압축 → credit 영향.
3. recipes.fundamental.quality.forensics.workingCapitalPressureMap - 압축 시점 운영자본 압박.

## 기본 검증

- 시계열 < 3 년 또는 peer < 4 면 결론 X.
- 모든 peer 가 동일 부호면 *cluster 변별력 없음* (산업 전체 신호).
- one-off 손익 / IFRS 변경 row 가 있으면 baseline 분리 또는 한계 명시.
