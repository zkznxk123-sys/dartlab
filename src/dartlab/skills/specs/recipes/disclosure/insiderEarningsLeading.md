---
id: recipes.disclosure.insiderEarningsLeading
title: 내부자 매수 클러스터 → 다음 분기 어닝 surprise 선행지표
category: recipes
kind: recipe
scope: builtin
status: drafted
purpose: 내부자 (임원·5% 이상 주주) 매수 거래가 *클러스터* 형태 (180 일 안 ≥ 3 명 동시) 일 때만 다음 분기 EPS surprise 와 양의 IC 가진다는 Cohen-Malloy-Pomorski (2012) "Decoding Inside Information" 결과 적용. 단순 net-buy 가 아닌 *집단 매수 동시성* 이 핵심. gather ↔ quant ↔ analysis 격리 메우는 조합. 트리거 — '내부자 매수 클러스터', 'insider cluster signal'.
whenToUse:
  - 내부자 매수 클러스터
  - insider cluster signal
  - 내부자 surprise 선행
  - cluster timing
linkedSkills:
  - engines.company
  - engines.gather
  - engines.quant
  - engines.analysis
toolRefs:
  - EngineCall
  - RunPython
requiredEvidence:
  - skillRef
  - tableRef
  - valueRef
  - dateRef
visualRefs:
  - "engines.viz.evidenceCoverage"
  - "engines.viz.mermaidDiagram"
visualGuidance:
  - "근거 충족도는 engines.viz.evidenceCoverage로 검산/한계 섹션에만 배치하고 결론 차트처럼 해석하지 않는다."
  - "메커니즘 diagram은 engines.viz.mermaidDiagram으로 8노드 이하만 만들고 모든 edge에 문장·수치·sourceRef 근거를 둔다."

runtimeCompatibility:
  server:
    status: supported
  localPython:
    status: supported
  pyodide:
    status: limited
gap:
  primary:
    - gather
    - quant
  secondary:
    - analysis
testUniverse:
  market: KR
  stockCodes:
    - "005930"
    - "000660"
    - "035420"
    - "051910"
    - "055550"
  asOfPolicy: latest
falsifier:
  description: cluster ≥ 3 인 종목의 다음 분기 surprise IC 가 < 0.05 면 신호 약함
  pythonCheck: |
    assert ic_of(cluster_signal, forward_surprise) >= 0.05
expectedNovelty:
  - clusterDensity
  - clusterFlag
  - icEstimate
forbidden:
  - 단일 거래 (1 명 매수) 로 신호 단정 금지 — 클러스터 (≥ 3 명 / 180 일) 만 유효.
  - 자사주 매입 / 파생 동시 행사는 net-buy 라도 information 가치 약함.
failureModes:
  - 내부자 정의 (임원만 vs 임원+주주) 별 cluster 임계 다름.
  - 분기 surprise 정의 (consensus vs trailing) 차이.
examples:
  - 삼성전자 180 일 내부자 cluster + Q1 surprise IC
  - 셀트리온 cluster 신호 다음 분기 EPS
lastUpdated: '2026-05-13'
---

## 공개 호출 방식

```python
import dartlab
import polars as pl
from datetime import datetime, timedelta

c = dartlab.Company("005930")

# 1. 180 일 내부자 거래
insider = c.gather("insiderTrading", days=180) if hasattr(c, "gather") else None
if isinstance(insider, pl.DataFrame) and not insider.is_empty():
    insider_df = insider
elif isinstance(insider, list):
    insider_df = pl.DataFrame(insider)
else:
    insider_df = pl.DataFrame({"reporter": [], "tradeType": [], "shares": [], "tradeDate": []})

# 2. 매수 거래 (tradeType="매수") 만 — net buy 분리
buys = insider_df.filter(pl.col("tradeType") == "매수") if "tradeType" in insider_df.columns else pl.DataFrame()
unique_buyers = buys["reporter"].n_unique() if "reporter" in buys.columns else 0
total_buy_shares = float(buys["shares"].sum()) if "shares" in buys.columns and not buys.is_empty() else 0
cluster_density = unique_buyers / 180  # buyers per day window

# 3. Cohen-Malloy-Pomorski cluster 임계 — ≥ 3 unique buyers in 180d
cluster_flag = unique_buyers >= 3

# 4. recent 8 분기 EPS surprise 시계열
surprise = c.quant("surprise") if hasattr(c, "quant") else None
recent_surprises = surprise.get("recentSurprises", []) if isinstance(surprise, dict) else []
mean_surprise = sum(recent_surprises) / len(recent_surprises) if recent_surprises else 0

# 5. predictionSignal feature 입력 + IC 추정 (1 차 wave: cluster_flag 가 단조 증가하는 surprise 와 동행하는지)
signal = c.analysis("predictionSignal", "예측신호") if hasattr(c, "analysis") else None
ic_estimate = signal.get("clusterSurpriseIc", 0) if isinstance(signal, dict) else 0

emit_result(
    table=[{
        "stockCode": "005930",
        "windowDays": 180,
        "uniqueBuyers": unique_buyers,
        "totalBuyShares": int(total_buy_shares),
        "clusterDensity": round(cluster_density, 4),
        "clusterFlag": cluster_flag,
        "recentSurpriseMean": round(mean_surprise, 4),
        "icEstimate": round(ic_estimate, 4),
    }],
    values={"clusterFlag": cluster_flag, "uniqueBuyers": unique_buyers, "icEstimate": ic_estimate},
    date="2024-12-31",
)
```

## 호출 동작

1. `c.gather("insiderTrading", days=180)` — 180 일 내부자 거래 시계열.
2. tradeType="매수" 필터 → unique reporter 수.
3. unique buyers ≥ 3 → cluster flag True.
4. `c.quant("surprise")` — 최근 8 분기 EPS surprise.
5. predictionSignal feature 입력 → IC estimate.

## 대표 반환 형태

`pl.DataFrame` — 컬럼:
- `windowDays : int` (default 180)
- `uniqueBuyers : int`
- `totalBuyShares : int`
- `clusterDensity : float`
- `clusterFlag : bool`
- `recentSurpriseMean : float`
- `icEstimate : float` — IC of cluster_flag vs forward 1Q surprise

## 연계 절차

1. 본 recipe → cluster signal 보유 종목 식별.
2. clusterFlag = True → `recipes.disclosure.filingTextSignal` 과 결합 — MD&A tone change 동행 검증.
3. universe 검증은 `recipes.credit.distressCandidateScreen` 의 inverse — cluster + low distress = 강한 매수 신호.
