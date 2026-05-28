---
id: recipes.news.newsHeadlineVelocity
title: 뉴스 헤드라인 빈도 가속 (7/30 일 분당 비율)
category: recipes
kind: recipe
scope: builtin
status: curated
graphTier: L1.5
cluster: news
purpose: 종목 news gather row 의 7 일 / 30 일 발생 빈도를 일평균 단위로 환산. 단기 일평균 / 장기 일평균 비율로 *뉴스 가속도* 측정. 추론 라벨 (긍정/부정) 없이 빈도 정량만. news gather 단일. 트리거 — '뉴스 헤드라인 빈도 가속 (7/30 일 분당 비율)', 'news headline velocity', 'newsHeadlineVelocity'.
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
validatedAt: '2026-05-27'
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

### 1. 결론 도출

뉴스 빈도 가속도 phase 단정 (accelerate > 1.5x / steady / decelerate < 0.66x). 예: "7d 일평균 8건 vs 30d 일평균 2.5건 → velocityRatio 3.2x → accelerate (뉴스 빈도 폭증)."

### 2. 핵심 근거 수집

- 종목 뉴스 row (Company.gather('news'))
- 7d 발생 row 카운트 / 7 = 단기 일평균
- 30d 발생 row 카운트 / 30 = 장기 일평균

### 3. 메커니즘 분석

```
news row → date 파싱
   ↓
7일 안 row 수 / 7  = velocity7d
30일 안 row 수 / 30 = velocity30d
   ↓
velocityRatio = velocity7d / velocity30d
   > 1.5    → accelerate (빈도 1.5배 폭증)
   0.66-1.5 → steady (정상)
   < 0.66   → decelerate (관심 이탈)
```

velocityRatio 큼 = 최근 뉴스 폭증. velocityRatio > 3 + 매체 다수 동시 = 사건 큰 가능성. 단순 같은 사건 복수 매체 보도 (`recipes.news.repeatedHeadlineFrequency`) 와 별도 분리 필요.

### 4. 반례·한계

- 같은 사건의 복수 매체 동시 보도 → velocity 부풀려짐.
- 정정·재공시 뉴스 cluster 도 별개 카운트.
- date 파싱 실패 row (이상 format) drop — 실제 빈도보다 낮게 측정.
- 휴장일·공휴일 효과 (월요일 spike) 보정 없음.

### 5. 후속 모니터링

- accelerate phase + 7d 안 ≥ 3 매체: `recipes.news.repeatedHeadlineFrequency` 로 사건 cluster 확인.
- accelerate + 가격 변동 동행: `recipes.news.eventVolatilityCheck` 로 변동성 확대 확인.
- decelerate 지속 (관심 이탈): `recipes.sentiment.flowImbalance` 로 수급 변화 cross-check.

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
