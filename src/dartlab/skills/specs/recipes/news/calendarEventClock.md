---
id: recipes.news.calendarEventClock
title: 이벤트 캘린더 시계 (예정 IR/실적/배당락 + 잔여일)
category: recipes
kind: recipe
scope: builtin
status: tested
graphTier: L1.5
cluster: news
purpose: 향후 예정된 IR/실적발표/배당락/주주총회 row 를 받아 잔여일 기준으로 정렬. 7 일 / 14 일 / 30 일 anchor 안 진입 row 카운트. 추론 라벨 없이 *시점 표면화* 만. calendar gather 단일.
whenToUse:
  - 이벤트 캘린더
  - event clock
  - 예정 실적 IR
  - 배당락 잔여일
  - calendar bracket
examples:
  - 005930 다음 실적 발표 며칠 남았어
  - 배당락 / 주총 / IR 예정 이벤트 잔여일
  - 7일 / 14일 / 30일 안 도래 이벤트 카운트
expectedOutputs:
  - 예정 이벤트 list (제목 + 잔여일 + 종류)
  - 7d / 14d / 30d bucket 별 이벤트 카운트
  - 가장 가까운 이벤트 단일 (제목 + 잔여일)
linkedSkills:
  - engines.gather
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
    - "000660"
expectedNovelty:
  - eventBracketCounts
  - daysUntilEarliest
falsifier:
  description: "calendar gather row 가 0 이면 결론 X. 추정 일자 (TBD 텍스트) 를 확정일로 처리하면 실패."
forbidden:
  - 잔여일을 매수/매도 결정으로 단정 금지
  - 과거 (이미 지난) 이벤트 row 를 미래 이벤트로 처리 금지
failureModes:
  - calendar row 텍스트 형식 변형 (날짜 파싱 실패)
  - TBD / 추정 표기를 확정일로 오인
  - 휴장일 기준 vs 캘린더일 기준 혼동
lastUpdated: '2026-05-23'
---

## 공개 호출 방식

```python
import dartlab
import polars as pl
from datetime import datetime, date

target = "005930"
c = dartlab.Company(target)

try:
    cal_df = c.gather("calendar").head(200)
    cal_rows = cal_df.to_dicts() if hasattr(cal_df, "to_dicts") else []
except Exception:
    cal_rows = []

today = date.today()


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


events = []
for r in cal_rows:
    d = parseDate(r.get("date") or r.get("eventDate") or r.get("scheduledAt"))
    if d is None:
        continue
    if d < today:
        continue
    days_until = (d - today).days
    events.append(
        {
            "date": str(d),
            "daysUntil": days_until,
            "type": str(r.get("type") or r.get("eventType") or "unknown"),
            "title": str(r.get("title") or r.get("name") or r.get("description") or ""),
        }
    )

events.sort(key=lambda r: r["daysUntil"])
in_7 = [r for r in events if r["daysUntil"] <= 7]
in_14 = [r for r in events if r["daysUntil"] <= 14]
in_30 = [r for r in events if r["daysUntil"] <= 30]
earliest = events[0]["daysUntil"] if events else None
latest_date = events[-1]["date"] if events else str(today)

table = pl.DataFrame(events) if events else pl.DataFrame(
    schema={"date": pl.Utf8, "daysUntil": pl.Int64, "type": pl.Utf8, "title": pl.Utf8}
)

emit_result(
    table=table,
    values={
        "eventsTotal": len(events),
        "in7d": len(in_7),
        "in14d": len(in_14),
        "in30d": len(in_30),
        "daysUntilEarliest": earliest,
    },
    date=latest_date,
    sources=["dartlab://gather/calendar"],
)
```

## 호출 동작

### 1. 결론 도출

events bucket 카운트 + earliest 단정. 예: "events total=12 / in7d=2 (실적발표 + 배당락 D-3) / in14d=4 (+IR + 주총 추가) / in30d=8 / daysUntilEarliest=3 (다음 실적발표) → 7d 안 2 이벤트 도래 (실적 + 배당락 동시 → 단기 가격 변동 가능 시점)."

### 2. 핵심 근거 수집

- Company.gather('calendar') latest 200 row
- 각 row 의 date / eventDate / scheduledAt 파싱
- 오늘 기준 미래 row 만 (daysUntil ≥ 0)
- 7d / 14d / 30d bucket 카운트

### 3. 메커니즘 분석

```
calendar 200 rows → date 파싱 → daysUntil 계산
   d < today → 제외 (과거 이벤트)
   d ≥ today → events list 추가
   ↓
정렬 + bucket 카운트:
   in7d  = daysUntil ≤ 7 row 수
   in14d = daysUntil ≤ 14 row 수
   in30d = daysUntil ≤ 30 row 수
   earliest = events[0] (가장 가까운 이벤트)
   ↓
시점 표면화 (추론 X):
   "다음 IR 5일 / 다음 실적 7일 / 배당락 10일 후"
   → 시점 자체만 정량 사실
   → 매수/매도 결정 단정 금지 (forbidden)
```

calendar = *시점 표면화* — 추론 라벨 X. 잔여일 자체가 정량 사실. 7d/14d/30d bucket 은 트레이딩 window 기준.

### 4. 반례·한계

- calendar row 0 → 결론 X (coverage 한계).
- 'TBD' / 추정 일자 → parseDate 실패 → events 에서 제외 (강제).
- 잔여일 음수 (과거 이벤트) → 미래 이벤트로 처리 시 forbidden.
- 휴장일 기준 vs 캘린더일 기준 혼동 (실제 거래일 ≠ 캘린더 7일).

### 5. 후속 모니터링

- in7d ≥ 2 → `recipes.news.eventTimelineFusion` 으로 이벤트 시점 ± 가격 반응 결합.
- earliest = earnings → `recipes.fundamental.disclosure.eventRadar.eventInbox` 로 실적 인박스.
- earliest = dividend ex-date → `recipes.fundamental.dividend.payoutFcfCoverage` 로 배당 sustainability.

## 대표 반환 형태

| column | 의미 |
|---|---|
| `date` | 이벤트 일자 |
| `daysUntil` | 오늘 기준 잔여일 |
| `type` | 이벤트 종류 (IR/earnings/dividend ex-date 등) |
| `title` | row 본문 |

## 연계 절차

1. recipes.news.eventTimelineFusion — 이벤트 시점 ± 가격 반응 결합.
2. recipes.fundamental.disclosure.event — 예정 이벤트 카테고리별 본문 점검.

## 기본 검증

- calendar row 0 → 결론 X.
- 'TBD' / 추정 일자는 events list 에서 제외 (parseDate 실패 → continue).
- 잔여일 음수 row (과거) 는 제외 — 미래만.
