---
id: engines.recipe.compounderCandidates
title: Compounder 후보 — ROE/매출/마진 5 년 일관성 스크리닝
category: engines
kind: recipe
scope: builtin
status: unverified
purpose: Buffett-style quality compounder 발굴 — ROE / revenueGrowth / grossMargin 의 5 년 평균과 표준편차로 사이클 무관 일관 quality 종목을 횡단으로 식별하는 절차. 트리거 — 'compounder 발굴', 'quality 일관 종목', 'Buffett 스타일 횡단'.
whenToUse:
  - 장기 복리 종목 발굴
  - Buffett style quality
  - 5 년 ROE 일관성
  - 사이클 무관 quality
  - compounder 후보
  - 우량주 횡단 비교
linkedSkills:
  - engines.scan
  - engines.scan.ratio
  - engines.scan.valuation
  - engines.recipe.qualityValueScreen
  - engines.recipe.garpScreen
  - engines.recipe.distressFilter
  - engines.analysis.profitability
  - engines.analysis.efficiency
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
      - 브라우저 안에서는 freq="Y" 5 기간 시계열 일부 한정
forbidden:
  - 단년도 고-ROE 로 compounder 단정 금지 — 5 년 일관성 + 표준편차 작음 동반.
  - 매출 역성장 1 회로 compounder 자격 박탈 단정 금지 — 사이클성 / 일회성 구분.
  - ROE 평균만 보고 표준편차 (사이클 무관) 점검 누락 금지.
  - 매출 / 마진 시계열 결손 분기 0 채워서 평균 단정 금지.
failureModes:
  - 5 년 윈도우의 시작점 (2020 코로나 vs 2019) 별 결과 차이
  - 사업부 개편 / 분할로 인한 역사 연속성 단절
  - 산업별 정상 ROE / 마진 분포 차이 (대형주 vs 중소형주)
  - 일회성 M&A / 매각으로 ROE 단발 변동
  - 회계 정책 변경 시점 영향 미보정
examples:
  - KR 시장 5 년 일관 compounder 후보"
  - ROE >= 15% + 표준편차 작은 종목"
  - 매출 안정 성장 + 고-margin
  - compounder + valuation 결합
gap:
  primary:
    - scan
    - analysis
lastUpdated: '2026-05-07'
---

## 학술 근거

Warren Buffett (Berkshire Hathaway 주주서한, 1977-2024): "wonderful company at fair price" — 단년도 고-ROE 가 아니라 **사이클 전체 일관 고-ROE**. 핵심 신호:

- ROE ≥ 15% 일관 5 년 + 표준편차 작음 (사이클 무관).
- 매출 안정 성장 (역성장 없음).
- grossMargin 안정 — moat (가격결정력) 의 정량 신호.

학술 검증:
- Asness-Frazzini-Pedersen, *"Quality Minus Junk"* (2019): profitability + safety + payout 결합 quality factor. 1956-2016 미국 연 5%p 초과수익. 핵심 — 단년도가 아닌 5 년 평균 + 일관성 (표준편차 역수).
- Novy-Marx (2014): ROE 일관성 (low volatility) 가 high mean ROE 보다 미래 수익률과 강한 상관.
- Sloan (1996): 일관 고-ROE 회사가 mean reversion 회피하는 비율 30% (전체 평균 5%) — 진짜 moat 신호.

dartlab 한계: ROIC 미노출 (WACC 부재로 ROIC &gt; WACC 게이트 X). 본 recipe 는 ROE 만 사용. ROE 는 자본구조 (부채비율) 영향 받으므로 debtRatio 보조 게이트 추가.

## 공개 호출 방식

```python
import dartlab
import polars as pl

# 1) ROE 5 년 시계열 freq="Y" — 컬럼 "2025"~"2021"
years = ["2025", "2024", "2023", "2022", "2021"]
roeY = dartlab.scanRatio("roe", freq="Y").select(["stockCode", *years])

# 2) 5 년 평균 + 표준편차 + 최소값 — Buffett quality
roeStats = roeY.with_columns([
    pl.mean_horizontal(*[pl.col(y) for y in years]).alias("roe5yMean"),
    pl.concat_list([pl.col(y) for y in years]).list.std().alias("roe5yStd"),
    pl.min_horizontal(*[pl.col(y) for y in years]).alias("roe5yMin"),
])

# 3) revenue 5 년 모두 양성장 (역성장 없음)
revG = dartlab.scanRatio("revenueGrowth", freq="Y").select(["stockCode", *years])
revGrowAll = revG.with_columns(
    pl.all_horizontal([pl.col(y) > 0 for y in years]).alias("revGrowAll")
).filter(pl.col("revGrowAll"))

# 4) grossMargin 5 년 평균 + 표준편차
gmY = dartlab.scanRatio("grossMargin", freq="Y").select(["stockCode", *years])
gmStats = gmY.with_columns([
    pl.mean_horizontal(*[pl.col(y) for y in years]).alias("gm5yMean"),
    pl.concat_list([pl.col(y) for y in years]).list.std().alias("gm5yStd"),
])

# 5) Compounder 게이트 — ROE 평균 ≥ 15 + 표준편차 ≤ 5 + 최소값 ≥ 10 + 5 년 양성장 + grossMargin 안정
candidates = (
    roeStats.join(revGrowAll.select(["stockCode"]), on="stockCode")
    .join(gmStats.select(["stockCode", "gm5yMean", "gm5yStd"]), on="stockCode")
    .filter(
        (pl.col("roe5yMean") >= 15)
        & (pl.col("roe5yStd") <= 5)
        & (pl.col("roe5yMin") >= 10)
        & (pl.col("gm5yMean") >= 25)
        & (pl.col("gm5yStd") <= 5)
    )
    .sort("roe5yMean", descending=True)
)
```

## 호출 동작

1. `scanRatio("roe", freq="Y")` — 5 기간 컬럼 wide 테이블.
2. polars `mean_horizontal` + `list.std` — 5 년 평균·표준편차·최소값.
3. `scanRatio("revenueGrowth", freq="Y")` — 5 기간 모두 양수 필터 (역성장 없음).
4. `scanRatio("grossMargin", freq="Y")` — 5 년 평균·표준편차.
5. join → 4 게이트 (ROE 평균 ≥ 15, ROE std ≤ 5, ROE min ≥ 10, 5 년 양성장, gm 평균 ≥ 25, gm std ≤ 5).
6. ROE 평균 내림차순 정렬.

## 대표 반환 형태

`candidates : pl.DataFrame` — 컬럼:
- `stockCode`, `corpName`
- `roe5yMean : float` — 5 년 ROE 평균 (≥ 15%)
- `roe5yStd : float` — 5 년 ROE 표준편차 (≤ 5%p)
- `roe5yMin : float` — 5 년 ROE 최소값 (≥ 10%)
- `gm5yMean : float` — 5 년 grossMargin 평균
- `gm5yStd : float` — 5 년 grossMargin 표준편차
- 매년 ROE / revenueGrowth / grossMargin 값 (디버깅용)

## 한계

- **ROE 는 자본구조 영향** — 부채 늘려 자기자본 줄이면 ROE 인위적 상승. debtRatio 게이트 추가 권장 (`debtRatio ≤ 100`).
- **ROIC &gt; WACC 게이트 부재** — Buffett 원전 framework 의 핵심 (capital efficiency). dartlab WACC 부재로 직접 X. ROE 만 사용 시 자본 비효율 회피 약함.
- **5 년 시계열 가용성** — 신규 IPO 종목 (5 년 미만) 자동 제외. KOSPI 약 1500 개 종목 만 후보 풀.
- **사이클 회사 자동 제외** — 조선·반도체·정유 처럼 사이클 큰 산업은 ROE 표준편차 5%p 이내 어려움. 산업 특성상 본 recipe 에서 자연 제외 — 의도된 동작.
- **Survivorship bias** — 5 년 일관 quality = 이미 검증된 종목 → 비싸진 상태일 가능성. 본 recipe 결과 + 가치 게이트 (PER ≤ 25 등) 결합 권장.

## 한국 / 미국 시장 차이

- **한국**: 일관 고-ROE 종목 풀 작음 — KOSPI 약 30-60 개. 삼성전자·SK하이닉스 같은 사이클 회사는 ROE 표준편차 큼 → 본 recipe 자연 제외. 통신·소비재·금융 (보험) 에서 후보 다수.
- **미국**: S&P 500 의 약 100-150 종목 통과. Apple·Microsoft·Visa 같은 platform 회사가 전형. 본 framework 학술 검증의 본 시장.

## 연계 절차

1. 본 recipe 로 후보 발굴 → `tableRef` 에 ROE/매출/마진 5 년 분포.
2. 후보 → `engines.recipe.qualityValueScreen` 의 GP/A 게이트 추가 검증.
3. `engines.recipe.garpScreen` 의 PEG 게이트 — compounder 가 비싸지 않은지 가치 검증.
4. `engines.recipe.distressFilter` 통과 (안전성).
5. `engines.analysis.profitability` — DuPont 분해로 ROE 동인 (margin × turnover × leverage) 확인.
6. `engines.analysis.efficiency` — capital cycle (재투자 효율) 정성 분석.
7. `engines.story` — moat narrative (가격결정력·전환비용·네트워크효과·규모) 까지.

## 기본 검증

- 후보 수 — 한국 30-60, 미국 100-150 개가 정상.
- ROE 평균 분포 — 후보 평균 18-22%, 표준편차 평균 2-3%p 이면 강한 quality.
- 산업 분포 — 통신·소비재·금융·플랫폼 우세 정상. 한 산업 80% 이상이면 게이트 점검.
- ROE 일관성 외에 자본배분 (배당+자사주+M&A) 정성 검증 필수.
- "5 년 quality = 영원" 단정 X — moat 변동 (기술 변화·규제·신규 경쟁) 별도 검증.
- 본 recipe 와 `qualityValueScreen` 교집합이 진짜 quality value compounder.
