---
id: engines.quant.marketContext
title: Quant Market Context
category: engines
kind: curated
status: observed
purpose: 현재 시장 환경 측정 — VIX/KOSPI mode/sector breadth — axis 호출 전 사전 진단.
sourceRefs:
  - dartlab://skills/engines.quant.marketContext
knowledgeRefs:
  - engines.quant
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
whenToUse:
  - axis 호출 전 사전 진단
  - 현재 시장 환경 측정
  - VIX / KOSPI mode / sector breadth
---

## 엔진 역할

`marketContext` 축은 가격 시계열 기반 — 일별 log-return 회귀로 시장 베타 + 거시 변수 베타 + 수급 강도를 1 행 evidence 로 묶는다. 모든 회귀는 numpy-only OLS 로 산출.

## scan.macroBeta 와 책임 분리

| 항목 | quant.marketContext | scan.macroBeta |
|---|---|---|
| 입력 | 일별 가격 시계열 | 연간 매출/이익 시계열 |
| 회귀 단위 | 일별 log-return | 연간 매출 성장률 |
| 윈도우 | 252 d (기본) | 5+ 년 |
| 목표 | 시장 민감도 (β) + 거시 민감도 (FX/금리/물가) + 수급 | 펀더멘털 민감도 (재무 성장 vs GDP/금리/환율) |
| 컬럼 | usdkrwBeta · baseRateBeta · cpiBeta · m2Beta | gdpBeta · rateBeta · fxBeta |
| 사용 시점 | 단기~중기 시장 변동 진단 | 중장기 펀더멘털 시나리오 |

같은 "거시 민감도" 라도 측정 대상 (가격 vs 매출) · 시간 단위 (일/연) · 컬럼명 모두 분리 — silent alias 회피.

## 공개 호출 방식

```python
import dartlab

# KR 기본 (USDKRW · BASE_RATE · CPI · M2)
r = dartlab.quant("시장맥락", "005930")

# 윈도우 2 년
r = dartlab.quant("marketContext", "035420", lookbackDays=504)

# US 자동감지 (FEDFUNDS · DGS10 · DCOILWTICO · CPIAUCSL)
r = dartlab.quant("marketContext", "AAPL")

# 사용자 명시 변수
r = dartlab.quant("시장맥락", "AAPL", macroVars=["FEDFUNDS", "DGS10"])
```

## 호출 동작

`dartlab.quant("marketContext", stockCode, ...)` 가 dispatch 진입. 다음 순서:

1. stockCode → market auto-detect
2. lookback 일수만큼 OHLCV + 시장 지수 + 거시 변수 동시 수집
3. 일별 수익률 시계열 정렬 (날짜 join)
4. 회귀 모델 (CAPM · 거시 · 수급) 각각 fit
5. β / α / R² + 수급 metric 통합 dict 반환

## 회귀 모델

- **CAPM**: r_i = α + β r_m + ε. β = `marketBeta`, α (annualized) = `marketAlpha`, R² = `marketR2`. 시장 지수는 종목 상장 시장 (KOSPI/KOSDAQ) 또는 SPX. `fetchBenchmarkOhlcv` SSOT 재사용.
- **거시 회귀**: r_i = α + β · ΔX + ε. ΔX 는 변수에 따라:
  - 금리 (BASE_RATE/FEDFUNDS/DGS10) → 단순 차분 Δ
  - 그 외 (USDKRW/CPI/M2/oil) → Δlog
  - 결측은 forward-fill (월별 변수 호환). R² 가 작을 수 있다.
- **수급 강도** (KR only): smart money = foreignNet + institutionNet. `smartMoneyNet60d` (60 d 합), `smartMoneyZ60d` (60 d 평균의 252 d 분포 z-score), `flowMomentum20d` (20 d 합).

## 대표 반환 형태

```text
{
  "stockCode": "005930",
  "market": "KR",
  "lookbackDays": 252,
  "dateRef": "2026-05-08",
  "lastClose": 75000.0,
  "marketBeta": 1.12,
  "marketAlpha": 0.035,        # annualized
  "marketR2": 0.482,
  "nObsCAPM": 250,
  "usdkrwBeta": -0.812,        # 음수: 원화 강세 시 +
  "usdkrwBeta_r2": 0.045,
  "baseRateBeta": 0.024,
  "baseRateBeta_r2": 0.002,
  "cpiBeta": 0.18,
  "cpiBeta_r2": 0.001,
  "m2Beta": 0.66,
  "m2Beta_r2": 0.003,
  "macroVarsUsed": ["USDKRW", "BASE_RATE", "CPI", "M2"],
  "smartMoneyNet60d": 12345678,
  "smartMoneyZ60d": +1.23,
  "flowMomentum20d": 4567890,
  "flowAvailable": true,
  "flowNObs": 1006,
  "macroSource": "wide",          # wide / singleFallback / none
  "summary": "β=1.12 · USDKRW β=-0.812 · smartMoney Z=+1.23"
}
```

`macroSource` 단일 키 — wide 호출 성공 시 `"wide"`, wide 실패 후 var 별 fetch 가 일부 성공하면 `"singleFallback"`, 둘 다 실패면 `"none"`. wide 실패 사유는 `macroWideErrorType` 진단 키로 별도 보존.

## evidence 기준

- target: `stockCode`
- period: `lookbackDays`, `dateRef`
- benchmark: 종목 상장 시장 (KOSPI/KOSDAQ/SPX) — `fetchBenchmarkOhlcv` 의 결과
- metric: `marketBeta`, `*Beta` 키 + `_r2` 쌍
- value: 숫자 + R² 함께
- dateRef: `dateRef`
- executionRef: 호출 캡처

## 자기 검증 노트

- 005930 (수출주) `usdkrwBeta` 음/양 부호는 시기에 따라 변할 수 있으나 |β| > 0.3 기대 (FX 민감)
- 035420 (네이버, 내수 IT) `|usdkrwBeta|` 작음 — 환율 비민감
- KOSPI 종목 `marketBeta` ∈ [0.3, 1.8] 합리적 범위
- US 종목 호출 시 flow 자동 비활성 (flowAvailable=False)
- R² < 0.05 인 베타는 *noise* — summary 인용 시 신중

## 한계 및 비목표

- 펀더멘털 (재무 vs 거시) 회귀는 `scan.macroBeta` 가 책임. 변수명도 분리 (gdpBeta/rateBeta vs cpiBeta/baseRateBeta)
- 거시 변수 빈도 mismatch (월별 CPI 가 일별 join 시 forward-fill) → R² 가 작은 건 *분포의 본질*
- 다변량 회귀 (multiple regression with controls) 는 본 축 범위 밖 — 단변량 OLS 로 시작
- VAR / cointegration / Granger causality 등 시계열 인과는 본 축 외부

## 기본 검증

스킬 변경 시 본 파일 + `engines.quant` SKILL.md 의 marketContext 행 + `tests/test_quant_marketContext.py` + `_AXIS_REGISTRY["marketContext"]` 4 곳을 같은 변경에서 갱신한다.
