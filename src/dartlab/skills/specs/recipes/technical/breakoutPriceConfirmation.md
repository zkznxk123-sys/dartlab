---
id: recipes.technical.breakoutPriceConfirmation
title: 52주 신고가 돌파율 z-score (breakoutNewsConfirmation v2 변형)
category: recipes
kind: recipe
scope: builtin
status: drafted
purpose: breakoutNewsConfirmation 의 신고가 binary flag 가 universe 강세장 치우침 (5 종 중 3 종 all_high) 으로 변별력 0 였던 문제 보강. v2 는 *binary 신고가* 대신 *돌파 폭 z-score* (현재가 / 52주 고가 - 1) 의 단면 분포 + 거래대금 confirmation 동시 검증. 트리거 — '신고가 돌파', 'breakout confirmation', '신고가 z'.
whenToUse:
  - 신고가 돌파 변별
  - breakout confirmation z
  - 거래대금 동반 돌파
linkedSkills:
  - engines.gather
  - engines.quant
  - recipes.technical.breakoutNewsConfirmation
  - recipes.technical.momentumFlowDivergence
toolRefs:
  - EngineCall
  - RunPython
requiredEvidence:
  - tableRef
  - dateRef
  - sourceRef
expectedOutputs:
  - 종목별 breakoutZ (현재가 / 52주 고가 비율)
  - 거래대금 z (20 거래일 평균 대비)
  - 두 z 동시 ≥ +1 row (confirmed breakout 후보)
runtimeCompatibility:
  server:
    status: supported
  localPython:
    status: supported
  pyodide:
    status: limited
    limitations:
      - Naver flow API 직접 호출 (CORS)
gap:
  primary:
    - gather
    - quant
testUniverse:
  market: KR
  stockCodes:
    - "005930"
    - "000660"
    - "035420"
    - "051910"
    - "207940"
falsifier:
  description: |
    5 종목 모두 confirmed (둘 다 z ≥ +1) 또는 모두 미달이면 변별력 0. v1 의 binary flag
    실패 모드를 v2 가 *분포* 로 변환했는지 검증 — 단면 std 가 0.5 이하면 v2 도 같은 실패.
  pythonCheck: |
    zs = [r["breakoutZ"] for r in result["table"] if r["breakoutZ"] is not None]
    import statistics
    assert len(zs) >= 3 and statistics.stdev(zs) > 0.5, "breakoutZ 단면 std ≤ 0.5 — v1 실패 모드 그대로"
failureModes:
  - 52주 고가 산출 시 분할/액면 보정 누락
  - 거래대금 평균이 1 회성 대규모 거래로 왜곡
  - 종가 close 와 고가 high 컬럼 혼동
forbidden:
  - 신고가 binary flag 단독 사용 (v1 실패 모드 회귀)
  - 거래대금 confirmation 없이 breakoutZ 만으로 결론
examples:
  - 005930 신고가 돌파 z + 거래대금 동반
  - 5 종목 confirmed breakout 후보 단면
lastUpdated: "2026-05-22"
---

## 공개 호출 방식

```python
import dartlab
import polars as pl
import statistics

codes = ["005930", "000660", "035420", "051910", "207940"]

rows = []
for code in codes:
    try:
        px = dartlab.gather("price", code).head(260).to_dicts()
    except Exception:
        px = []
    if not px:
        rows.append({"code": code, "breakoutZ": None, "volZ": None, "confirmed": False})
        continue
    px.sort(key=lambda r: str(r.get("date") or r.get("tradeDate")))
    closes = [float(r.get("close") or r.get("closePrice") or 0) for r in px if (r.get("close") or r.get("closePrice"))]
    highs = [float(r.get("high") or r.get("highPrice") or 0) for r in px if (r.get("high") or r.get("highPrice"))]
    vols = [float(r.get("volume") or r.get("tradingVolume") or 0) * float(r.get("close") or 0) for r in px]
    if len(closes) < 60:
        rows.append({"code": code, "breakoutZ": None, "volZ": None, "confirmed": False})
        continue
    high52 = max(highs[-252:]) if len(highs) >= 60 else max(highs)
    cur = closes[-1]
    breakout_z = (cur / high52 - 1) if high52 > 0 else None
    recent_vol = vols[-1] if vols else 0
    vol_mean = statistics.mean(vols[-20:-1]) if len(vols) > 20 else 0
    vol_std = statistics.stdev(vols[-20:-1]) if len(vols) > 21 else 0
    vol_z = (recent_vol - vol_mean) / vol_std if vol_std > 0 else None
    confirmed = (breakout_z is not None and breakout_z >= -0.005 and vol_z is not None and vol_z >= 1.0)
    rows.append({
        "code": code,
        "breakoutZ": breakout_z,
        "volZ": vol_z,
        "confirmed": confirmed,
    })

table = pl.DataFrame(rows)
confirmed_n = int((table["confirmed"]).sum()) if table.height else 0

emit_result(
    table=table,
    values={"universe": len(codes), "confirmed": confirmed_n},
    date=None,
    sources=["dartlab://gather/price"],
)
```

## 호출 동작

종목별 (1) `breakoutZ = close / max(high, 52주) - 1` (2) 직전일 거래대금의 20 거래일 z-score `volZ` 두 신호 산출. `confirmed = breakoutZ ≥ -0.005 AND volZ ≥ 1.0` — 신고가 근처 + 거래대금 1σ 이상 동반.

## 대표 반환 형태

| column | 의미 |
|---|---|
| `code` | 종목코드 |
| `breakoutZ` | close / 52주 고가 - 1 |
| `volZ` | 직전일 거래대금 20 거래일 z-score |
| `confirmed` | 두 신호 동시 충족 여부 |

## 연계 절차

1. recipes.technical.breakoutNewsConfirmation - v1 (binary flag) 과 비교.
2. recipes.technical.momentumFlowDivergence - 수급 동조성 확인.
3. recipes.sentiment.flowImbalance - 신고가 시점 수급 imbalance.

## 기본 검증

- 표본 거래일 < 60 인 종목은 breakoutZ / volZ 결론 X.
- 52주 고가 산출 시 액면분할·무상증자 보정 row 가 raw 에 반영됐는지 확인 — 미반영 시 한계.
- confirmed 단독으로 매수 결론 X — momentumFlow / sentiment 와 결합 후 thesis.
