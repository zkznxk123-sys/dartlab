---
id: recipes.news.newsImpact
title: 단일 사건 → CAR + t-stat + 동기간 뉴스 컨텍스트
category: recipes
kind: recipe
scope: builtin
status: drafted
graphTier: L2
cluster: news
purpose: 종목 단일 사건일 (DART 공시 or 외부 이벤트) 의 |abnormal return| 누적값 CAR (event window) 과 estimation window 시장 모델 잔차 σ 기반 t-stat 산출. 동기간 ±N 일 뉴스 헤드라인 keyword 매칭 컨텍스트 동행. MacKinlay 1997 표준. 추론 sentiment 라벨 X — 정량 CAR/t-stat 만. 트리거 — 'CAR event study', '단일 사건 영향', 'newsImpact'.
whenToUse:
  - DART 공시 사건 가격 영향 정량
  - CAR 1.96 유의 검정
  - 사건 ± 뉴스 컨텍스트 한 번에
examples:
  - 005930 2024-10-08 사건일 CAR t-stat 확인
  - 사건 (-1, +5) 윈도우 abnormal return + 동기간 뉴스 5건
expectedOutputs:
  - car / carPct 단일값 + t-stat + isSignificant
  - alpha / beta / sigma 시장 모델 추정
  - event window 일별 AR 시계열
  - 동기간 ±3 일 뉴스 헤드라인 (title/url/sentiment_score)
linkedSkills:
  - engines.quant
  - engines.gather
  - recipes.news.eventTimelineFusion
  - recipes.news.priceShockNews
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
  - eventCarTstat
  - eventNewsContext
falsifier:
  description: "estimation window (-120, -30) 가 부족하거나 (history < 50일) eventDate 가 전체 윈도우 밖이면 결과 error 키. CAR 의 t-stat |t| < 1.96 = 통계 비유의 → '사건 영향 확인됨' 단정 금지."
forbidden:
  - 비유의 t-stat 으로 사건 영향 단정 금지
  - estimation window 부족시 CAR 단일값 단정 금지
failureModes:
  - history < 50 일 (시장 모델 부족)
  - eventDate 가 ohlcv 범위 밖
  - benchmark (KOSPI/SPY) 결합 누락
lastUpdated: '2026-05-28'
---

## 공개 호출 방식

```python
from dartlab.analysis.eventStudy.newsImpact import newsImpact

result = newsImpact(
    stockCode="005930",
    eventDate="2024-10-08",
    market="KR",
    eventWindow=(-1, 5),
    estimationWindow=(-120, -30),
)

if "error" in result:
    print("계산 불가:", result["error"])
else:
    print(f"CAR: {result['carPct']:.2f}% (t={result['tStat']:.2f})")
    print(f"유의: {result['isSignificant']}")
    print(f"동기간 뉴스 {result['n_news']}건")
```

## 출력 schema

`newsImpact()` 결과 dict 의 핵심 키:

| key | 의미 |
|---|---|
| `car` / `carPct` | 누적 abnormal return (점수 / %) |
| `tStat` | standardized CAR (|t|>1.96 = 5% 유의) |
| `alpha` / `beta` / `sigma` | 시장 모델 OLS 추정 |
| `ar` | event window 일별 AR (list[float]) |
| `news` | 동기간 ±3 일 헤드라인 (list[dict]) |
| `interpretation` | 한국어 요약 |

## 한계

- estimation window (-120, -30) 가 부족하면 (history < 50 일) error 반환. 짧은 IPO 종목 제외.
- benchmark 시장 지수와 거래일 join 후 50 일 미만이면 결과 신뢰 X.
- t-stat 비유의 시 사건 영향 확인되지 않은 것 — "영향 작다" 추론 금지 (검정 부정 아님).

## 연계 절차

1. 본 recipe → 이벤트 전후 abnormal return (CAR / t-stat) 측정.
2. `engines.gather` 뉴스 archive + `engines.quant` market model 결합.
3. `recipes.news.priceShockNews` 의 shock 일자 → 본 recipe 로 임팩트 정량화.
4. `recipes.news.eventTimelineFusion` 으로 이벤트 타임라인 결합.
