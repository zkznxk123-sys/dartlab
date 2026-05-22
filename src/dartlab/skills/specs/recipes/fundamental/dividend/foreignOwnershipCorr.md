---
id: recipes.fundamental.dividend.foreignOwnershipCorr
title: 외국인 보유율 vs 배당성향 상관
category: recipes
kind: recipe
scope: builtin
status: drafted
purpose: 한국 시장에서 외국인 보유율 변화와 배당성향 변화의 시차 상관을 본다. 외국인이 *배당 정책에 영향* 한 종목 (높은 상관) vs *영향 없는* 종목 (낮은 상관) 분리. 단일 회사 시계열 5~10 년. gather ↔ analysis 격리 메우는 조합. 트리거 — '외국인 배당', 'foreign ownership dividend', '주주환원 외인 영향'.
whenToUse:
  - 외국인 보유율 배당
  - foreign ownership dividend
  - 주주환원 외국인 영향
  - 외인 매수 배당정책 shift
linkedSkills:
  - engines.company
  - engines.gather
  - recipes.fundamental.dividend.capitalReturn
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
  - "engines.viz.mermaidDiagram"
visualGuidance:
  - "표 기반 순위·추세는 engines.viz.tableBackedChart만 사용하고 tableRef/evidenceBinding이 없으면 차트 대신 검산 표로 낮춘다."
  - "메커니즘 diagram은 engines.viz.mermaidDiagram으로 8노드 이하만 만들고 모든 edge에 문장·수치·sourceRef 근거를 둔다."
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
    - gather
    - analysis
testUniverse:
  market: KR
  stockCodes:
    - "005930"
    - "000660"
expectedOutputs:
  - 연도별 외국인 보유율 + 배당성향 표
  - Pearson r (동일 연도) + lag-1 r (외인이 1 년 선행)
  - 상관 임계 (|r| ≥ 0.5) 통과 여부
failureModes:
  - 5 년 미만 표본으로 상관 강도 단정
  - 외국인 보유율 측정 시점 (연말 vs 평균) 불일치
  - 우선주 비포함 보유율로 보통주 배당과 매칭
forbidden:
  - 상관관계를 인과로 단정 (외인이 배당 정책 결정한다)
  - 단일 lag 만 보고 시차 결론
examples:
  - 005930 외국인 vs 배당 10년 상관
  - 외인 매수 → 1년 뒤 배당 인상 종목
audiences:
  llm: c.gather("ownership") + c.analysis("capitalAllocation") 로 연도별 외국인 보유율 + 배당성향 두 시계열을 받아 Pearson r 산출.
  agent: lag-1 상관 (외인이 1 년 선행) 도 같이 산출, |r| ≥ 0.5 임계 통과 여부 명시.
  human: 외인이 배당 결정에 영향이 있는지 시계열 상관으로 본다. 인과 아님.
humanIntro: "foreignOwnershipCorr 는 한국 시장 특유의 *외국인 영향* 가설을 단일 회사 시계열로 검증한다. 상관 ≠ 인과지만, 상관 임계 미통과 회사의 배당 thesis 에서 *외인 변동성* 은 1 차 변수가 아니다."
lastUpdated: "2026-05-22"
---

## 공개 호출 방식

```python
import dartlab
import polars as pl

target = "005930"
c = dartlab.Company(target)

def rows(value, limit=80):
    if hasattr(value, "head") and hasattr(value, "to_dicts"):
        return value.head(limit).to_dicts()
    if isinstance(value, list):
        return value[:limit]
    return []

own_rows = rows(c.gather("ownership"), limit=40)
try:
    cap_rows = c.analysis("capitalAllocation").to_dicts()
except Exception:
    cap_rows = []

# year-key 로 join
by_year = {}
for o in own_rows:
    y = str(o.get("year") or o.get("asOfYear") or "")[:4]
    if not y: continue
    by_year.setdefault(y, {})["foreignPct"] = float(o.get("foreignPct") or o.get("foreign_ratio") or 0)
for cap in cap_rows:
    y = str(cap.get("year") or cap.get("period") or "")[:4]
    if not y: continue
    div = abs(float(cap.get("dividends_paid") or cap.get("dividendsPaid") or 0))
    ni = float(cap.get("net_income") or cap.get("netIncome") or 0)
    by_year.setdefault(y, {})["payoutNi"] = (div / ni) if ni else None

merged = [{"year": y, **v} for y, v in sorted(by_year.items()) if "foreignPct" in v and "payoutNi" in v and v.get("payoutNi") is not None]
table = pl.DataFrame(merged) if merged else pl.DataFrame(
    schema={"year": pl.Utf8, "foreignPct": pl.Float64, "payoutNi": pl.Float64}
)

def pearson(a, b):
    if len(a) < 3 or len(a) != len(b):
        return None
    import statistics as st
    ma, mb = st.mean(a), st.mean(b)
    num = sum((x-ma)*(y-mb) for x, y in zip(a, b))
    da = sum((x-ma)**2 for x in a) ** 0.5
    db = sum((y-mb)**2 for y in b) ** 0.5
    return num / (da*db) if da*db else None

a = table["foreignPct"].to_list()
b = table["payoutNi"].to_list()
r0 = pearson(a, b)
r1 = pearson(a[:-1], b[1:]) if len(a) >= 4 else None

emit_result(
    table=table,
    values={"pearson": r0, "pearsonLag1": r1, "years": table.height},
    date=str(table["year"].max()) if table.height else None,
    sources=["dartlab://gather/ownership", "dartlab://analysis/capitalAllocation"],
)
```

## 호출 동작

`gather.ownership` 의 연도별 외국인 보유율과 `analysis.capitalAllocation` 의 연도별 payoutNi 를 year-key 로 join 한 뒤 Pearson 상관 2 개 산출: 동일 연도 r0, 외인 1 년 선행 r1. r0 ≥ 0.5 이면 동기 영향, r1 ≥ 0.5 이면 외인이 1 년 선행 가설 지지.

## 대표 반환 형태

| column | 의미 |
|---|---|
| `year` | 결산 연도 |
| `foreignPct` | 외국인 보유율 (%) |
| `payoutNi` | 배당 / NI |

## 연계 절차

1. recipes.fundamental.dividend.capitalReturn - 환원 thesis 진입.
2. recipes.fundamental.dividend.stressTest - 외인 이탈 시나리오 별 cut 임계.

## 기본 검증

- 표본 < 5 년이면 상관 결론 X, *coverage 한계* 로만.
- 우선주 분리 발행 시 보통주 보유율만 사용한다 — 본 recipe 의 임계는 보통주 기준.
- 상관 = 인과 아님 — 답변 본문에 항상 명시.
