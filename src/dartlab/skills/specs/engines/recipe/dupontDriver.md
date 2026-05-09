---
id: engines.recipe.dupontDriver
title: DuPont 5-step ROE 동인 분해 (L1 raw 시계열 직접 계산)
category: engines
kind: recipe
scope: builtin
status: unverified
purpose: ROE 변동의 진짜 원인을 5 동인 (세부담·이자부담·영업마진·자산회전·재무레버리지) 으로 분리해 단일 회사 5 년 시계열에서 어떤 요소가 ROE 를 끌고 갔는지 정량화하는 절차. L1 raw (`c.show("BS"|"IS")`) 만 사용. 트리거 — 'ROE 분해', 'DuPont 5 동인', 'ROE 추적'.
whenToUse:
  - DuPont 5-step 분해
  - ROE 동인 식별
  - ROE 변동 원인 분석
  - 영업마진 vs 레버리지 효과 분리
  - 5 년 ROE 추세 해석
  - CFA 표준 ROE 분해
linkedSkills:
  - engines.company
  - engines.gather
  - engines.scan.ratio
  - engines.recipe.qualityValueScreen
  - engines.recipe.compounderCandidates
  - engines.recipe.capitalAllocationScorecard
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
forbidden:
  - ROE 15% 단정 (좋다) 금지 — 5 동인 분포로 구조적 우위 vs 일시적 분리.
  - 단일 동인 (예 — leverage 만 높음) 변동을 영구 우위로 단정 금지.
  - 음수 영업이익 (적자) 회사에 본 framework 단순 적용 금지 — InterestBurden 무한대.
  - 금융업 (은행 / 보험) 에 본 분해 그대로 적용 금지 — IS 구조 다름.
failureModes:
  - earnings_before_tax snakeId 가용성 차이로 InterestBurden 추정 실패
  - 평균자산 (전년말 + 당년말 / 2) 보다 분기 가중평균이 정확
  - 연결 vs 별도 회계 차이로 분해 결과 차이
  - 일회성 손익으로 OperatingMargin 단발 변동
  - 회계 기준 변경 (정책 자발적) 시점 영향 미보정
examples:
  - 삼성전자 5 년 ROE 5 동인 분해
  - DuPont 동인 표준편차 큰 항목 식별
  - 산업 평균 분해 + 회사 비교
  - DuPont + working capital quality 결합
gap:
  primary:
    - gather
    - scan
lastUpdated: '2026-05-07'
---

## 학술 근거

DuPont 사 (E.I. du Pont de Nemours, 1920 년대) 가 도입한 ROE 분해. CFA Institute Level 1 표준 (CFA Curriculum, FRA Reading 22). 핵심 식:

ROE = (NI / EBT) × (EBT / EBIT) × (EBIT / Sales) × (Sales / Avg Assets) × (Avg Assets / Avg Equity)
    = TaxBurden × InterestBurden × OperatingMargin × AssetTurnover × FinancialLeverage

각 항목의 의미:
- **TaxBurden** — 세후 / 세전. 1 에 가까울수록 세부담 낮음. 산업·국가·세제 의존.
- **InterestBurden** — 세전 / 영업이익. 1 에 가까울수록 이자비용 낮음. 부채 자본 구조 반영.
- **OperatingMargin** — 영업이익 / 매출. 사업 본업의 수익성.
- **AssetTurnover** — 매출 / 평균자산. 자산 효율 (자본 회전).
- **FinancialLeverage** — 평균자산 / 평균자기자본. 부채를 통한 자본 증폭 — equity multiplier.

ROE 가 같은 두 회사도 5 동인 분포가 다르면 사업 모델이 완전 다름. 예: 명품 회사는 OpMargin 높고 Turnover 낮음, 마트는 반대.

검증 사례:
- Penman (2013): DuPont 분해가 future earnings 예측에서 단순 ROE 보다 우월. RNOA (Return on Net Operating Assets) 와 결합 시 가장 강한 신호.
- Soliman (2008): 산업 평균 대비 OpMargin·Turnover 분해로 미래 수익률 예측 가능.

## L1 데이터로 직접 계산 (analysis axis 미사용)

dartlab 의 `c.show()` 가 L1 provider 데이터 그대로 노출. analysis 엔진의 `profitability` / `efficiency` axis 결과를 의존하지 않고 raw 시계열에서 직접 분해.

## 공개 호출 방식

```python
import dartlab
import polars as pl

c = dartlab.Company("005930")

is_df = c.show("IS", freq="Y")   # 손익계산서 (매출·영업이익·세전·순이익)
bs_df = c.show("BS", freq="Y")   # 재무상태표 (자산·자본 시계열)

years = ["2025", "2024", "2023", "2022", "2021"]

def dupontDecompose(is_df: pl.DataFrame, bs_df: pl.DataFrame, years: list[str]) -> pl.DataFrame:
    sales = is_df.filter(pl.col("snakeId") == "sales").select(years).to_numpy()[0]
    op = is_df.filter(pl.col("snakeId") == "operating_profit").select(years).to_numpy()[0]
    ebt = is_df.filter(pl.col("snakeId") == "earnings_before_tax").select(years).to_numpy()[0]
    ni = is_df.filter(pl.col("snakeId") == "net_income").select(years).to_numpy()[0]
    assets = bs_df.filter(pl.col("snakeId") == "total_assets").select(years).to_numpy()[0]
    equity = bs_df.filter(pl.col("snakeId") == "total_stockholders_equity").select(years).to_numpy()[0]

    avg_assets = [(assets[i] + assets[i+1]) / 2 for i in range(len(years)-1)]
    avg_equity = [(equity[i] + equity[i+1]) / 2 for i in range(len(years)-1)]

    rows = []
    for i, y in enumerate(years[:-1]):
        rows.append({
            "year": y,
            "taxBurden": ni[i] / ebt[i],
            "interestBurden": ebt[i] / op[i],
            "operatingMargin": op[i] / sales[i],
            "assetTurnover": sales[i] / avg_assets[i],
            "financialLeverage": avg_assets[i] / avg_equity[i],
            "roeReconstructed": (ni[i] / ebt[i]) * (ebt[i] / op[i]) * (op[i] / sales[i])
                               * (sales[i] / avg_assets[i]) * (avg_assets[i] / avg_equity[i]),
        })
    return pl.DataFrame(rows)

result = dupontDecompose(is_df, bs_df, years)
```

## 호출 동작

1. `c.show("IS", freq="Y")` — 5 기간 손익계산서 시계열 (snakeId 기반 wide).
2. `c.show("BS", freq="Y")` — 5 기간 재무상태표.
3. snakeId 로 6 항목 추출 — sales / operating_profit / earnings_before_tax / net_income / total_assets / total_stockholders_equity.
4. 평균자산 / 평균자본 계산 (직전년도 + 당년도 / 2).
5. 5 동인 직접 계산 + 재구성 ROE (5 곱) — 원본 ROE 와 일치 검증.

## 대표 반환 형태

`result : pl.DataFrame` — 컬럼:
- `year : str` — 4 기간 (5 년 시계열에서 평균자산 계산으로 1 기간 손실)
- `taxBurden : float` — NI/EBT
- `interestBurden : float` — EBT/EBIT
- `operatingMargin : float` — EBIT/Sales
- `assetTurnover : float` — Sales/AvgAssets
- `financialLeverage : float` — AvgAssets/AvgEquity
- `roeReconstructed : float` — 5 동인 곱 (원본 ROE 일치 확인)

## 한계

- **`earnings_before_tax` snakeId 가용성** — 일부 회사 IS 에서 영업외손익 분리 안 됨. fallback 으로 `net_income / (1 - taxRate)` 추정.
- **평균자산 단일 시점 가중** — Q1·Q2·Q3·Q4 가중평균이 더 정확하나 본 recipe 는 연말 + 전년말 평균만.
- **연결 vs 별도** — 한국 회사 연결재무 기준. 자회사 효과 큰 지주회사는 분해 해석 주의.
- **금융업 부적합** — 은행·보험 IS 구조 다름 (이자수익·보험료 매출). 별도 분해 framework 필요.

## 한국 / 미국 시장 차이

- **한국**: 법인세율 변동 작아 TaxBurden 안정. 영업외손익 비중 큰 회사 (지주·금융 자회사) 다수 → InterestBurden 변동 크게 나타나는 경우 주의.
- **미국**: 본 framework 의 본 시장. S&P 500 대표 회사 5 동인 평균 배포 — Damodaran 산업 데이터로 비교 가능.

## 연계 절차

1. 본 recipe → ROE 5 동인 시계열 도출.
2. 동인 변화 큰 (표준편차 큰) 항목 식별 — ROE 변동의 원인.
3. OperatingMargin 변동 → `engines.recipe.workingCapitalQuality` 로 운전자본 효율 점검.
4. AssetTurnover 변동 → 자산 재투자 시점 (CAPEX 시계열) 분석.
5. FinancialLeverage 변동 → `engines.recipe.creditDistressDual` 로 부채 위험 점검.
6. 5 년 일관 quality compounder 인지 → `engines.recipe.compounderCandidates` 와 상호 검증.

## 기본 검증

- `roeReconstructed` 와 원본 ROE (`net_income / avg_equity`) 차이 ≤ 0.5%p 이어야 분해 정확.
- 5 동인 변화율 표 확인 — 한 동인이 전체 ROE 변화의 70% 이상 설명하면 단일 동인 사이클.
- 산업 평균 분해와 비교 — 본 회사가 동종 대비 어느 동인이 우월/열위인지.
- 음수 영업이익 시 InterestBurden 무한대 — 흑자 5 년 회사만 적용 권장.
- "ROE 15% = 좋다" 단정 X — 5 동인 분포로 구조적 우위 (margin·turnover) vs 일시적 (leverage 상승) 구분.
