---
id: recipes.industry.sectorMomentumLeadership
title: 섹터 안 모멘텀 leader / laggard (20d 분포 top/bottom)
category: recipes
kind: recipe
scope: builtin
status: tested
graphTier: L1.5
cluster: industry
purpose: 종목 peer set 의 20 거래일 수익률 분포에서 자기 종목 percentile 위치 + 분포 top/bottom 보고. 추론 라벨 없이 ranking + 절대 위치만. peers + price gather 결합.
whenToUse:
  - 섹터 leader
  - 섹터 laggard
  - sector momentum ranking
  - peer percentile
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

종목 + 최대 8 peer 의 20 거래일 수익률 ranking. 자기 종목 percentile ≥ 75% = leader, ≤ 25% = laggard, 그 외 = middle. 추론 X.

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
