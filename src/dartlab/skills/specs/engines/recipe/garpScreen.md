---
id: engines.recipe.garpScreen
title: GARP 스크리닝 (Lynch PEG 근사 + 부채 게이트)
category: engines
kind: recipe
scope: builtin
status: unverified
purpose: Lynch GARP (Growth at Reasonable Price) — PEG = PER / 이익성장률 ≤ 1 을 dartlab 의 netProfitGrowth 로 근사하고 부채·매출성장 게이트 를 더해 성장+가치 결합 후보를 횡단으로 발굴하는 절차.
whenToUse:
  - GARP 성장+가치 결합
  - Lynch PEG 스크리닝
  - 성장 대비 저평가
  - PER 대비 저평가
  - 부채 안정 성장주
  - 시장 미반영 성장
linkedSkills:
  - engines.scan
  - engines.scan.screen
  - engines.scan.valuation
  - engines.scan.ratio
  - engines.recipe.qualityValueScreen
  - engines.recipe.distressFilter
  - engines.recipe.compounderCandidates
  - engines.analysis.valuation
toolRefs:
  - engine_call
  - run_python
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
      - 브라우저 안에서는 valuation snapshot prebuild 의존
lastUpdated: '2026-05-06'
---

## 학술 근거

Peter Lynch, *One Up On Wall Street* (1989): GARP (Growth at Reasonable Price) — 가치투자 한정 저PER + 성장투자 한정 고성장 의 절충.

- **PEG ratio** = PER / 이익성장률 (%). PEG ≤ 1 = 시장이 성장률을 미반영.
- 핵심 발견: PER 단독 또는 성장률 단독 보다 두 결합이 sharpe ratio 우월.
- Lynch Magellan Fund (1977-1990): 연 29% 수익률 — 본 framework 의 실증.

학술적 후속: Easton (2004) — implied growth rate 와 PER 결합. Bradshaw (2004) — 애널리스트 LTG (long-term growth) + PER 결합 모델 우월성.

dartlab 한계: EPS 직접 컬럼 X → `netProfitGrowth` 로 근사. EPS 성장률 ≈ 순이익 성장률 (자사주 매입·신주발행 비중 작은 시기) 이므로 합리적 근사.

## 공개 호출 방식

```python
import dartlab
import polars as pl

# 1) 성장 게이트 — netProfitGrowth ≥ 15% + revenueGrowth ≥ 10% + debtRatio ≤ 100%
growth = dartlab.scan("screen", spec={"where": [
    {"field": "finance.ratio.netProfitGrowth", "op": ">=", "value": 15},
    {"field": "finance.ratio.revenueGrowth", "op": ">=", "value": 10},
    {"field": "finance.ratio.debtRatio", "op": "<=", "value": 100},
    {"field": "finance.ratio.netMargin", "op": ">", "value": 0},
]})

# 2) Valuation snapshot
value = dartlab.scan("valuation")

# 3) PEG 근사 = PER / netProfitGrowth, ≤ 1.5 추출
candidates = (
    growth.join(value.select(["stockCode", "per", "pbr", "grade"]), on="stockCode")
    .filter(pl.col("per") > 0)
    .with_columns(
        (pl.col("per") / pl.col("finance.ratio.netProfitGrowth")).alias("pegApprox")
    )
    .filter(pl.col("pegApprox") <= 1.5)
    .sort("pegApprox")
)
```

## 호출 동작

1. `scan("screen", spec=...)` — 4 게이트 (이익성장 15%, 매출성장 10%, 부채 100%, 흑자) 동시 통과.
2. `scan("valuation")` — KR snapshot.
3. PEG 근사 = `per / netProfitGrowth` 계산.
4. PEG ≤ 1.5 (Lynch 의 1.0 보다 약간 완화) 만 추출.
5. PEG 오름차순 정렬 — 가장 저평가된 성장주 우선.

## 대표 반환 형태

`candidates : pl.DataFrame` — 컬럼:
- `stockCode`, `corpName`
- `finance.ratio.netProfitGrowth : float` — 순이익 YoY (%)
- `finance.ratio.revenueGrowth : float` — 매출 YoY (%)
- `finance.ratio.debtRatio : float` — 부채비율 (%)
- `per`, `pbr : float`
- `grade : str` — valuation grade
- `pegApprox : float` — PEG 근사 (낮을수록 저평가)

## 한계

- **EPS 성장률 → netProfitGrowth 근사** — 자사주 매입 비중 큰 미국 기업에서 EPS 성장률 &gt; netProfitGrowth (주식수 감소). 한국에서는 자사주 소각 부재로 두 값 거의 동일.
- **단일 연도 성장률 의존** — Lynch 원전은 5 년 평균 EPS 성장률 사용. 본 recipe 는 YoY 1 년 (분기/연간) 만. 5 년 일관성은 `engines.recipe.compounderCandidates` 로 보완.
- **PEG 1.5 임계는 한국 KOSPI 분포 기반** — 미국은 1.0 표준. 시장별 조정 필요.
- **성장률 음수 종목 자동 제외** — netProfitGrowth ≤ 0 이면 PEG 음수 → 무의미. 흑자 게이트 (`netMargin > 0`) 필수.
- **고성장 + 고PER 조합도 통과** — 예: PER 50, growth 40 → PEG 1.25. 절대 PER 게이트 추가 권장 (PER ≤ 30).

## 한국 / 미국 시장 차이

- **한국**: 자사주 매입·소각 미발달로 EPS 성장률 ≈ netProfitGrowth. 단 한국 IPO·주식분할 빈도 낮아 분모 안정. KOSPI 성장주 풀 작아 임계 (15%/10%) 달성 종목 수 100~200 개.
- **미국**: 자사주 매입 비중 커 EPS &gt; 순이익 성장률 (1-3%p). 본 recipe 보수적 근사. S&amp;P 500 성장 임계 보통 10%/5% 정도로 완화.

## 연계 절차

1. 본 recipe 로 후보 발굴 → `tableRef` 에 PEG 분포.
2. PEG ≤ 1.0 종목 (강한 신호) 에 대해 `engines.recipe.compounderCandidates` 로 5 년 일관성 추가 검증.
3. `engines.recipe.distressFilter` 로 부도 위험 종목 제외 (성장률 통과해도 부채 급증 종목 위험).
4. `engines.analysis.valuation` — DCF + valuation band 단일 회사 심층.
5. `engines.story` 로 narrative 생성 — 성장 동력 (제품·시장점유·신규사업) 까지 묶어 보고.

## 기본 검증

- 후보 수 — 30~80 개가 정상 (KOSPI 1-3%). 200 개 초과 = 게이트 너무 느슨.
- PEG 분포 — 중앙값 0.8-1.2, 하위 25 percentile 0.5 미만이어야 강한 신호 군집.
- 단일 연도 성장률은 base effect (전년 일회성 손실 등) 영향 큼 — 분기 시계열 추가 점검 필수.
- 성장 catalyst 명시 — 단순 숫자 통과 X. 신규 제품·M&A·시장점유 변화 등 정성 근거 함께.
- "PEG = 0.5 = 매수" 단정 X — 성장 지속 가능성 (moat·산업 사이클) 별도 검증.
