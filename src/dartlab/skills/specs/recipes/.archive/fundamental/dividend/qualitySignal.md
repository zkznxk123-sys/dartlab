---
id: recipes.fundamental.dividend.qualitySignal
title: 배당 quality 종합 신호 (지속·증가·안정 3 축)
category: recipes
kind: recipe
scope: builtin
status: drafted
purpose: 배당 quality 를 3 축 (1) 지속 연수 (consecutive paying years) (2) DPS 증가율 5y CAGR (3) payoutNi 변동성 (std) — 단순 yield 가 아닌 *quality* 점수. dividend 페르소나의 thesis 합성용. analysis 단일축. 트리거 — '배당 quality', '배당 안정성', 'dividend aristocrat 식'.
whenToUse:
  - 배당 quality
  - dividend aristocrat 식
  - 배당 안정성
  - 배당 thesis 합성
linkedSkills:
  - engines.company
  - recipes.fundamental.dividend.policyChangeHistory
  - recipes.fundamental.dividend.payoutFcfCoverage
  - recipes.fundamental.dividend.thesis
toolRefs:
  - EngineCall
  - RunPython
requiredEvidence:
  - skillRef
  - tableRef
  - valueRef
  - dateRef
  - executionRef
  - sourceRef
visualRefs:
  - "engines.viz.tableBackedChart"
  - "engines.viz.evidenceCoverage"
visualGuidance:
  - "표 기반 순위·추세는 engines.viz.tableBackedChart만 사용하고 tableRef/evidenceBinding이 없으면 차트 대신 검산 표로 낮춘다."
  - "근거 충족도는 engines.viz.evidenceCoverage로 검산/한계 섹션에만 배치하고 결론 차트처럼 해석하지 않는다."
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
gap:
  primary:
    - analysis
    - synth
testUniverse:
  market: KR
  stockCodes:
    - "005930"
    - "055550"
    - "035250"
expectedOutputs:
  - consecutivePayingYears
  - dpsCagr5y
  - payoutVolStd
  - qualityScore 0~3 (axis 통과 수)
failureModes:
  - 5 년 미만 데이터로 quality 결론
  - 무상증자 후 DPS 하락을 cut 으로 잘못 카운트
  - 특별배당 포함된 cagr 사용
forbidden:
  - quality score 만으로 배당주 thesis 단독 결론
  - axis 3 통과 = "aristocrat 등급" 단정 (한국 시장은 미국 aristocrat 정의와 다름)
examples:
  - 005930 배당 quality 3 축 점수
  - KOSPI 배당 안정 종목 quality 비교
audiences:
  llm: policyChangeHistory + payoutFcfCoverage 결과를 합쳐 3 축 점수를 만든다. 단독 호출 시는 직접 dividends 시계열에서 계산.
  agent: axis 별 통과/미통과 분리 표기, 단일 score 만 답변에 노출하지 않는다.
  human: yield 보다 *quality* 가 우선이라는 thesis 의 정량 신호.
humanIntro: "qualitySignal 은 yield 의 함정 (high-yield trap) 을 피하기 위한 3 축 quality 점수다. 지속·증가·안정 3 가지를 분리해서 본다 — 한 축에 다 맡기지 않는다."
lastUpdated: "2026-05-22"
---

## 공개 호출 방식

```python
import dartlab
import polars as pl
import statistics

target = "005930"
c = dartlab.Company(target)

def rows(value, limit=40):
    if hasattr(value, "head") and hasattr(value, "to_dicts"):
        return value.head(limit).to_dicts()
    if isinstance(value, list):
        return value[:limit]
    return []

div_rows = sorted(rows(c.gather("dividends"), limit=20), key=lambda x: str(x.get("year") or ""))

dps_series = []
payout_series = []
for r in div_rows:
    dps = r.get("dps") or r.get("dividendPerShare")
    try:
        dps = float(dps) if dps is not None else None
    except (TypeError, ValueError):
        dps = None
    if dps is not None and dps > 0:
        dps_series.append((str(r.get("year"))[:4], dps))
    ratio = r.get("payoutRatio") or r.get("payout_ni")
    try:
        ratio = float(ratio) if ratio is not None else None
    except (TypeError, ValueError):
        ratio = None
    if ratio is not None:
        payout_series.append(ratio)

# axis 1: 연속 배당 연수
consecutive = len(dps_series)

# axis 2: DPS 5y CAGR
dps5 = dps_series[-5:] if len(dps_series) >= 5 else dps_series
cagr5 = None
if len(dps5) >= 2 and dps5[0][1] > 0:
    years = len(dps5) - 1
    cagr5 = (dps5[-1][1] / dps5[0][1]) ** (1/years) - 1

# axis 3: payout 변동성
payout_std = float(statistics.stdev(payout_series)) if len(payout_series) >= 3 else None

axis_pass = {
    "consecutive_ge_5": consecutive >= 5,
    "cagr5_ge_0": cagr5 is not None and cagr5 >= 0,
    "payoutVol_le_0_1": payout_std is not None and payout_std <= 0.10,
}
score = sum(1 for v in axis_pass.values() if v)

table = pl.DataFrame([
    {"axis": "consecutivePayingYears", "value": consecutive, "threshold": ">= 5", "pass": axis_pass["consecutive_ge_5"]},
    {"axis": "dpsCagr5y", "value": cagr5, "threshold": ">= 0", "pass": axis_pass["cagr5_ge_0"]},
    {"axis": "payoutVolStd", "value": payout_std, "threshold": "<= 0.10", "pass": axis_pass["payoutVol_le_0_1"]},
])

emit_result(
    table=table,
    values={"qualityScore": score, "consecutive": consecutive, "cagr5y": cagr5, "payoutStd": payout_std},
    date=dps_series[-1][0] if dps_series else None,
    sources=["dartlab://gather/dividends"],
)
```

## 호출 동작

dividends 시계열에서 3 축 산출:
- (1) `consecutivePayingYears`: DPS > 0 인 연속 연수 (cut 또는 omit row 만나면 끊김)
- (2) `dpsCagr5y`: 최근 5 년 DPS CAGR
- (3) `payoutVolStd`: payoutNi 의 표준편차

각 축 임계 (≥5 년, CAGR ≥0, std ≤0.10) 통과 카운트가 `qualityScore` (0~3). 답변은 score 만 노출하지 않고 axis 별 통과·미통과 분리 표기.

## 대표 반환 형태

| column | 의미 |
|---|---|
| `axis` | 3 축 이름 |
| `value` | 측정값 |
| `threshold` | 통과 임계 |
| `pass` | true / false |

## 연계 절차

1. recipes.fundamental.dividend.policyChangeHistory - axis 1 (consecutive) 의 원천 시계열.
2. recipes.fundamental.dividend.payoutFcfCoverage - axis 3 (변동성) 의 baseline.
3. recipes.fundamental.dividend.thesis - quality 점수를 종합 thesis 에 입력.

## 기본 검증

- 표본 연수 < 5 인 회사는 axis 1 미통과 표기, axis 2/3 도 결론 X.
- 무상증자·분할 row 발견 시 DPS series 분리 보정 또는 한계 명시.
- score 3 = "aristocrat" 단정 금지 — 한국 시장은 미국 aristocrat (25 년 raise) 정의와 다름.
