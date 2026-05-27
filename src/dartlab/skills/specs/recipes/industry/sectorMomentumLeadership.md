---
id: recipes.industry.sectorMomentumLeadership
title: 섹터 안 모멘텀 leader / laggard (20d 분포 top/bottom)
category: recipes
kind: recipe
scope: builtin
status: curated
graphTier: L1.5
cluster: industry
purpose: 종목 peer set 의 20 거래일 수익률 분포에서 자기 종목 percentile 위치 + 분포 top/bottom 보고. 추론 라벨 없이 ranking + 절대 위치만. peers + price gather 결합.
whenToUse:
  - 섹터 leader
  - 섹터 laggard
  - sector momentum ranking
  - peer percentile
examples:
  - 반도체 섹터에서 20일 모멘텀 leader 가 누구
  - 005930 이 섹터 안 몇 분위에 있나
  - peer 중 모멘텀 leader / laggard top 3 bottom 3
expectedOutputs:
  - peer 종목별 20d 수익률 + 분포 percentile rank 표
  - top / bottom 3 종목 (leader / laggard)
  - 자기 종목 위치 (percentile + 절대 수익률)
linkedSkills:
  - engines.gather
  - recipes.industry.peerPriceConvergence
  - recipes.sentiment.priceMomentumGap
toolRefs:
  - EngineCall
  - RunPython
requiredEvidence:
  - skillRef
  - tableRef
  - valueRef
  - dateRef
  - sourceRef
  - executionRef
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
testUniverse:
  market: KR
  stockCodes:
    - "005930"
    - "000660"
expectedNovelty:
  - peerPercentile
  - leaderLaggardLabel
falsifier:
  description: "peer 측정 < 5 면 percentile 신뢰도 낮음 — 결론 X."
forbidden:
  - leader → 매수 단정 / laggard → 매도 단정 금지
  - peer 정의 변경 시점 보정 없이 결론
failureModes:
  - peer 수 부족
  - 단일 outlier peer 가 percentile 위치 좌우
  - peer 정의 (sub-industry vs 산업 전체) 차이
lastUpdated: '2026-05-23'
validatedAt: '2026-05-27'
---

## 공개 호출 방식

```python
import dartlab
import polars as pl

target = "005930"
c = dartlab.Company(target)


def floatOr(v):
    try:
        return float(v) if v is not None else None
    except Exception:
        return None


def closeOf(r):
    for k in ("close", "closePrice", "adjClose"):
        x = floatOr(r.get(k))
        if x is not None and x > 0:
            return x
    return None


def ret20(rows):
    if not rows:
        return None
    rows_sorted = sorted(rows, key=lambda r: str(r.get("date") or r.get("tradeDate") or ""))
    closes = [closeOf(r) for r in rows_sorted]
    closes = [x for x in closes if x is not None]
    if len(closes) < 21:
        return None
    return (closes[-1] / closes[-21]) - 1.0


try:
    peers_df = c.gather("peers")
    peer_rows = peers_df.to_dicts() if hasattr(peers_df, "to_dicts") else []
except Exception:
    peer_rows = []

peer_codes = []
for r in peer_rows:
    code = str(r.get("stockCode") or r.get("code") or r.get("peerCode") or "")
    if code and code != target:
        peer_codes.append(code)
peer_codes = peer_codes[:8]

# 자기 종목 + peers ret
try:
    own_df = c.gather("price").head(30)
    own_ret = ret20(own_df.to_dicts() if hasattr(own_df, "to_dicts") else [])
except Exception:
    own_ret = None

peer_rets = []
for code in peer_codes:
    try:
        pc = dartlab.Company(code)
        df = pc.gather("price").head(30)
        rows = df.to_dicts() if hasattr(df, "to_dicts") else []
        r20 = ret20(rows)
        if r20 is not None:
            peer_rets.append({"stockCode": code, "ret20d": r20})
    except Exception:
        continue

all_rets = peer_rets + ([{"stockCode": target, "ret20d": own_ret}] if own_ret is not None else [])
n = len(all_rets)
sorted_rets = sorted(all_rets, key=lambda r: r["ret20d"])

target_rank = next((i for i, r in enumerate(sorted_rets) if r["stockCode"] == target), None)
target_pct = (target_rank / (n - 1)) if (target_rank is not None and n > 1) else None

label = "insufficient"
if target_pct is not None:
    if target_pct >= 0.75:
        label = "leader"
    elif target_pct <= 0.25:
        label = "laggard"
    else:
        label = "middle"

top_n = sorted_rets[-3:] if n >= 3 else sorted_rets
bottom_n = sorted_rets[:3] if n >= 3 else sorted_rets

table = pl.DataFrame(
    [
        {
            "stockCode": r["stockCode"],
            "ret20d": r["ret20d"],
            "rank": i,
            "isTarget": r["stockCode"] == target,
        }
        for i, r in enumerate(sorted_rets)
    ]
)

emit_result(
    table=table,
    values={
        "peerCount": len(peer_rets),
        "targetRet20d": own_ret,
        "targetPercentile": (round(target_pct * 100, 1) if target_pct is not None else None),
        "label": label,
    },
    date="latest",
    sources=["dartlab://gather/peers", "dartlab://gather/price"],
)
```

## 호출 동작

### 1. 결론 도출

종목 vs peer 20일 모멘텀 percentile rank 단정 (leader ≥ 75% / middle / laggard ≤ 25%). 예: "종목 20d +8.4% (peer 분포 p82) → leader phase, top 3: A · B · C."

### 2. 핵심 근거 수집

- 자기 종목 + 최대 8 peer 의 20 거래일 수익률
- peer 분포 (p10/p50/p90 분위수)
- 자기 종목 rank + percentile

### 3. 메커니즘 분석

```
종목 + peer 8 → 20거래일 close 시계열
              → ret20d 계산 (closes[-1]/closes[-21] - 1)
              → ranking (오름차순 또는 내림차순)
              → 자기 종목 percentile rank
                            ↓
percentile ≥ 75%  → leader (상위 quartile)
25% < x < 75%     → middle (peer 동행)
percentile ≤ 25%  → laggard (하위 quartile)
```

peer 분포 dispersion 이 좁으면 leader/laggard 차이 marginal — 답안에 분포 std 명시.

### 4. 반례·한계

- peer set 5 종목 미만 시 분포 신뢰도 낮음.
- 신규 상장 종목 (price history < 20 거래일) 비교 base 부재.
- 같은 산업 peer 중 시총 격차 큰 종목 섞이면 변동성 차이 큼 — size factor 보정 X.
- 단기 20일 ranking 만으로 추세 단정 금지 — 60d/120d 결합 권장.

### 5. 후속 모니터링

- leader 진입 직후: `recipes.sentiment.priceMomentumGap` 로 단/중기 momentum gap 확인.
- laggard 지속 시 (3 측정 모두 laggard): `recipes.industry.sectorFlowConcentration` 로 자금 이탈 확인.
- middle phase + dispersion 좁음: peer convergence `recipes.industry.peerPriceConvergence` cross-check.

## 대표 반환 형태

| column | 의미 |
|---|---|
| `stockCode` | 종목 코드 |
| `ret20d` | 20 거래일 수익률 |
| `rank` | 정렬 위치 (오름차순) |
| `isTarget` | 자기 종목 여부 |

values: peerCount · targetRet20d · targetPercentile · label

## 연계 절차

1. recipes.industry.peerPriceConvergence — leader/laggard 가 분산 phase 어디 위치하는지.
2. recipes.sentiment.priceMomentumGap — 자기 종목 단독 모멘텀 갭과 결합.

## 기본 검증

- peer 측정 < 5 → label=insufficient.
- peer 정의 변경 시점 직후 row 는 한계 표기.
- leader 라벨이 *매수 신호* 가 아님을 명시.
