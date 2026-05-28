---
id: recipes.industry.rdIntensityTrend
title: R&D / 매출 비율 추세 + peer cross-section rank
category: recipes
kind: recipe
scope: builtin
status: curated
purpose: 회사의 R&D / 매출 비율 5y 시계열 + 같은 산업 peer set 단면 분포에서 percentile rank. R&D 강도가 peer 대비 *상위 quartile* + *상승 추세* 인 회사는 *innovation lead* 후보. 단순 ratio 가 아닌 추세 + cross-section 결합. 트리거 — 'R&D / 매출 비율 추세 + peer cross-section rank', 'rd intensity trend', 'rdIntensityTrend'.
whenToUse:
  - R&D 강도 추세
  - innovation lead 후보
  - R&D peer rank
  - 연구개발 비중 추세
examples:
  - 005930 R&D / 매출 비율이 peer 대비 어느 분위
  - 반도체 산업에서 연구개발 강도 가장 높은 회사
  - 5년간 R&D 강도가 상승 추세인 종목
expectedOutputs:
  - 회사 R&D / 매출 비율 5y 시계열 + YoY 변화율
  - peer set 단면 percentile rank + 평균 / 중앙값
  - innovation lead 후보 분류 (상위 quartile + 상승 추세 동시)
linkedSkills:
  - engines.industry
  - engines.company
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
    - analysis
testUniverse:
  market: KR
  stockCodes:
    - "005930"
    - "000660"
    - "035420"
falsifier:
  description: "R&D 항목이 비용처리·자산화 정책 변경된 연도가 추세 안에 있으면 신호 왜곡 가능 — 회계정책 변경 row 별도 명시 필수."
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

def rd_series(code):
    try:
        rows = dartlab.Company(code).analysis("rdSummary").to_dicts()
        return [(str(r.get("year"))[:4], (float(r.get("rdExpense") or 0)) / max(float(r.get("revenue") or 1), 1)) for r in rows if r.get("year")]
    except Exception:
        return []

own = dict(rd_series(target))
years = sorted(own.keys())
if len(years) >= 3:
    # 5y trend slope
    recent = [own[y] for y in years[-5:]]
    n = len(recent)
    if n >= 3:
        x = list(range(n))
        mx = statistics.mean(x)
        my = statistics.mean(recent)
        num = sum((xi-mx)*(yi-my) for xi, yi in zip(x, recent))
        den = sum((xi-mx)**2 for xi in x)
        slope = num / den if den else 0
    else:
        slope = None
else:
    slope = None

try:
    peers_meta = c.industry("peers").to_dicts()
except Exception:
    peers_meta = []

peer_recent = []
for p in peers_meta[:15]:
    code = p.get("code") or p.get("stockCode")
    if not code or code == target:
        continue
    p_series = dict(rd_series(code))
    p_years = sorted(p_series.keys())
    if p_years:
        peer_recent.append((code, p_series[p_years[-1]]))

# percentile rank
my_recent = own[years[-1]] if years else None
rank = None
if my_recent is not None and peer_recent:
    higher = sum(1 for _, v in peer_recent if v > my_recent)
    rank = 1 - higher / len(peer_recent)  # 0~1 (1 = 최고)

table = pl.DataFrame([{
    "rdIntensityLatest": my_recent,
    "trendSlope5y": slope,
    "peerCount": len(peer_recent),
    "percentileRank": rank,
    "trendDirection": "rising" if (slope is not None and slope > 0.001) else "falling" if (slope is not None and slope < -0.001) else "flat",
}])

emit_result(
    table=table,
    values={"rdIntensity": my_recent, "rank": rank, "slope": slope},
    date=years[-1] if years else None,
    sources=["dartlab://analysis/rdSummary", "dartlab://industry/peers"],
)
```

## 호출 동작

### 1. 결론 도출

R&D / 매출 비율 5y slope + peer percentile rank 단정 (innovation lead 후보 / inline / lag). 예: "R&D/매출 6.8% (peer p82), 5y slope +0.4%/yr → rising trend + 상위 quartile → innovation lead 후보."

### 2. 핵심 근거 수집

- 회사 R&D 비용 5y 시계열 (Company.show 의 R&D 항목)
- 매출 5y 시계열 (Company.show revenue)
- peer set 단면 R&D / 매출 분포 (산업)

### 3. 메커니즘 분석

```
회사 R&D 5년 + 매출 5년
   ↓
ratio[t] = R&D[t] / revenue[t] (각 연도)
   ↓
linear regression slope (5점 fit) → trendDirection
   slope > +0.5%/yr → rising
   slope < -0.5%/yr → falling
   ±0.5%/yr          → flat
   ↓
peer 단면 비교 → percentile rank (1 = 가장 높음)
   percentile ≥ 75% + rising → innovation lead 후보
   percentile ≥ 75% + flat  → 고강도 유지 (mature R&D)
   percentile < 25%          → R&D 강도 낮음 (cost-leadership 또는 mature)
```

추세 + cross-section 결합 = 단순 ratio 가 아닌 *추세 + 위치* 신호. innovation lead 후보 = 두 조건 동시 충족.

### 4. 반례·한계

- R&D 정의 차이 (자본화 vs 비용화) peer 비교 노이즈.
- 5점 표본 너무 작아 slope 신뢰도 낮음.
- 일회성 R&D 폭증 (대형 인수 직후) outlier 영향.
- 산업별 R&D 강도 base 다름 (반도체 vs 식품) — 같은 산업 peer 만 비교 의미.

### 5. 후속 모니터링

- innovation lead 후보 진입: `recipes.fundamental.valuation.damodaran.reinvestmentRoc` 로 reinvestment ROC 정합 확인.
- R&D 강도 falling 지속: `recipes.industry.industryStagePhase` 으로 산업 mature/decline 확인.
- R&D 강도 percentile p25 미만 + 매출 성장 둔화: `recipes.fundamental.quality.forensics.deepDive` 로 회사 quality 점검.

## 대표 반환 형태

| column | 의미 |
|---|---|
| `rdIntensityLatest` | 최근 연도 R&D / 매출 |
| `trendSlope5y` | 5 년 linear slope |
| `peerCount` | peer 비교 표본 |
| `percentileRank` | peer 단면 percentile (0~1) |
| `trendDirection` | rising / falling / flat |

## 연계 절차

1. recipes.industry.industryStagePhase - phase 와 R&D 강도 정합.
2. recipes.fundamental.quality.forensics.accountingPolicyChange - R&D 회계 정책 변경 추적.
3. recipes.fundamental.valuation.damodaran.rdCapitalization - R&D 자산화 효과 검증.

## 기본 검증

- 시계열 < 3 년 또는 peer < 4 면 결론 X.
- R&D 회계 정책 변경 (비용 ↔ 자산화) 발생 연도는 추세 분석에서 분리.
- *innovation lead* 결론은 R&D 강도만으로 단정 X — patent · 매출 증분 등 보조 신호 필요.
