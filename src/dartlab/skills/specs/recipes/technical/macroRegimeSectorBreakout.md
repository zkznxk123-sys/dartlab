---
id: recipes.technical.macroRegimeSectorBreakout
title: 매크로 regime × 종목 모멘텀 정합성
category: recipes
kind: recipe
scope: builtin
status: drafted
purpose: KR 기준금리 (BASE_RATE) 90 일 변화 방향과 종목의 60 일 누적 수익률 방향이 정합 (금리 ↓ × 가격 ↑ 또는 금리 ↑ × 가격 ↓) 인지 측정 — 매크로 흐름과 동기화되는 모멘텀 종목 식별. 트리거 — '매크로 regime', '금리 환경 종목', 'macro × momentum 정합'.
whenToUse:
  - 금리 사이클 변화 국면에서 종목 흐름 정합 점검
  - 매크로 흐름 동기화 종목 발굴
  - 매크로 역행 종목 (alignment = -1) 발굴
inputs:
  - stockCode (KR)
outputs:
  - tableRef (code · sectorName · rateShift · ret60 · ret20 · alignment)
  - dateRef (마지막 거래일)
linkedSkills:
  - engines.gather
toolRefs:
  - EngineCall
  - RunPython
requiredEvidence:
  - tableRef
  - dateRef
expectedNovelty:
  - rateShift
  - alignment
  - ret60
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
    5 종목 모두 ret60 같은 부호이면 (전부 + 또는 전부 -) 시장 전체 흐름 — 종목별
    변별력 0. rateShift 가 |x| < 0.1 (= 금리 정체 구간) 이면 alignment 신호 무의미.
  pythonCheck: |
    rets = [r.get("ret60", 0.0) for r in result["table"]]
    rate_shifts = [r.get("rateShift", 0.0) for r in result["table"]]
    if rets:
        signs = {1 if r > 0 else (-1 if r < 0 else 0) for r in rets}
        assert len(signs) >= 2, "ret60 모두 같은 부호 — 종목 변별력 0"
    if rate_shifts:
        assert abs(rate_shifts[0]) >= 0.1, "rateShift 정체 (|x| < 0.1) — alignment 무의미"
runtimeCompatibility:
  server:
    status: supported
  localPython:
    status: supported
  pyodide:
    status: limited
    limitations:
      - HF macro 데이터셋 다운로드 (CORS)
failureModes:
  - macro HF 벌크 데이터 freshness ≤ 어제까지만 (오늘 발표 금리 미반영)
  - rateShift 90 일 윈도우 default — 더 긴 사이클 (1 년) 시그널 다름
  - alignment 는 부호 단순 비교 — 정도 (magnitude) 무시
forbidden:
  - alignment = +1 만으로 매수 결정 — 정합성 ≠ 알파
  - rateShift 와 가격 사이 직접 인과 단정 (혼란 변수 다수)
  - 미국/일본 종목 입력 (KR BASE_RATE 한정)
examples:
  - "금리 인하기 정합 종목"
  - "매크로 regime 역행 종목"
  - "KR base rate × momentum"
lastUpdated: '2026-05-21'
---

## 공개 호출 방식

```python
import dartlab
import polars as pl

code = "005930"
macro_kr = dartlab.gather("macro", "BASE_RATE")
sector = dartlab.gather("sector", code)
px = dartlab.gather("price", code)

# macro regime — 90 일 단위 base rate 변화 (percentage point)
macro_sorted = macro_kr.sort("date").drop_nulls()
if macro_sorted.height >= 90:
    rate_recent = float(macro_sorted["value"][-1])
    rate_90d_ago = float(macro_sorted["value"][-90])
    rateShift = rate_recent - rate_90d_ago
else:
    rate_recent = 0.0
    rateShift = 0.0

# 가격 모멘텀
px_sorted = px.sort("date").select(["date", "close"])
close = px_sorted["close"].drop_nulls()
n = close.len()
if n < 60:
    ret60 = 0.0
    ret20 = 0.0
else:
    last_close = float(close[-1])
    close_60d_ago = float(close[-60])
    close_20d_ago = float(close[-20])
    ret60 = last_close / close_60d_ago - 1 if close_60d_ago > 0 else 0.0
    ret20 = last_close / close_20d_ago - 1 if close_20d_ago > 0 else 0.0

# alignment 산정
rateSign = -1 if rateShift < -0.1 else (1 if rateShift > 0.1 else 0)
priceSign = -1 if ret60 < -0.05 else (1 if ret60 > 0.05 else 0)

if rateSign == 0 or priceSign == 0:
    alignment = 0  # regime 모호 또는 가격 정체
elif rateSign * priceSign < 0:
    alignment = 1  # 금리 ↓ × 가격 ↑ 또는 금리 ↑ × 가격 ↓ → 정합
else:
    alignment = -1  # 금리 흐름과 가격 흐름 같은 방향 (역행)

sectorName = sector["sectorName"][0] if sector.height > 0 else ""

emit_result(
    table=[{
        "code": code,
        "sectorName": str(sectorName),
        "rateShift": round(rateShift, 3),
        "ret60": round(ret60, 4),
        "ret20": round(ret20, 4),
        "alignment": int(alignment),
    }],
    date=str(px_sorted["date"].max()),
    headline={"metric": "ret60", "value": round(ret60, 4)},
)
```

## 호출 동작

1. `gather("macro", "BASE_RATE")` — KR 기준금리 시계열.
2. `gather("sector", code)` — 종목 sectorName.
3. `gather("price", code)` — OHLCV.
4. rateShift = (최근 base rate) - (90 일 전 base rate), percentage point.
5. ret60 = 60 일 누적 수익률.
6. alignment = sign(rateShift) × sign(ret60) 부호 (역방향 = +1 정합).
7. headline = ret60.

## 대표 반환 형태

- `tableRef` — code · sectorName · rateShift · ret60 · ret20 · alignment.
- `dateRef` — 마지막 거래일.

## 연계 절차

1. `engines.gather` — `gather("macro", "BASE_RATE")` KR 기준금리 시계열.
2. `engines.gather` — `gather("sector", code)` 종목 sectorName.
3. `engines.gather` — `gather("price", code)` OHLCV.
4. `runPython` — rateShift + ret60 + alignment 인라인 산출.
5. `recipes.technical.quantTechnicalReview` — 같은 종목 기술적 verdict 결합.
6. `engines.macro` — 본 alignment 결과를 macro cycle 분석 입력으로 연계 (후속 트랙).

## 기본 검증

- alignment = +1 표시는 "매크로 흐름과 정합" — 절대 알파 신호 아님.
- alignment = -1 (역행) 은 매크로 무시하는 강한 종목 흐름 — 더 비싼 정보일 수 있음.
- rateShift 절댓값 < 0.1 이면 alignment 무의미 (regime 모호).
- ret60 분포가 universe 전체 한쪽으로 치우치면 시장 전체 영향 — 본 신호 미적용.

## 한계

- BASE_RATE 단일 매크로 변수 — CPI / USDKRW / M2 등 추가는 별 recipe.
- 90 일 윈도우 default — 사이클 정의에 따라 가변.
- alignment 부호만 — 정합 강도 (z-score 등) 는 후속 변형.
