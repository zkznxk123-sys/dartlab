---
id: recipes.fundamental.dividend.policyChangeHistory
title: 배당 정책 변경 history (인상·유지·삭감)
category: recipes
kind: recipe
scope: builtin
status: drafted
purpose: 연도별 DPS (Dividend Per Share) 변화율 + 정책 분류 (raise / maintain / cut / omit) 시계열. 단일 yield 가 아닌 *정책 일관성* 점검. cut/omit 이력이 있으면 thesis 의 *배당 약속 신뢰* 가 깎인다. analysis 단일축. 트리거 — '배당 정책 history', 'DPS 변화', '배당 컷 이력'.
whenToUse:
  - 배당 정책 history
  - DPS 변화율
  - 배당 컷 이력
  - 배당 일관성
linkedSkills:
  - engines.company
  - recipes.fundamental.dividend.capitalReturn
  - recipes.fundamental.dividend.payoutFcfCoverage
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
visualGuidance:
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
    - gather
testUniverse:
  market: KR
  stockCodes:
    - "005930"
    - "055550"
expectedOutputs:
  - 연도별 DPS 표
  - DPS 변화율 + 정책 분류 (raise/maintain/cut/omit)
  - 누적 raise 년수 / cut 년수
failureModes:
  - 무상증자·주식분할 후 DPS 비교 시 분모 보정 누락
  - 특별배당 (one-off) 을 정기 배당 raise 로 오인
  - 분기배당 도입 연도의 연환산 누락
forbidden:
  - 1~2 회 cut/omit 으로 "배당 신뢰 깨짐" 단정
  - 무상증자 후 명목 DPS 하락을 정책 cut 으로 처리
examples:
  - 005930 10년 DPS 변화율
  - 배당 cut 이력 있는 KOSPI 종목
audiences:
  llm: c.gather("dividends") 또는 c.show 로 연도별 DPS 시계열을 받아 변화율 + 정책 분류 4 카테고리로 라벨.
  agent: 주식분할·무상증자 row 가 발견되면 분모 보정 적용 또는 한계 명시.
  human: 배당이 *얼마나* 가 아닌 *얼마나 일관* 한가를 시계열로 본다.
humanIntro: "policyChangeHistory 는 배당 thesis 의 *신뢰* 축이다. 높은 yield 인데 cut 이력 잦은 회사는 thesis 가 깨지기 쉽다 — 일관성 자체가 자산."
lastUpdated: "2026-05-22"
---

## 공개 호출 방식

```python
import dartlab
import polars as pl

target = "005930"
c = dartlab.Company(target)

def rows(value, limit=40):
    if hasattr(value, "head") and hasattr(value, "to_dicts"):
        return value.head(limit).to_dicts()
    if isinstance(value, list):
        return value[:limit]
    return []

div_rows = rows(c.gather("dividends"), limit=20)

audit = []
prev_dps = None
for r in sorted(div_rows, key=lambda x: str(x.get("year") or x.get("period") or "")):
    dps = r.get("dps") or r.get("dividendPerShare")
    try:
        dps = float(dps) if dps is not None else None
    except (TypeError, ValueError):
        dps = None
    chg = (dps - prev_dps) / prev_dps if (prev_dps and dps is not None) else None
    if dps is None or dps == 0:
        policy = "omit"
    elif prev_dps is None:
        policy = "init"
    elif chg is None:
        policy = "unknown"
    elif chg > 0.02:
        policy = "raise"
    elif chg < -0.02:
        policy = "cut"
    else:
        policy = "maintain"
    audit.append({
        "year": r.get("year") or r.get("period"),
        "dps": dps,
        "changePct": chg,
        "policy": policy,
    })
    prev_dps = dps if dps is not None else prev_dps

table = pl.DataFrame(audit) if audit else pl.DataFrame(
    schema={"year": pl.Utf8, "dps": pl.Float64, "changePct": pl.Float64, "policy": pl.Utf8}
)

def count_policy(name):
    if not table.height:
        return 0
    return int((table["policy"] == name).sum())

emit_result(
    table=table,
    values={
        "years": table.height,
        "raises": count_policy("raise"),
        "cuts": count_policy("cut"),
        "omits": count_policy("omit"),
    },
    date=str(table["year"].max()) if table.height else None,
    sources=["dartlab://gather/dividends"],
)
```

## 호출 동작

연도별 DPS 시계열을 정렬한 뒤 직전년 대비 변화율 (`changePct`) 산출. ±2% 안은 `maintain`, +2% 이상 `raise`, -2% 이하 `cut`, DPS=0 은 `omit`, 첫 연도는 `init`. 누적 raise / cut / omit 카운트가 headline.

## 대표 반환 형태

| column | 의미 |
|---|---|
| `year` | 결산 연도 |
| `dps` | 주당배당금 (원) |
| `changePct` | 직전년 대비 변화율 |
| `policy` | raise / maintain / cut / omit / init |

## 연계 절차

1. recipes.fundamental.dividend.capitalReturn - 환원 thesis 진입.
2. recipes.fundamental.dividend.payoutFcfCoverage - cut 이 발생한 해의 FCF 커버리지 동시 확인.
3. recipes.fundamental.dividend.stressTest - 매크로 침체 시 cut/omit 임계.

## 기본 검증

- 무상증자·주식분할 발견 row 는 분모 보정 적용 또는 한계 명시.
- 특별배당이 분리 표시 가능하면 `policy=specialAdded` 로 분리, 기본 정책 분류와 섞지 않는다.
- cut/omit 카운트가 0 ≠ "안전" — 표본 연수와 함께 본다 (5 년 안 raise 만 있어도 그 자체로 *trend 안정* 신호 단정 금지).
