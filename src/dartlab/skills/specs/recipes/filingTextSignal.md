---
id: recipes.filingTextSignal
title: 8-K / 사업보고서 비정상 키워드 빈도 → predictionSignal feature
category: recipes
kind: recipe
scope: builtin
status: drafted
purpose: 최근 365 일 공시 본문에서 "going concern" / "의견거절" / "거짓서명" / "계속기업" 같은 위험 키워드 빈도가 trailing 3y baseline 대비 z-score ≥ 2 이면 비정상 신호. predictionSignal feature 로 입력. Loughran-McDonald sentiment 의 일반 dictionary 와 다른 anomaly-on-rare-keywords 접근. search/edgar ↔ analysis 격리 메우는 조합. 트리거 — 'filing text signal', '공시 키워드 anomaly', '사업보고서 위험 신호'.
whenToUse:
  - filing text signal
  - 공시 키워드 anomaly
  - 위험 키워드 빈도
  - going concern signal
linkedSkills:
  - engines.gather.collect
  - engines.search
  - engines.analysis.predictionSignal
toolRefs:
  - EngineCall
  - RunPython
requiredEvidence:
  - skillRef
  - tableRef
  - valueRef
  - dateRef
runtimeCompatibility:
  server:
    status: supported
  localPython:
    status: supported
  pyodide:
    status: limited
gap:
  primary:
    - search
    - analysis
  secondary:
    - gather
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
  description: "anomaly z > 2 인 종목의 forward 90d drawdown 이 base 종목보다 크지 않으면 신호 무효"
  pythonCheck: |
    assert forward_90d_drawdown(z_high) > forward_90d_drawdown(z_low)
expectedNovelty:
  - keywordZScore
  - anomalyFlag
forbidden:
  - 단일 키워드 빈도 1 회 등장만으로 신호 단정 금지.
  - rare 키워드 dictionary 가 회사 산업 별 baseline 다름 — universal dictionary 강행 X.
failureModes:
  - 한국 공시 본문 OCR / parsing 품질이 회사 별 차이 — 키워드 매칭 누락.
  - 보일러플레이트 (감사보고서 표준 문구) 가 안전 공시에서도 등장 — false positive.
examples:
  - 삼성전자 365 일 공시 anomaly z
  - HMM going concern 빈도 추세
lastUpdated: '2026-05-10'
---

## 공개 호출 방식

```python
import dartlab
import polars as pl
import statistics

c = dartlab.Company("005930")

# 1. 365 일 공시 list
filings_recent = c.gather("collect", days=365) if hasattr(c, "gather") else []
if isinstance(filings_recent, pl.DataFrame):
    recent_list = filings_recent.to_dicts()
elif isinstance(filings_recent, list):
    recent_list = filings_recent
else:
    recent_list = []

# 2. trailing 3y baseline (1095 일 ~ 365 일)
baseline_filings = c.gather("collect", days=1095) if hasattr(c, "gather") else []
if isinstance(baseline_filings, pl.DataFrame):
    baseline_list = baseline_filings.to_dicts()
elif isinstance(baseline_filings, list):
    baseline_list = baseline_filings
else:
    baseline_list = []

# 3. 위험 키워드
RISK_KEYWORDS = ["going concern", "계속기업", "의견거절", "거짓서명", "감사인 변경", "매각 검토"]

def count_keyword(filings, keyword):
    return sum(1 for f in filings if isinstance(f, dict) and keyword in str(f.get("title", "") + f.get("body", "")))

results = []
for kw in RISK_KEYWORDS:
    recent_count = count_keyword(recent_list, kw)
    # baseline 365 일 단위로 normalize (baseline 3y → 1 년 평균).
    baseline_count_yearly = count_keyword(baseline_list, kw) / 3
    baseline_stdev = max(1.0, baseline_count_yearly ** 0.5)  # Poisson stdev 근사.
    z = (recent_count - baseline_count_yearly) / baseline_stdev
    results.append({
        "keyword": kw,
        "recentCount": recent_count,
        "baselineYearly": round(baseline_count_yearly, 2),
        "keywordZScore": round(z, 2),
        "anomalyFlag": z >= 2,
    })

# 4. 종합 anomaly count
anomaly_count = sum(1 for r in results if r["anomalyFlag"])

emit_result(
    table=results,
    values={"anomalyCount": anomaly_count, "totalKeywords": len(RISK_KEYWORDS)},
    date="2024-12-31",
)
```

## 호출 동작

1. `c.gather("collect", days=365)` — 최근 365 일 공시 list.
2. `c.gather("collect", days=1095)` — 3 년 baseline.
3. 위험 키워드 list (going concern / 의견거절 / 거짓서명 / etc) 빈도 측정.
4. z-score = (recent - baseline_yearly) / Poisson stdev 근사.
5. z ≥ 2 인 키워드 anomaly flag.

## 대표 반환 형태

`pl.DataFrame` — 키워드 별 row:
- `keyword : str`
- `recentCount : int` — 최근 365 일 등장 횟수
- `baselineYearly : float` — 3y 평균 (연간 환산)
- `keywordZScore : float`
- `anomalyFlag : bool` — z ≥ 2

## 연계 절차

1. 본 recipe → 키워드 별 anomaly z-score.
2. anomalyFlag = True 키워드 ≥ 2 → `engines.analysis.predictionSignal` 의 input feature.
3. 동시 발현 → `recipes.disclosureToneToStoryRisk` 와 결합 — story.risk 자동 발행 트리거.
