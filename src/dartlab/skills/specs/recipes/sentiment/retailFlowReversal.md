---
id: recipes.sentiment.retailFlowReversal
title: 개인 매매 반전 신호 (외인/기관 vs 개인 z-divergence)
category: recipes
kind: recipe
scope: builtin
status: curated
purpose: 개인 순매수 z-score 와 (외인+기관) 순매수 z-score 의 부호 반대 발산. 두 z 갭 ≥ 3 인 row 는 *스마트머니 vs 개인 반전 점* 후보. sentiment 페르소나 보조.
whenToUse:
  - 개인 매매 반전
  - retail flow reversal
  - 스마트머니 vs 개인
  - 수급 다이버전스
examples:
  - 005930 개인 매수 vs 외인+기관 매도 반전 신호
  - 스마트머니와 개인 자금 방향 발산 종목
  - retail vs institutional flow divergence
expectedOutputs:
  - 개인 z-score + (외인+기관) z-score 시계열
  - 갭 (개인 - 스마트머니) 절대값 ≥ 3 row list
  - 부호 반대 발산 횟수 단일값 (60d window)
linkedSkills:
  - engines.company
  - engines.gather
  - recipes.sentiment.flowImbalance
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
    - gather
    - synth
testUniverse:
  market: KR
  stockCodes:
    - "005930"
    - "000660"
falsifier:
  description: "거래일 < 30 으로 z-score 노이즈. 같은 부호 (둘 다 매수 또는 둘 다 매도) 는 reversal 신호 아님."
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
    flow = c.gather("flow").head(120).to_dicts()
except Exception:
    flow = []
flow.sort(key=lambda r: str(r.get("date") or r.get("tradeDate")))

retail = [float(r.get("individualNet") or 0) for r in flow]
smart = [float(r.get("foreignNet") or 0) + float(r.get("institutionNet") or 0) for r in flow]

WINDOW = 20
rows = []
for i, r in enumerate(flow):
    if i < WINDOW: continue
    r_window = retail[i-WINDOW:i]
    s_window = smart[i-WINDOW:i]
    r_mu, r_sd = statistics.mean(r_window), statistics.stdev(r_window) if len(r_window) > 1 else 0
    s_mu, s_sd = statistics.mean(s_window), statistics.stdev(s_window) if len(s_window) > 1 else 0
    z_r = (retail[i] - r_mu) / r_sd if r_sd > 0 else None
    z_s = (smart[i] - s_mu) / s_sd if s_sd > 0 else None
    rev = "smartBuy_retailSell" if (z_s and z_r and z_s >= 1.5 and z_r <= -1.5) else \
          "smartSell_retailBuy" if (z_s and z_r and z_s <= -1.5 and z_r >= 1.5) else "normal"
    rows.append({"date": r.get("date") or r.get("tradeDate"), "zRetail": z_r, "zSmart": z_s, "reversal": rev})

if rows:
    table = pl.DataFrame(rows)
    rev_n = int((table["reversal"] != "normal").sum())
    latest_date = str(table["date"].max())
else:
    # 윈도우 만족 X — 데이터 부족 표시 + 최신 flow 날짜 표면
    latest_date = str(flow[-1].get("date") or flow[-1].get("tradeDate")) if flow else None
    table = [{"reversal": "insufficient", "date": latest_date, "flowRowsAvailable": len(flow), "windowRequired": WINDOW}]
    rev_n = 0

emit_result(
    table=table,
    values={"reversalCount": rev_n, "rows": (table.height if hasattr(table, "height") else len(table))},
    date=latest_date,
    sources=["dartlab://gather/flow"],
)
```

## 호출 동작

### 1. 결론 도출

reversalCount + z-divergence cluster 단정. 예: "60d 거래일 z-divergence 시계열: 개인 z + (외인+기관) z 부호 반대 row 8건 — 6건 'smartSell_retailBuy' (개인 매수 + 스마트머니 매도, 고점 추격 패턴) + 2건 'smartBuy_retailSell' (개인 매도 + 스마트머니 매수, 저점 매집). reversal 빈도 13% (8/60) — *매매 발산* 강함."

### 2. 핵심 근거 수집

- Company.gather('flow') latest 120 row (60-120 거래일)
- 각 row × (individualNet + foreignNet + institutionNet)
- 20 거래일 rolling z-score: zRetail (개인) + zSmart (외인+기관)
- reversal 분류: 부호 반대 + |z| ≥ 1.5

### 3. 메커니즘 분석

```
flow 120 row → 2 시리즈 (retail / smart)
   smart = foreignNet + institutionNet
   retail = individualNet
   ↓
20 거래일 rolling z-score (각 시리즈):
   zRetail[t] = (retail[t] - mean(retail[t-20:t])) / std
   zSmart[t]  = (smart[t]  - mean(smart[t-20:t]))  / std
   ↓
reversal 판정 (부호 + 크기 조건):
   zSmart ≥ +1.5 + zRetail ≤ -1.5 → smartBuy_retailSell (저점 매집)
   zSmart ≤ -1.5 + zRetail ≥ +1.5 → smartSell_retailBuy (고점 추격)
   부호 같거나 |z| 약함 → normal
   ↓
reversalCount = 60-90d 안 reversal row 수
   ≥ 5 → 매매 발산 빈번 (sentiment 약화 phase)
   < 3 → 정상 매매 (수급 정합)
```

스마트머니 vs 개인 정량 divergence — *스마트머니 = 항상 옳다* 단정 금지. 정량 관찰만. smartSell_retailBuy 다수 = 고점 형성 의심 (historical 패턴), smartBuy_retailSell = 저점 매집 의심.

### 4. 반례·한계

- 거래일 < 30 → z-score 노이즈 → 결론 X.
- 동일 부호 (둘 다 매수) → reversal 아님 (정상 동조).
- 20일 rolling baseline → regime shift 시 z 후행.
- *스마트머니 = 옳다* 단정 → forbidden. 단순 ranking 신호.

### 5. 후속 모니터링

- reversalCount ≥ 5 → `recipes.sentiment.flowImbalance` 로 단일 imbalance 비교.
- smartSell_retailBuy 일관 + 가격 상승 → `recipes.technical.priceVolumeZScore` 로 거래량 z-score 점검.
- reversal 시점 → `recipes.sentiment.consensusRevisionPace` 로 컨센서스 변화 cross-check.

## 대표 반환 형태

| column | 의미 |
|---|---|
| `date` | 거래일 |
| `zRetail` | 개인 순매수 z |
| `zSmart` | (외인+기관) z |
| `reversal` | smartBuy_retailSell / smartSell_retailBuy / normal |

## 연계 절차

1. recipes.sentiment.flowImbalance - 단일 imbalance 와 갭 비교.
2. recipes.sentiment.consensusRevisionPace - reversal 시점 컨센서스 변화.

## 기본 검증

- 거래일 < 30 이면 결론 X.
- 동일 부호 (둘 다 매수 또는 매도) 는 reversal 아님.
- *스마트머니 = 항상 옳다* 단정 금지 — 정량 관찰일 뿐.
