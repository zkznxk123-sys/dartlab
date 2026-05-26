---
id: recipes.news.newsHeadlineVelocity
title: 뉴스 헤드라인 빈도 가속 (7/30 일 분당 비율)
category: recipes
kind: recipe
scope: builtin
status: tested
graphTier: L1.5
cluster: news
purpose: 종목 news gather row 의 7 일 / 30 일 발생 빈도를 일평균 단위로 환산. 단기 일평균 / 장기 일평균 비율로 *뉴스 가속도* 측정. 추론 라벨 (긍정/부정) 없이 빈도 정량만. news gather 단일.
whenToUse:
  - 뉴스 빈도 가속
  - news velocity
  - 헤드라인 폭증
  - news pulse
examples:
  - 005930 뉴스 빈도가 평소보다 높나
  - 헤드라인 폭증 종목 — 7일 / 30일 비율
  - 뉴스 가속도 신호
expectedOutputs:
  - 7d 일평균 헤드라인 수 + 30d 일평균
  - 가속 비율 (7d / 30d) 단일값
  - 가속 / 감속 / 평상 라벨 (비율 임계 1.5x)
linkedSkills:
  - engines.gather
  - recipes.news.eventTimelineFusion
  - recipes.news.repeatedHeadlineFrequency
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
  - newsVelocityRatio
  - shortLongFrequencyGap
falsifier:
  description: "news row 가 < 5 면 일평균 비율 계산 불안정 → 결론 X. 중복 헤드라인 (자동 재배포) 가중치 보정 없이 빈도 단정하면 실패."
forbidden:
  - 가속도 자체로 호재/악재 라벨 단정 금지
  - 자동 재배포 중복 헤드라인 가중치 보정 안 한 결과로 단정 금지
failureModes:
  - news row < 5 (커버리지 부족)
  - 자동 재배포 중복 row 가 빈도 과대 측정
  - 30 일 < 60 day-old row 일 때 장기 베이스 불안정
lastUpdated: '2026-05-23'
---

## 공개 호출 방식

```python
import dartlab
import polars as pl
from datetime import datetime, date, timedelta

target = "005930"
c = dartlab.Company(target)

try:
    news_df = c.gather("news").head(500)
    news_rows = news_df.to_dicts() if hasattr(news_df, "to_dicts") else []
except Exception:
    news_rows = []

today = date.today()
cutoff_7 = today - timedelta(days=7)
cutoff_30 = today - timedelta(days=30)


def parseDate(v):
    if v is None:
        return None
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    s = str(v)[:10].replace(".", "-").replace("/", "-")
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except Exception:
        return None


dated = []
for r in news_rows:
    d = parseDate(r.get("date") or r.get("publishedAt") or r.get("pubDate"))
    if d is None:
        continue
    dated.append(d)

in_7 = [d for d in dated if d >= cutoff_7]
in_30 = [d for d in dated if d >= cutoff_30]

per_day_7 = len(in_7) / 7.0 if in_7 else 0.0
per_day_30 = len(in_30) / 30.0 if in_30 else 0.0
velocity_ratio = (per_day_7 / per_day_30) if per_day_30 > 0 else None
gap = (per_day_7 - per_day_30) if per_day_30 > 0 else None

phase = "insufficient"
if velocity_ratio is not None:
    if velocity_ratio > 1.5:
        phase = "accelerating"
    elif velocity_ratio < 0.66:
        phase = "decelerating"
    else:
        phase = "steady"

latest_date = str(max(dated)) if dated else str(today)

table = pl.DataFrame(
    [
        {
            "newsTotalScanned": len(news_rows),
            "newsRowsDated": len(dated),
            "rows7d": len(in_7),
            "rows30d": len(in_30),
            "perDay7d": round(per_day_7, 3),
            "perDay30d": round(per_day_30, 3),
            "velocityRatio": velocity_ratio,
            "shortLongGap": gap,
            "phase": phase,
        }
    ]
)

emit_result(
    table=table,
    values={
        "velocityRatio": velocity_ratio,
        "perDay7d": per_day_7,
        "perDay30d": per_day_30,
        "phase": phase,
    },
    date=latest_date,
    sources=["dartlab://gather/news"],
)
```

## 호출 동작

news gather row 에서 일자 파싱 → 7 일 / 30 일 row 카운트 → 일평균 환산 → 단기/장기 비율 (velocityRatio). > 1.5 = 가속, < 0.66 = 감속, 그 외 = steady. 추론 X.

## 대표 반환 형태

| column | 의미 |
|---|---|
| `perDay7d` | 직전 7 일 뉴스 일평균 |
| `perDay30d` | 직전 30 일 뉴스 일평균 |
| `velocityRatio` | perDay7d / perDay30d |
| `shortLongGap` | perDay7d − perDay30d |
| `phase` | accelerating / steady / decelerating / insufficient |

## 연계 절차

1. recipes.news.repeatedHeadlineFrequency — 같은 헤드라인 반복 빈도 = 자동 재배포 보정 입력.
2. recipes.sentiment.priceMomentumGap — news 가속 + price 갭 두 축 동시 확인.

## 기본 검증

- news row < 5 → phase=insufficient.
- 중복 헤드라인 (예: 재배포) 보정 없으면 한계 명시.
- 30 일 row 가 24 일분만 있으면 perDay30 underestimate — 한계 표기.
