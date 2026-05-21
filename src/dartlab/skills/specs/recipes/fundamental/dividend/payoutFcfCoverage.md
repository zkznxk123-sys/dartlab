---
id: recipes.fundamental.dividend.payoutFcfCoverage
title: 배당성향 vs FCF 커버리지 z-score
category: recipes
kind: recipe
scope: builtin
status: drafted
purpose: 회사의 배당성향 (Dividends / Net Income) 과 FCF 커버리지 (Dividends / FCF) 두 축의 trailing 5y baseline 대비 z-score 를 동시에 본다. EPS 기준 payout 은 정상인데 FCF 기준이 무너진 row 가 *회계이익↔현금* 괴리 신호. analysis 단일축. 트리거 — '배당 FCF 커버리지', 'payout sustainable', '배당 갭'.
whenToUse:
  - 배당 FCF 커버리지
  - payout sustainable
  - 회계이익 현금 괴리
  - 배당 z-score
linkedSkills:
  - engines.company
  - recipes.fundamental.dividend.capitalReturn
  - recipes.fundamental.dividend.stressTest
toolRefs:
  - EngineCall
  - RunPython
requiredEvidence:
  - skillRef
  - tableRef
  - valueRef
  - dateRef
visualRefs:
  - "engines.viz.cashflowWaterfall"
  - "engines.viz.tableBackedChart"
visualGuidance:
  - "현금흐름·배당·자본배분 bridge는 engines.viz.cashflowWaterfall을 사용하고 CF 원표와 부호 convention을 검산한다."
  - "표 기반 순위·추세는 engines.viz.tableBackedChart만 사용하고 tableRef/evidenceBinding이 없으면 차트 대신 검산 표로 낮춘다."
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
    - "035420"
expectedOutputs:
  - 연도별 payoutNI / payoutFcf 표
  - trailing 5y baseline z-score 2 종
  - 두 z-score 갭 신호
failureModes:
  - 일회성 손익으로 NI 가 튄 연도를 baseline 에 그대로 포함
  - FCF 계산식 (OCF - capex) 변형으로 비교 시점간 일관성 깨짐
  - capex 가 lump-sum 인 산업 (예: 유통 부동산) 에서 단년 노이즈를 신호로 오인
forbidden:
  - 단일 연도 z-score 로 배당 cut 결론
  - payoutFcf > 1 자체를 컷 위험 단정 (M&A·자본구조 조정 동반 가능)
examples:
  - 005930 5년 payoutNI vs payoutFcf z-score
  - 회계이익은 견조하나 FCF 커버리지 깨진 종목
audiences:
  llm: c.analysis("capitalAllocation") 또는 cf 직접 호출로 dividends·netIncome·fcf 3 행을 받아 trailing 5y baseline + 최근 연도 z-score 2 개를 만든다.
  agent: payoutNi 와 payoutFcf 갭이 ±1.0 z 이상이면 회계이익↔현금 괴리 한계 명시.
  human: EPS 기준만 보면 안 보이는 *현금 기준 배당 부담* 을 z-score 로 본다.
humanIntro: "payoutFcfCoverage 는 동일한 배당총액에 대해 *회계이익 기준* 과 *현금 기준* 두 z-score 를 비교한다. 한쪽만 깨지는 row 가 자본구조 조정 또는 회계이익 부풀림 의심 row 다."
lastUpdated: "2026-05-22"
---

## 공개 호출 방식

```python
import dartlab
import polars as pl

target = "005930"
c = dartlab.Company(target)

try:
    rows = c.analysis("capitalAllocation").to_dicts()
except Exception:
    rows = []

audit = []
for r in rows:
    div = abs(float(r.get("dividends_paid") or r.get("dividendsPaid") or 0))
    ni = float(r.get("net_income") or r.get("netIncome") or 0)
    fcf = float(r.get("free_cash_flow") or r.get("freeCashFlow") or 0)
    audit.append({
        "year": r.get("year") or r.get("period"),
        "dividends": div,
        "netIncome": ni,
        "fcf": fcf,
        "payoutNi": (div / ni) if ni else None,
        "payoutFcf": (div / fcf) if fcf else None,
    })

table = pl.DataFrame(audit) if audit else pl.DataFrame(
    schema={"year": pl.Utf8, "dividends": pl.Float64, "netIncome": pl.Float64,
            "fcf": pl.Float64, "payoutNi": pl.Float64, "payoutFcf": pl.Float64}
)

def z_last(col):
    series = table[col].drop_nulls()
    if series.len() < 3:
        return None
    mean = float(series.head(series.len()-1).mean()) if series.len() > 1 else None
    std = float(series.head(series.len()-1).std()) if series.len() > 2 else None
    cur = float(series.tail(1)[0])
    if std is None or std == 0 or mean is None:
        return None
    return (cur - mean) / std

z_ni = z_last("payoutNi")
z_fcf = z_last("payoutFcf")

emit_result(
    table=table,
    values={"zNi": z_ni, "zFcf": z_fcf, "gap": (z_fcf - z_ni) if (z_ni is not None and z_fcf is not None) else None},
    date=str(table["year"].max()) if table.height else None,
    sources=["dartlab://analysis/capitalAllocation"],
)
```

## 호출 동작

연도별 `payoutNi = dividends / netIncome` 과 `payoutFcf = dividends / FCF` 를 만들고, 최근 연도의 trailing baseline 대비 z-score 2 개를 산출. 두 z-score 의 gap (`zFcf - zNi`) 이 음수 + |gap| ≥ 1.0 이면 *EPS 는 견조하지만 현금 기준 배당 부담 가중* 신호.

## 대표 반환 형태

| column | 의미 |
|---|---|
| `year` | 결산 연도 |
| `dividends` | 배당총액 |
| `netIncome` | 순이익 |
| `fcf` | FCF (OCF - capex) |
| `payoutNi` | 배당 / NI |
| `payoutFcf` | 배당 / FCF |

## 연계 절차

1. recipes.fundamental.dividend.capitalReturn - 환원 thesis 진입.
2. recipes.fundamental.dividend.stressTest - 매크로 침체 시 커버리지 무너지는 임계.
3. recipes.fundamental.quality.forensics.revenueToCashBridge - 회계이익↔현금 괴리 깊이.

## 기본 검증

- baseline 표본 < 3 년이면 z-score 계산 안 함, 한계로 명시.
- payoutFcf > 1 단독으로 "cut 위험" 단정 금지 — 자본구조 조정 동반 가능.
- 일회성 손익 (`oneOffAdjustment` 메모 동행) 으로 NI 튄 연도는 baseline 분리.
