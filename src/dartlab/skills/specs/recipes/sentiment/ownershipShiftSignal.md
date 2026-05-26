---
id: recipes.sentiment.ownershipShiftSignal
title: 주요주주 보유 변화 신호 (5% 보유공시 누적 변화)
category: recipes
kind: recipe
scope: builtin
status: tested
graphTier: L1.5
cluster: sentiment
purpose: 5% 보유공시 (대량보유 + 임원·주요주주) row 에서 보고자별 보유비율 변화의 정량 격차를 본다. 누적 매수 측 (보유비율 증가) vs 매도 측 (감소) row 수 + 누적 변화량. 추론 라벨 없이 숫자만. ownership gather 단일.
whenToUse:
  - 주요주주 보유 변화
  - ownership shift
  - 5% 보유공시
  - 대량보유 트렌드
examples:
  - 005930 주요주주 보유 변화 누적 어디
  - 5% 보유공시 매수 측 vs 매도 측 격차
  - 대량보유 변동 가장 큰 종목
expectedOutputs:
  - 보고자별 보유비율 변화 표 (시계열)
  - 매수 측 row 수 + 매도 측 row 수 + 누적 변화량 합
  - 보유비율 증감 top 변동 보고자 (절대값 기준)
linkedSkills:
  - engines.gather
  - recipes.sentiment.insiderClusterTiming
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
  - ownershipShiftBalance
  - cumulativeRatioDelta
falsifier:
  description: "보유공시 row 가 적어 (< 5 건) 양/음 row 비교 결론을 내리면 실패. 임원 자기주식 매수와 외부 주주 매수를 한 row 로 묶으면 실패."
forbidden:
  - 단일 보유공시 row 로 sentiment 결론
  - 임원 self purchase 와 외부 institutional 매수 동일시
failureModes:
  - 단기간 (1 분기) row 수 부족
  - 자기주식 처분과 외부 매수 혼동
  - 보유율 변화 + 절대 보유율 혼동
lastUpdated: '2026-05-23'
---

## 공개 호출 방식

```python
import dartlab
import polars as pl

target = "005930"
c = dartlab.Company(target)

try:
    own_df = c.gather("ownership").head(200)
    own_rows = own_df.to_dicts() if hasattr(own_df, "to_dicts") else []
except Exception:
    own_rows = []


def changeOf(r):
    for k in ("changeRatio", "ratioDelta", "deltaRatio", "changePct"):
        v = r.get(k)
        if v is not None:
            try:
                return float(v)
            except Exception:
                continue
    # fallback: 현재 - 직전 보유율
    cur = r.get("currentRatio") or r.get("holdingRatio") or r.get("ratio")
    prev = r.get("previousRatio") or r.get("priorRatio")
    if cur is not None and prev is not None:
        try:
            return float(cur) - float(prev)
        except Exception:
            return None
    return None


delta_rows = []
for r in own_rows:
    d = changeOf(r)
    if d is None:
        continue
    delta_rows.append(
        {
            "date": r.get("date") or r.get("filedAt") or r.get("reportDate"),
            "filer": r.get("filer") or r.get("name") or r.get("reporter") or "?",
            "delta": d,
        }
    )

pos = [r for r in delta_rows if r["delta"] > 0]
neg = [r for r in delta_rows if r["delta"] < 0]
pos_sum = round(sum(r["delta"] for r in pos), 4)
neg_sum = round(sum(r["delta"] for r in neg), 4)
net = round(pos_sum + neg_sum, 4)

latest_date = (
    str(delta_rows[-1]["date"])
    if delta_rows
    else (str(own_rows[-1].get("date") or own_rows[-1].get("filedAt")) if own_rows else None)
)

table = pl.DataFrame(
    [
        {
            "positiveRows": len(pos),
            "negativeRows": len(neg),
            "positiveSumPct": pos_sum,
            "negativeSumPct": neg_sum,
            "netDeltaPct": net,
            "totalRowsScanned": len(own_rows),
        }
    ]
)

emit_result(
    table=table,
    values={
        "netDeltaPct": net,
        "positiveRows": len(pos),
        "negativeRows": len(neg),
    },
    date=latest_date,
    sources=["dartlab://gather/ownership"],
)
```

## 호출 동작

ownership gather row 마다 보유비율 변화 (`changeRatio` / 또는 `currentRatio - previousRatio`) 추출 → 양/음 row 분리 → 누적 변화량 합산. 결과는 양 row 수·음 row 수·누적 +/- 합 + net delta. 추론 X.

## 대표 반환 형태

| column | 의미 |
|---|---|
| `positiveRows` | 보유비율 증가 신고 row 수 |
| `negativeRows` | 감소 신고 row 수 |
| `positiveSumPct` | 증가 row 누적 변화 합 (% 포인트) |
| `negativeSumPct` | 감소 row 누적 변화 합 |
| `netDeltaPct` | 양 + 음 누적 합 (net) |

## 연계 절차

1. recipes.sentiment.insiderClusterTiming — 보유공시 트렌드 + 내부자 cluster 시점 비교.
2. recipes.fundamental.governance.audit — 대량보유 신고자 풀의 governance 영향 점검.

## 기본 검증

- row 수 < 5 면 결론 X — coverage 한계만 표기.
- 자기주식 처분 row 는 외부 주주 매수와 분리해서 해석.
- 보유율 변화 (pp) ↔ 보유율 (%) 단위 혼동 주의.
