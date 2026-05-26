---
id: recipes.industry.peerPriceConvergence
title: 동종 peer 가격 수렴 / 발산 (60d ret 분포)
category: recipes
kind: recipe
scope: builtin
status: tested
graphTier: L1.5
cluster: industry
purpose: 종목의 industry peer 들의 60 거래일 수익률 분포 측정. peer 수익률 std-dev 가 좁아지면 *수렴 phase*, 넓어지면 *발산 phase*. 추론 라벨 없이 분산 정량만. peers + price gather 결합.
whenToUse:
  - peer 가격 수렴
  - sector dispersion
  - 동종 종목 분포
  - 산업 회귀 phase
examples:
  - 반도체 peer 주가 60일 수익률이 수렴하고 있나
  - 동종 종목들 가격 흩어짐 정도 어느 수준
  - 산업이 회귀 phase 인지 발산 phase 인지 정량 확인
expectedOutputs:
  - peer 60d 수익률 평균 + 표준편차 + 분포 분위수 (p10/p50/p90)
  - dispersion direction (convergent / divergent) — std-dev 변화 % 명시
  - 자기 종목 위치 (peer 분포 안 percentile)
linkedSkills:
  - engines.gather
  - recipes.technical.sectorRelativeStrength
  - recipes.macro.betaPeerScreen
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
  - peerReturnDispersion
  - convergencePhase
falsifier:
  description: "peer 수 < 5 면 분산 측정 신뢰도 낮음 — 결론 X. 한 peer 의 outlier 가 분산을 좌우하면 한계 명시."
forbidden:
  - 분산 좁음 → 강세 / 분산 넓음 → 약세 단정 금지
  - peer set 정의 (sub-industry vs 산업 전체) 명시 없이 결론
failureModes:
  - peer 수 부족
  - 단일 outlier 가 dispersion 좌우
  - peer 정의 (GICS / KRX / cross-listed) 차이로 결과 변동
lastUpdated: '2026-05-23'
---

## 공개 호출 방식

```python
import dartlab
import polars as pl
import statistics

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


def ret60(rows):
    if not rows:
        return None
    rows_sorted = sorted(rows, key=lambda r: str(r.get("date") or r.get("tradeDate") or ""))
    closes = [closeOf(r) for r in rows_sorted]
    closes = [x for x in closes if x is not None]
    if len(closes) < 61:
        return None
    return (closes[-1] / closes[-61]) - 1.0


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
peer_codes = peer_codes[:8]  # cap 메모리 안전

# 자기 종목 ret
try:
    own_df = c.gather("price").head(70)
    own_ret = ret60(own_df.to_dicts() if hasattr(own_df, "to_dicts") else [])
except Exception:
    own_ret = None

# peer ret 들 — 메모리 안전 위해 직렬 + cap=8
peer_rets = []
for code in peer_codes:
    try:
        pc = dartlab.Company(code)
        df = pc.gather("price").head(70)
        rows = df.to_dicts() if hasattr(df, "to_dicts") else []
        r60 = ret60(rows)
        if r60 is not None:
            peer_rets.append({"stockCode": code, "ret60d": r60})
    except Exception:
        continue

if len(peer_rets) >= 5:
    rets = [p["ret60d"] for p in peer_rets]
    dispersion = statistics.pstdev(rets)
    p_mean = statistics.mean(rets)
else:
    dispersion = None
    p_mean = None

phase = "insufficient"
if dispersion is not None:
    if dispersion < 0.05:
        phase = "converging"
    elif dispersion > 0.15:
        phase = "diverging"
    else:
        phase = "normal"

table = pl.DataFrame(
    [
        {
            "targetRet60d": own_ret,
            "peerCount": len(peer_rets),
            "peerMeanRet": p_mean,
            "peerDispersion": dispersion,
            "phase": phase,
        }
    ]
)

emit_result(
    table=table,
    values={
        "peerDispersion": dispersion,
        "peerMeanRet": p_mean,
        "phase": phase,
        "peerCount": len(peer_rets),
    },
    date="latest",
    sources=["dartlab://gather/peers", "dartlab://gather/price"],
)
```

## 호출 동작

종목 + 최대 8 peer 의 60 거래일 수익률 분포 산출. dispersion (pstdev) < 5% = converging, > 15% = diverging, 그 외 = normal. 자기 종목 수익률은 분포 위치 비교용. 추론 X.

## 대표 반환 형태

| column | 의미 |
|---|---|
| `targetRet60d` | 종목 60d 수익률 |
| `peerCount` | 측정 성공 peer 수 |
| `peerMeanRet` | peer 60d 평균 |
| `peerDispersion` | peer pstdev |
| `phase` | converging / normal / diverging / insufficient |

## 연계 절차

1. recipes.technical.sectorRelativeStrength — 자기 종목 vs sector index 비교.
2. recipes.macro.betaPeerScreen — peer set 의 macroBeta outlier 점검.

## 기본 검증

- peer 측정 < 5 → phase=insufficient.
- 단일 outlier peer 가 dispersion 좌우하는지 별도 확인 권장.
- peer 정의 (sub-industry vs 산업 전체) 답변에 명시.
