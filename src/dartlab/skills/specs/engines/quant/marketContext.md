---
id: engines.quant.marketContext
title: Quant Market Context 축
kind: curated
scope: builtin
status: observed
category: engines
purpose: dartlab.quant("시장맥락", "005930") 형태로 종목의 시장 베타 + 거시 민감도 (USDKRW/금리/CPI/M2) + 외국인+기관 수급 강도 1 행 evidence 를 산출한다. 가격-거시 OLS (일별 252 d). 펀더멘털-거시 OLS (`scan.macroBeta`, 연간 매출 vs 거시) 와 책임 분리. 트리거 — '시장맥락', 'marketContext', '맥락'.
whenToUse:
  - 종목의 시장 민감도 + 환율/금리 베타 + 수급 강도를 한 번에 묻고 싶을 때
  - 수출주 (USDKRW β > 0) 와 내수주 (β ≈ 0) 의 부호 검증
  - 금리 인하/인상 시 종목 영향도 사전 진단
  - 외국인+기관 수급의 60 d 누적 / z-score 조사
inputs:
  - stockCode (str, 필수)
  - market (str, "KR" / "US" / "auto", 기본 "auto")
  - lookbackDays (int, 기본 252)
  - macroVars (list[str] 또는 None) — None 이면 KR 4 default / US 4 default
outputs:
  - dict — stockCode, market, lookbackDays, dateRef, lastClose, marketBeta, marketAlpha, marketR2, nObsCAPM, {macro}Beta + _r2, smartMoneyNet60d, smartMoneyZ60d, flowMomentum20d, flowAvailable, summary
capabilityRefs:
  - quant
  - Company.quant
knowledgeRefs:
  - engines.quant
  - engines.gather
sourceRefs:
  - dartlab://skills/engines.quant.marketContext
requiredEvidence:
  - target (stockCode)
  - period (lookbackDays, dateRef)
  - benchmark (KOSPI/KOSDAQ/SPX)
  - metric (marketBeta, *Beta + _r2)
  - dateRef
  - executionRef
runtimeCompatibility:
  server:
    status: supported
  localPython:
    status: supported
  mcp:
    status: supported
  webAi:
    status: supported
  pyodide:
    status: limited
failureModes:
  - 종목 OHLCV < 60 일 → "데이터 부족" error 반환
  - 거시 wide DF 수집 실패 → macroBetaError 키만 남김 (다른 키 정상 계산)
  - flow 데이터 없음 (US 종목 또는 수집 실패) → flowAvailable=False
  - β 만 인용하고 R² 누락 (의미 있는 베타인지 R² 로 검증)
forbidden:
  - 펀더멘털-거시 회귀 (재무 vs GDP) — `scan.macroBeta` 가 SSOT
  - β 부호만 보고 "이 종목은 환율에 민감하다" 단정 — R² < 0.05 면 noise 가능성
  - statsmodels / scipy import 추가
examples:
  - 005930 시장 맥락 (β + USDKRW + 수급)
  - 035420 내수주 검증 (USDKRW β ≈ 0)
  - AAPL US 자동감지 + FEDFUNDS β
procedure:
  - dartlab.quant("시장맥락", "005930") 호출
  - 결과의 marketBeta / marketR2 → CAPM 검증
  - 각 매크로 β + _r2 쌍으로 인용 (R² 작으면 noise 표시)
  - smartMoneyZ60d > +1 (대형 매수) / < -1 (대형 매도) 해석
  - summary 한 줄 (β=, USDKRW β=, smartMoney Z=)
linkedSkills:
  - engines.quant
  - engines.scan.macroBeta
  - engines.gather
source:
  type: manual_skill
  format: markdown
lastUpdated: '2026-05-09'
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

- **CAPM**: r_i = α + β r_m + ε. β = `marketBeta`, α (annualized) = `marketAlpha`, R² = `marketR2`. 시장 지수는 종목 상장 시장 (KOSPI/KOSDAQ) 또는 SPX. `fetch_benchmark_ohlcv` SSOT 재사용.
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
- benchmark: 종목 상장 시장 (KOSPI/KOSDAQ/SPX) — `fetch_benchmark_ohlcv` 의 결과
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
