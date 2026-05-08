---
id: engines.recipe.earningsQualityTriad
title: 이익 quality 3 모델 합의 (Sloan + Beneish + Novy-Marx — L1 raw)
category: engines
kind: recipe
scope: builtin
status: unverified
purpose: 이익 quality 를 3 학술 모델 (Sloan accruals · Beneish M-Score · Novy-Marx GP/A) 동시 적용으로 합의 점수화. analysis axis 미사용, L1 raw (`c.show("BS"|"IS"|"CF")`) 만 사용. 트리거 — 'Sloan accruals', 'Beneish M-Score', 'Novy-Marx GP/A', '이익 quality 3 모델'.
whenToUse:
  - Sloan accruals 분식 신호
  - Beneish M-Score 분식 가능성
  - Novy-Marx GP/A quality
  - 이익 quality 3 모델 합의
  - 발생주의 vs 현금주의 괴리
  - 분식 회계 다축 점검
linkedSkills:
  - engines.company
  - engines.gather
  - engines.recipe.workingCapitalQuality
  - engines.recipe.distressFilter
  - engines.recipe.creditDistressDual
  - engines.recipe.qualityValueScreen
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
    limitations:
      - 브라우저 안에서는 다년 시계열 일부 한정
lastUpdated: '2026-05-07'
---

## 학술 근거

3 학술 framework 동시 적용 — 각 모델이 잡지 못하는 신호를 다른 모델이 보완.

### 1. Sloan Accruals (1996)
Richard Sloan, *"Do Stock Prices Fully Reflect Information in Accruals and Cash Flows about Future Earnings?"* (The Accounting Review):

- ACC = (NI − CFO) / Average Total Assets
- 발생액 (accruals) 이 큰 회사 → 미래 abnormal return 음(−). 1962-1991 백테스트 연 10%p 차이.
- 핵심 — 회계상 이익 ≠ 현금 이익. 차이가 클수록 미래 회귀 가능성.

### 2. Beneish M-Score (1999)
Daniel Beneish, *"The Detection of Earnings Manipulation"* (Financial Analysts Journal):

- M = −4.84 + 0.92·DSRI + 0.528·GMI + 0.404·AQI + 0.892·SGI + 0.115·DEPI − 0.172·SGAI − 0.327·LVGI + 4.679·TATA
- 8 변수 logit. M &gt; −1.78 = 분식 의심. 검증 76% 적중.
- Enron (1998 M-Score = +5.5) 분식 1 년 전 detection.

### 3. Novy-Marx GP/A (2013)
Robert Novy-Marx, *"The Other Side of Value: The Gross Profitability Premium"* (JFE):

- GP/A = (Sales − COGS) / Total Assets
- ROE·ROA 보다 강력 quality factor. 가치 (B/M) 와 음(-) 상관.

## L1 데이터 직접 계산

3 모델 모두 BS + IS + CF 의 raw snakeId 에서 직접 계산. analysis 의 `이익품질` axis 결과를 의존하지 않고 학술 공식 그대로 적용.

## 공개 호출 방식

```python
import dartlab
import polars as pl

c = dartlab.Company("005930")

bs_df = c.show("BS", freq="Y")
is_df = c.show("IS", freq="Y")
cf_df = c.show("CF", freq="Y")
years = ["2025", "2024", "2023", "2022", "2021"]

def fetchSeries(df: pl.DataFrame, snake: str, years: list[str]) -> list[float]:
    row = df.filter(pl.col("snakeId") == snake).select(years)
    return row.to_numpy()[0].tolist() if row.height > 0 else [0.0] * len(years)

# 공통 raw
sales = fetchSeries(is_df, "sales", years)
cogs = fetchSeries(is_df, "cost_of_sales", years)
ni = fetchSeries(is_df, "net_income", years)
sga = fetchSeries(is_df, "selling_general_admin_expenses", years)
dep = fetchSeries(is_df, "depreciation_expense", years)
cfo = fetchSeries(cf_df, "cash_flow_from_operations", years)
assets = fetchSeries(bs_df, "total_assets", years)
ar = fetchSeries(bs_df, "trade_receivables", years)
ppe = fetchSeries(bs_df, "property_plant_equipment", years)
currAssets = fetchSeries(bs_df, "current_assets", years)
liab = fetchSeries(bs_df, "total_liabilities", years)
ltd = fetchSeries(bs_df, "long_term_debt", years)

# 1) Sloan Accruals (당년)
avgAssets = [(assets[i] + assets[i+1]) / 2 for i in range(len(years)-1)]
sloan = [(ni[i] - cfo[i]) / avgAssets[i] for i in range(len(years)-1)]

# 2) Beneish M-Score (당년 vs 전년 비교)
def beneishMScore(i: int) -> float:
    dsri = (ar[i] / sales[i]) / (ar[i+1] / sales[i+1])
    gmi = ((sales[i+1] - cogs[i+1]) / sales[i+1]) / ((sales[i] - cogs[i]) / sales[i])
    aqi_curr = 1 - (currAssets[i] + ppe[i]) / assets[i]
    aqi_prev = 1 - (currAssets[i+1] + ppe[i+1]) / assets[i+1]
    aqi = aqi_curr / aqi_prev
    sgi = sales[i] / sales[i+1]
    depi = (dep[i+1] / (dep[i+1] + ppe[i+1])) / (dep[i] / (dep[i] + ppe[i]))
    sgai = (sga[i] / sales[i]) / (sga[i+1] / sales[i+1])
    lvgi = ((ltd[i] + (liab[i] - ltd[i])) / assets[i]) / ((ltd[i+1] + (liab[i+1] - ltd[i+1])) / assets[i+1])
    tata = (ni[i] - cfo[i]) / assets[i]
    return (-4.84 + 0.92*dsri + 0.528*gmi + 0.404*aqi + 0.892*sgi
            + 0.115*depi - 0.172*sgai - 0.327*lvgi + 4.679*tata)

beneishScores = [beneishMScore(i) for i in range(len(years)-1)]

# 3) Novy-Marx GP/A
gpa = [(sales[i] - cogs[i]) / assets[i] for i in range(len(years))]

triad = pl.DataFrame({
    "year": years[:-1],
    "sloanAccruals": sloan,
    "sloanFlag": [s > 0.10 for s in sloan],  # 10% 이상 = 위험
    "beneishM": beneishScores,
    "beneishFlag": [m > -1.78 for m in beneishScores],
    "gpa": gpa[:-1],
    "gpaPct": [g * 100 for g in gpa[:-1]],
}).with_columns(
    (pl.col("sloanFlag").cast(pl.Int8) + pl.col("beneishFlag").cast(pl.Int8)).alias("riskScore")
)
```

## 호출 동작

1. `c.show("BS" | "IS" | "CF", freq="Y")` 3 회 — 5 년 wide.
2. snakeId 로 12 raw 항목 추출.
3. Sloan ACC = (NI − CFO) / AvgAssets — 5 점 시계열.
4. Beneish M-Score = 8 변수 logit (당년/전년 비교) — 5 점 중 4 점 시계열 (전년 비교 위해 1 점 손실).
5. Novy-Marx GP/A = (Sales − COGS) / Total Assets — 5 점 시계열.
6. 종합 위험 점수 — Sloan flag + Beneish flag (0 ~ 2).

## 대표 반환 형태

`triad : pl.DataFrame` — 컬럼:
- `year : str`
- `sloanAccruals : float` — (NI−CFO)/AvgAssets
- `sloanFlag : bool` — &gt; 0.10 = 분식 의심
- `beneishM : float` — M-Score
- `beneishFlag : bool` — &gt; −1.78 = 분식 의심
- `gpa : float` — Gross Profit / Assets
- `gpaPct : float` — % 표기
- `riskScore : int` — 0 (안전), 1 (한 모델 의심), 2 (양 모델 의심)

## 한계

- **Sloan 임계 0.10** — 일반적 임계. 산업별 분포 다름 (제조업 &lt; 서비스업).
- **Beneish 8 변수 모두 가용** — `selling_general_admin_expenses`, `depreciation_expense`, `property_plant_equipment` 등 snakeId 일부 회사 결손 가능. fallback 으로 0 처리 시 점수 왜곡.
- **Novy-Marx GP/A** — `cost_of_sales` 분리 안 된 회사 (서비스업) 부적합. 매출원가 = 영업비용 가정 시 GP 과소.
- **3 모델 모두 미국 시장 학술 검증** — 한국 시장 직접 검증 부재. 한국 chaebol 회계 특이성으로 false positive 가능.
- **분식 *예측* 아닌 *의심 신호*** — 점수 통과해도 실제 분식 보장 X.

## 한국 / 미국 시장 차이

- **한국**: chaebol 계열사 internal trading 으로 매출/매출채권 변동 noise 큼 → DSRI · SGI 신뢰성 낮음. 별도재무 vs 연결재무 차이 큼.
- **미국**: 본 framework 의 본 시장. 8 변수 모두 신뢰성 높음. SOX (2002) 이후 Beneish 검출률 다소 낮아짐.

## 연계 절차

1. 본 recipe → 5 년 3 모델 점수 + riskScore.
2. riskScore = 2 (양 모델 의심) → `engines.recipe.workingCapitalQuality` 의 AR/Inv vs Sales gap 점검.
3. 실제 분식 의심 회사 → 공시 (`c.disclosure(...)`) 의 감사보고서 의견·정정공시 빈도 검증.
4. GP/A 강 (상위 10%) + Sloan 약 (하위 30%) = 진짜 quality. `engines.recipe.qualityValueScreen` 와 상호 검증.
5. `engines.recipe.creditDistressDual` 와 결합 — 분식 의심 + 부도 위험 = 강한 회피 신호.

## 기본 검증

- 3 모델 점수 시계열 확인 — 단년도 점수 신뢰 X, 5 년 추세 봄.
- Sloan + Beneish 모두 의심 시 — 실제 분식 case study (대우조선·한진중공업 등) 와 비교.
- GP/A 변화 추세 — 안정 또는 상승 = quality 우월. 급락 = 산업 사이클 또는 경쟁 심화.
- "M-Score = +0.5 = 분식 확정" 단정 X — 의심 신호이지 결정 X.
- 학술 모델은 *통계적* 임. 단일 회사 단정 위험. 점수 + 정성 (감사 보고서·정정공시·CFO 교체 빈도) 결합.
