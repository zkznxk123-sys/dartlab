---
id: recipes.news.priceShockNews
title: "|AR|>3σ 가격 shock 자동 검출 + 인접 뉴스 컨텍스트"
category: recipes
kind: recipe
scope: builtin
status: drafted
graphTier: L2
cluster: news
purpose: 종목 1 년 일별 abnormal return (market model 잔차) 의 σ 임계 ±k 밖 일자 = shock event 자동 검출. 각 shock 일자에 ±N 일 뉴스 헤드라인 keyword 매칭 컨텍스트 + 옵션 newsImpact 위임으로 CAR/t-stat 동행. "왜 -5% 빠졌지" 사후 답함. 추론 sentiment 라벨 X — shock direction (up/down) + z-score 정량만. 트리거 — '왜 빠졌나', 'shock event 검출', 'priceShockNews', '가격 → 뉴스 역방향'.
whenToUse:
  - 가격 급변 일자 자동 검출
  - shock 사후 원인 뉴스 매칭
  - "왜 +/- N% 움직였나 질문"
examples:
  - 005930 1 년 |AR|>3σ shock 일자 + 인접 뉴스
  - 가격 급락 일자 + 그날 공시·뉴스 컨텍스트
  - 3σ 외 일자 자동 마커 (UI chart 동행)
expectedOutputs:
  - n_shocks + threshold_sigma + sigma_obs
  - shock_events (list) — date / ar / z_score / direction / is_significant / news (list)
  - 옵션 computeImpact=True → 각 shock 의 CAR / t-stat 추가
linkedSkills:
  - engines.quant
  - engines.gather
  - recipes.news.newsImpact
  - recipes.news.eventTimelineFusion
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
expectedNovelty:
  - shockReverseScan
  - shockNewsContext
falsifier:
  description: "history < 30 일 또는 AR variance = 0 (변동성 0) 이면 error. thresholdSigma 10 같은 극단 임계는 noise-only 데이터에서 n_shocks=0 정상. 검출된 shock 에 매칭 news 0 건이면 '뉴스 원인 없음' 단정 금지 — keyword 미스 또는 archive 누락 가능."
forbidden:
  - 매칭 뉴스 0 건으로 원인 부재 단정 금지
  - shock direction 으로 sentiment 라벨 단정 금지
failureModes:
  - history < 30 일 또는 estimation window 부족
  - AR variance 0 (정지 종목)
  - news archive Phase A/D 미실행 시 컨텍스트 0
lastUpdated: '2026-05-28'
---

## 공개 호출 방식

```python
from dartlab.analysis.eventStudy.priceShockNews import priceShockNews

result = priceShockNews(
    stockCode="005930",
    market="KR",
    periodDays=365,
    thresholdSigma=3.0,
    newsContextDays=3,
    computeImpact=False,  # True 면 각 shock CAR/t-stat 위임
)

print(f"{result['n_shocks']} shocks (σ={result['sigma_obs']:.4f})")
for ev in result["shock_events"]:
    print(f"  {ev['date']}: {ev['direction']} {ev['ar_pct']}% (z={ev['z_score']}) — 뉴스 {ev['n_news']}건")
```

## 출력 schema

| key | 의미 |
|---|---|
| `n_shocks` | 검출된 shock 개수 |
| `threshold_sigma` / `sigma_obs` | 임계 × σ |
| `alpha` / `beta` | market model (전체 윈도우 lstsq) |
| `shock_events[i].direction` | "up" / "down" |
| `shock_events[i].z_score` | AR / σ |
| `shock_events[i].news` | 인접 ±3 일 keyword 매칭 헤드라인 |

## L4 UI 차트 연동

`/analysis/$code/events` (PriceEventChart) 가 본 결과를 직접 소비 — `is_significant` shock 은 빨강 (up) / 파랑 (down) 깃발 마커로 차트 상단 표시. 클릭 시 EventSidePanel Sheet 에 동일 dict 의 news 컨텍스트 노출.

## 연계 절차

1. 본 recipe → |AR|>3σ 가격 shock 일자 자동 검출 + 인접 뉴스 컨텍스트.
2. `engines.gather` 뉴스 archive + `engines.quant` market model (abnormal return) 결합.
3. shock 일자 → `recipes.news.newsImpact` 로 CAR / t-stat 임팩트 정량화.
4. `recipes.news.eventTimelineFusion` 으로 이벤트 타임라인 결합.
