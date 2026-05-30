---
id: recipes.sentiment.newsSentimentFactor
title: 뉴스 sentiment cross-section factor + IC + 5분위 spread
category: recipes
kind: recipe
scope: builtin
status: drafted
graphTier: L2
cluster: sentiment
purpose: 시장 전종목 (KRX listing × news archive) lookback news headline 의 평균 sentiment score 를 cross-section factor 로 격상. 종목별 corpName keyword 필터 → mean sentiment → forward return cross-section IC (Pearson + Spearman + t-stat). 5분위 long-short spread 동행. Tetlock 2007 "Giving Content to Investor Sentiment" 표준. 트리거 — 'news sentiment factor', '뉴스 alpha', 'newsSentimentFactor'.
whenToUse:
  - 시장 sentiment factor IC 검증
  - top/bottom 5분위 spread alpha
  - 다른 factor 와의 결합 검증
examples:
  - KR 시장 30 일 lookback newsSentiment IC + 5분위 spread
  - newsSentiment factor 가 PER/PBR 보다 forward 5d 수익 더 잘 정렬하나
expectedOutputs:
  - ic_pearson / ic_spearman / t_stat / is_significant
  - quintile_spread (top - bottom 평균 수익률)
  - n_long / n_short 종목 수
linkedSkills:
  - engines.quant
  - engines.gather
  - recipes.sentiment.priceMomentumGap
  - recipes.news.newsImpact
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
expectedNovelty:
  - newsSentimentFactor
  - sentimentIcSpread
falsifier:
  description: "n_stocks < 10 이면 IC NaN — universe 부족 (archive Phase A/D 미실행 또는 corpName 매칭 0). |t| < 2.0 이면 sentiment alpha 검증 안 됨. 5분위 chunk < 2 면 spread 의미 X. lm_dict 사전만 사용 시 모델 한계 — 'sentiment 결정적' 단정 금지."
forbidden:
  - n_stocks < 10 IC 결과로 alpha 검증 단정 금지
  - lm_dict 단일 모델로 sentiment 의미 단정 금지
failureModes:
  - news archive Phase A/D 미실행
  - KRX listing × archive 매칭 종목 < 10
  - forward return horizon ohlcv 부족
lastUpdated: '2026-05-28'
---

## 공개 호출 방식

```python
from dartlab.quant.factor.newsSentimentFactor import newsSentimentIC

result = newsSentimentIC(
    market="KR",
    lookbackDays=30,
    forwardDays=5,
)

print(f"IC pearson: {result['ic_pearson']:.4f} (t={result['t_stat']:.2f})")
print(f"5분위 spread: {result['quintile_spread']:.4f} (n_long={result['n_long']})")
print(f"유의: {result['is_significant']}")
```

## 출력 schema

| key | 의미 |
|---|---|
| `ic_pearson` / `ic_spearman` | Pearson + Spearman cross-section IC |
| `t_stat` / `is_significant` | t-stat + |t|>2.0 유의 검정 |
| `n_stocks` | universe × forward return 공통 종목 |
| `quintile_spread` | top - bottom 5분위 평균 수익률 |
| `n_long` / `n_short` | 5분위 종목 수 |

## 메모리 가드

- `@withMemoryBudget(500)` — universe build RSS delta 상한
- `BoundedCache _news_sentiment_universe_*` LRU 50 / 400MB
- 기본 `sentimentModel="lm_dict"` — 대량 cross-section CPU 비용 가드

## 한계

- archive 7 일 이내 lookback 은 분산 부족 — 30 일 권장.
- lm_dict 만 사용 시 동음이의·문맥 무시. transformers 모델 (`sentimentModel="auto"`) 은 GPU 권장.
- forward return horizon 너무 길면 (>20 일) IC 약화.

## 연계 절차

1. 본 recipe → news sentiment 팩터 빌드 + IC / 분위 스프레드 검증.
2. `engines.gather` 뉴스 archive + `engines.quant` 팩터 프레임 결합.
3. `recipes.news.newsImpact` 이벤트 임팩트와 교차 검증.
4. `recipes.sentiment.priceMomentumGap` 과 결합해 모멘텀-센티먼트 갭 점검.
