---
title: Financial Data
---

# 재무 데이터

재무제표(BS/IS/CF) + 47개 비율 + 시계열 + 계정 표준화.

## 재무제표

```python
c = dartlab.Company("005930")

c.show("BS")                    # 재무상태표 (자산/부채/자본)
c.show("IS")                    # 손익계산서 (매출/영업이익/순이익) — 분기 (기본)
c.show("IS", freq="Y")          # 연간 합산
c.show("CF")                    # 현금흐름표 (영업/투자/재무)
c.show("CIS")                   # 포괄손익계산서
c.show("SCE")                   # 자본변동표
```

## 특정 계정 추출 — select

```python
# 특정 계정만 추출
c.select("IS", ["매출액", "영업이익", "당기순이익"])

# 기간 필터
c.select("BS", ["자산총계"], period=["2023", "2024"])

# 차트 시각화
c.select("IS", ["매출액"]).chart()

# dict 변환
c.select("IS", ["매출액", "영업이익"]).toDict()
```

## 재무비율 — ratios

47개 비율을 한 번에 산출한다. DataFrame 형태로 반환.

```python
ratios_df = c.show("ratios")    # 47 비율 × 기간 DataFrame
ratios_df

# 카테고리: 수익성/안정성/성장성/효율성/현금흐름/부실예측/주당/밸류에이션
# 항목 예: roe, roa, operatingMargin, netMargin, ebitdaMargin
#         debtRatio, currentRatio, interestCoverage, netDebtRatio
#         revenueGrowth, operatingProfitGrowth
#         totalAssetTurnover, inventoryTurnover, ccc
#         fcf, operatingCfMargin
#         altmanZScore, ohlsonProbability, beneishMScore, piotroskiFScore
#         eps, bps, per, pbr

# 특정 비율 행만 추출
c.select("ratios", ["ROE", "ROA", "영업이익률"])
```

## 비율 시계열

```python
c.show("ratioSeries")    # 비율 × 연도 시계열 DataFrame

# 특정 비율 시계열만
c.select("ratioSeries", ["ROE"])
```

## 계정 표준화

상장사의 재무제표는 같은 개념이라도 다른 계정명을 사용한다.

```
ifrs-full_Revenue          → 삼성전자
dart_OperatingIncomeLoss   → LG화학
dart_ConstructionRevenue   → 현대건설
```

dartlab은 7단계 매핑 파이프라인으로 이를 **하나의 `매출액`**으로 통일한다.
15,850,000행 중 **98.7%**가 표준 계정에 매핑된다.

## EDGAR 호환

```python
us = dartlab.Company("AAPL")

us.show("BS")                 # US-GAAP Balance Sheet
us.select("IS", ["매출액"])    # 한국어로 질의 → 자동 번역
us.select("IS", ["revenue"])  # 영문으로도 가능
```
