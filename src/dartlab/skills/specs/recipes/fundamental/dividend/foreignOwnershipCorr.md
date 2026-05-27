---
id: recipes.fundamental.dividend.foreignOwnershipCorr
title: 외국인 보유율 vs 배당성향 상관
category: recipes
kind: recipe
scope: builtin
status: tested
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

### 1. 결론 도출

Pearson r0 + r1 임계 단정. 예: "10y 표본 (2016-2025): foreignPct 49% → 54% / payoutNi 0.28 → 0.36 추세. Pearson r0 (동기) = +0.62 / r1 (외인 1y 선행) = +0.71 → 둘 다 |r| ≥ 0.5 통과 — 외인이 1년 선행 가설 지지 (상관 = 인과 아님 명시 필수)."

### 2. 핵심 근거 수집

- Company.gather('ownership') 연도별 외국인 보유율 (foreignPct)
- Company.analysis('capitalAllocation') 연도별 (dividends_paid + net_income) → payoutNi
- year-key 로 join, 표본 ≥ 5 년
- Pearson r0 (동일 연도) + Pearson r1 (외인 1y 선행)

### 3. 메커니즘 분석

```
2 시계열 → year-key join
   foreignPct[t]
   payoutNi[t] = dividends_paid[t] / net_income[t]
   ↓
Pearson 상관 2 종:
   r0 = corr(foreignPct[t], payoutNi[t]) — 동기 상관
   r1 = corr(foreignPct[t-1], payoutNi[t]) — 외인 1y 선행 lag
   ↓
임계 판정:
   |r0| ≥ 0.5 + |r1| ≥ 0.5 → 동기 + 선행 모두 — 외인 영향 강
   |r0| < 0.5 + |r1| ≥ 0.5 → 외인 선행 우세 — 외인이 배당 정책 trigger 후보
   |r0| ≥ 0.5 + |r1| < 0.5 → 동기만 — 외인이 결정 *이후* 매수 (배당이 외인 attract)
   둘 다 < 0.5            → 외인 영향 약 (다른 요인 우세)
```

상관 ≠ 인과 — 외인이 배당 결정에 영향? 또는 배당 인상이 외인 attract? r1 (선행 lag) 가 r0 보다 강하면 외인 선행 가설 지지.

### 4. 반례·한계

- 표본 < 5 년이면 상관 강도 결론 X — 노이즈 영향 큼.
- 우선주 분리 발행 시 보통주 보유율만 사용해야 함 (보통주 배당 매칭).
- 외국인 보유율 측정 시점 (연말 vs 연평균) 일관성 필요.
- *외인* 단일 카테고리 — 헤지펀드 / 장기 패시브 분리 X.

### 5. 후속 모니터링

- r1 ≥ 0.5 → `recipes.fundamental.dividend.capitalReturn` 으로 환원 thesis 진입.
- r0 + r1 둘 다 ≥ 0.5 → `recipes.sentiment.foreignBuyMomentum` 으로 외인 가속도 cross-check.
- 둘 다 < 0.5 → `recipes.fundamental.dividend.payoutFcfCoverage` 로 fcf 충당으로 다른 driver 점검.

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
