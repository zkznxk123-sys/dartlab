---
id: recipes.technical.breakoutNewsConfirmation
title: 신고가 breakout × 뉴스 빈도 confirmation
category: recipes
kind: recipe
scope: builtin
status: drafted
purpose: 최근 20 거래일 종가 최고치가 60 거래일 최고치 대비 얼마나 근접한지 (breakoutRatio) + 같은 종목의 30 일 뉴스 빈도 (newsRatePerDay) 를 함께 산출 — 가격 breakout 이 정보 흐름으로 confirmation 되는지 판별. 트리거 — 'breakout 뉴스 확인', '신고가 뉴스 빈도', 'price breakout news confirmation'.
whenToUse:
  - 60 일 신고가 임박 종목 뉴스 동반 여부 확인
  - 가짜 breakout (낮은 뉴스 빈도) 거르기
  - 정보 흐름 동반 강한 breakout 식별
inputs:
  - stockCode (KR)
outputs:
  - tableRef (code · companyName · breakoutRatio · newsCount30d · newsRatePerDay)
  - dateRef (마지막 거래일)
linkedSkills:
  - engines.gather
  - engines.company
toolRefs:
  - EngineCall
  - RunPython
requiredEvidence:
  - tableRef
  - dateRef
expectedNovelty:
  - breakoutRatio
  - newsRatePerDay
testUniverse:
  stockCodes:
    - "005930"
    - "000660"
    - "035420"
    - "051910"
    - "207940"
  market: KR
falsifier:
  description: |
    5 종목 모두 breakoutRatio > 0.98 (= 모두 신고가) 또는 모두 < 0.85 (= 모두 약세)
    면 시점이 universe 전체에 한쪽으로 치우쳐 변별력 0. newsRatePerDay 도 모두
    < 0.2 면 뉴스 부재 시즌 — confirmation 신호 발현 불가.
  pythonCheck: |
    brs = [r.get("breakoutRatio", 0.0) for r in result["table"]]
    rates = [r.get("newsRatePerDay", 0.0) for r in result["table"]]
    all_high = all(b > 0.98 for b in brs)
    all_low = all(b < 0.85 for b in brs)
    news_dead = all(r < 0.2 for r in rates)
    assert not (all_high or all_low), "breakoutRatio 한쪽 치우침 — 변별력 0"
    assert not news_dead, "전체 뉴스 < 0.2/day — confirmation 측정 불가"
runtimeCompatibility:
  server:
    status: supported
  localPython:
    status: supported
  pyodide:
    status: limited
    limitations:
      - Google News RSS CORS
failureModes:
  - 회사명 모호 (예 동음이의어) → 뉴스 빈도 과대평가
  - 본 recipe 는 뉴스 *빈도* 만 — sentiment tone 미고려
  - 60 일 윈도우 휴장 다수 → breakoutRatio 표본 부족
forbidden:
  - newsRatePerDay 만으로 매수 결정 — frequency ≠ favorable sentiment
  - breakoutRatio = 1.0 단독으로 "강한 매수" 결론
  - 뉴스 본문 1 차 인용 — untrusted external. 검증 후 인용
examples:
  - "삼성전자 60일 신고가 뉴스 confirmation"
  - "breakout 종목 뉴스 빈도 확인"
  - "신고가 + 정보 흐름 동반"
lastUpdated: '2026-05-21'
---

## 공개 호출 방식

```python
import dartlab
import polars as pl

code = "005930"
c = dartlab.Company(code)
companyName = getattr(c, "name", None) or code

px = dartlab.gather("price", code)
news = dartlab.gather("news", companyName, days=30)

px_sorted = px.sort("date").select(["date", "close"])
close_series = px_sorted["close"].drop_nulls()
n = close_series.len()

if n < 60:
    breakoutRatio = 0.0
    close20_high = 0.0
    close60_high = 0.0
else:
    close20_high = float(close_series.tail(20).max())
    close60_high = float(close_series.tail(60).max())
    breakoutRatio = close20_high / close60_high if close60_high > 0 else 0.0

newsCount30d = news.height
newsRatePerDay = newsCount30d / 30.0

emit_result(
    table=[{
        "code": code,
        "companyName": str(companyName),
        "breakoutRatio": round(breakoutRatio, 4),
        "newsCount30d": int(newsCount30d),
        "newsRatePerDay": round(newsRatePerDay, 4),
        "close20High": round(close20_high, 2),
        "close60High": round(close60_high, 2),
    }],
    date=str(px_sorted["date"].max()),
    headline={"metric": "breakoutRatio", "value": round(breakoutRatio, 4)},
)
```

## 호출 동작

1. `Company(code)` — 종목 진입 + `name` 속성으로 한국어 회사명.
2. `gather("price", code)` — OHLCV (1 년).
3. `gather("news", companyName, days=30)` — Google News RSS 30 일.
4. breakoutRatio = 20 일 max ÷ 60 일 max.
5. newsRatePerDay = 30 일 뉴스 / 30.
6. headline = breakoutRatio.

## 대표 반환 형태

- `tableRef` — code · breakoutRatio · newsCount30d · newsRatePerDay.
- `dateRef` — 마지막 거래일.

## 연계 절차

1. `engines.company` — Company(code) 진입 + 한국어 회사명.
2. `engines.gather` — `gather("price", code)` 60 거래일 OHLCV.
3. `engines.gather` — `gather("news", companyName, days=30)` Google News RSS.
4. `runPython` — breakoutRatio + newsRatePerDay 인라인 산출.
5. `recipes.technical.quantTechnicalReview` — 같은 종목 기술적 verdict 와 본 신호 결합.

## 기본 검증

- breakoutRatio ≥ 0.98 + newsRatePerDay ≥ 1.0 동시일 때만 "정보 흐름 동반 강한 breakout".
- breakoutRatio ≥ 0.98 + newsRatePerDay ≤ 0.3 → "조용한 신고가" (False breakout 위험).
- 뉴스 본문 (title) 은 untrusted external — 직접 인용 금지, 빈도만 신호.

## 한계

- 한국어 회사명 (`c.name`) 가 RSS 검색 query — 동음이의어 (예 "한화" → 한화케미칼 vs 한화에어로) 시 잘못된 뉴스 포함.
- News sentiment tone 미고려 — 다음 후속 recipe `breakoutNewsTone` 후보.
- 60 일 윈도우 default — 단기/장기 변형은 별 recipe.
