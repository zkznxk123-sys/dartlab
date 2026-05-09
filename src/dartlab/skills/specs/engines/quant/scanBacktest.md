---
id: engines.quant.scanBacktest
title: Quant scanBacktest top-level helper
kind: curated
scope: builtin
status: observed
category: engines
purpose: dartlab.quant.scanBacktest(scanResult, signalFn=, style=, topN=, weighting=) 형태로 scan 결과 DataFrame 의 universe 를 받아 종목별 Rule 빌드 → multi_asset_backtest 호출 → BacktestResult.scanContext 에 universe 출처 SHA-1 기록. axis 미등록 (top-level helper). 트리거 — 'scanBacktest', 'scan→quant', 'universe → backtest'.
whenToUse:
  - scan 으로 추린 universe 에 quant 백테스트를 직접 적용하고 싶을 때
  - signalFn (forecast / momentum / 사용자 정의) → 종목별 entry/exit 로 변환 후 멀티자산 백테스트
  - style preset (trendFollow / meanReversion 등 8 종) 을 universe 에 일괄 적용
  - universe 출처 추적 가능한 결정적 SHA-1 hash 가 필요할 때
inputs:
  - scanResult (pl.DataFrame, 필수, stockCode/종목코드/stock_code 컬럼 보유)
  - signalFn (Callable[[close], np.ndarray[bool]] 또는 None)
  - style (str 또는 None) — STYLE_REGISTRY 8 styles 키
  - universeCol (str, "auto" 면 자동 감지)
  - topN (int, 기본 20)
  - weighting (str, "equal" / "inv_vol" / "risk_parity")
  - fee_bps · slip_bps (float)
outputs:
  - BacktestResult — equity / returns / trades / sharpe / sortino / mdd / dsr / pbo / scanContext (universeSize, universeCol, topN, scanResultHash, signalSource, weighting)
capabilityRefs:
  - quant.scanBacktest
  - Company.quant.scanBacktest
knowledgeRefs:
  - engines.quant
  - engines.scan
  - engines.gather
sourceRefs:
  - dartlab://skills/engines.quant.scanBacktest
requiredEvidence:
  - target (universe 종목 리스트)
  - period (BacktestResult.period)
  - benchmark (style 또는 signalFn)
  - metric (sharpe / mdd / dsr)
  - scanContext.scanResultHash (universe 출처)
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
  - 빈 scanResult → BacktestResult(status="error", reason="empty scanResult")
  - signalFn 과 style 둘 다 미지정 → error
  - universe 컬럼 미감지 → error (후보 4종 알려줌)
  - 미등록 style → KeyError + 후보 목록
  - 수수료/슬리피지/리밸런싱 가정 누락 인용 — 백테스트 가정 명시 의무
forbidden:
  - axis dispatch 호출 시도 (`dartlab.quant("scanBacktest", ...)`) — 미등록
  - scan 모듈 직접 import (architecture: quant → scan 금지)
  - 백테스트 결과 미래 성과 보장처럼 표현
  - scanContext.scanResultHash 누락 인용 (universe 출처 추적 깨짐)
examples:
  - scan("valuation") → 등급 A → topN=20 → trendFollow 스타일 백테스트
  - scan("ranking") → top10 → forecast signalFn 변환 → 백테스트
  - signalFn=lambda c: c > moving_avg(c, 20) (단순 모멘텀)
procedure:
  - scanResult = dartlab.scan(...) (사용자 사전 sort/filter)
  - dartlab.quant.scanBacktest(scanResult, style=..., topN=20, weighting="equal")
  - result.scanContext 로 universe 출처 추적 + result.sharpe / mdd / dsr 인용
  - 기간 (BacktestResult.period), 수수료 (fee_bps), 슬리피지 (slip_bps), 리밸런싱 (weighting) 명시
linkedSkills:
  - engines.quant
  - engines.scan
  - engines.quant.forecast
source:
  type: manual_skill
  format: markdown
lastUpdated: '2026-05-09'
---

## 엔진 역할

`scanBacktest` 는 scan 결과 universe + signalFn (또는 style) → ``multi_asset_backtest`` 호출의 wrapper. 내부 로직 0 — 모든 백테스트는 ``multi_asset_backtest`` SSOT 가 처리. 본 helper 의 책임은 ① universe 추출, ② signalFn → Rule 변환, ③ scanContext SHA-1 기록.

## architecture 룰 준수

- quant → scan import **금지** (역방향). scan 결과는 사용자가 호출자에서 추출해 ``pl.DataFrame`` 입력으로 전달.
- 본 helper 는 ``dartlab.scan`` 을 import 하지 않음 — 단지 stockCode 컬럼이 있는 DataFrame 만 받는다.
- axis 미등록 — registry dispatcher 의 ``fn(stockCode=stockCode, **kwargs)`` 계약은 첫 인자가 stockCode. scanBacktest 의 첫 인자는 DataFrame 이라 어긋남. ``dartlab.quant("scanBacktest", ...)`` 호출 X.

## 공개 호출 방식

```python
import dartlab as dl
import polars as pl

# scan 으로 valuation 등급 A 추리고 trendFollow 스타일 백테스트
top = dl.scan("valuation").filter(pl.col("등급") == "A").sort("PER").head(20)
result = dl.quant.scanBacktest(top, style="trendFollow", topN=20)
result.sharpe, result.mdd, result.scanContext

# signalFn 직접 정의 — 단순 momentum 시그널
import numpy as np
def momentum_signal(close):
    sma_short = np.convolve(close, np.ones(10) / 10, mode="same")
    sma_long = np.convolve(close, np.ones(50) / 50, mode="same")
    return sma_short > sma_long

result = dl.quant.scanBacktest(top, signalFn=momentum_signal, topN=20)
```

## signalFn / style 우선순위

1. `signalFn` 명시 → 우선 (signalFn 으로 Rule 빌드)
2. signalFn 미지정 + `style` 명시 → STYLE_REGISTRY (`trendFollow` / `meanReversion` / `breakout` / `dipBuy` / `eventDriven` / `flowFollow` / `lowVolDefensive` / `seasonalKR`)
3. 둘 다 미지정 → error

## universe 컬럼 자동 감지

`universeCol="auto"` (default) 시 다음 우선순위로 첫 매칭 컬럼 사용:
1. `stockCode`
2. `종목코드`
3. `stock_code`
4. `corp_code`

명시 override: `universeCol="myCustomCol"`.

## scanContext (BacktestResult 신규 필드)

```text
{
  "universeSize": 20,
  "universeCol": "stockCode",
  "topN": 20,
  "scanResultHash": "a3b1c2d4e5f60718",  # 결정적 SHA-1 (16 자)
  "signalSource": "style:trendFollow",   # 또는 "signalFn"
  "weighting": "equal"
}
```

같은 universe 입력 → 같은 hash. 사용자가 다른 sort/filter 적용 → 다른 hash. universe 출처 추적 가능.

## evidence 기준

- target: universe 종목 리스트 (BacktestResult.trades 의 stock_code 컬럼 or scanContext)
- period: BacktestResult.period
- benchmark: signalFn 또는 style 명시
- metric: sharpe / mdd / dsr (cpcv 있으면 PBO 도)
- 가정: fee_bps, slip_bps, weighting
- scanContext.scanResultHash: universe 출처

## 자기 검증 노트

- 빈 scanResult → BacktestResult(status="error", reason="empty scanResult")
- signalFn / style 둘 다 미지정 → error
- 같은 universe 두 번 호출 → 같은 scanResultHash
- multi_asset_backtest 직접 호출 vs scanBacktest 의 결과 sharpe ε 이내 일치 (회귀 가드)

## 한계 및 비목표

- universe 의 등급/sort 자동 추출 X — 사용자가 사전에 ``scanResult.filter(...).sort(...).head(N)`` 책임
- multi-period 백테스트 (월별 리밸런싱) 는 본 helper 범위 밖 — ``multi_asset_backtest`` 가 정적 가중치만 지원
- forecast 모델의 fold 마다 재학습 (walk-forward refit) 은 후속 PR

## 기본 검증

스킬 변경 시 본 파일 + `engines.quant` SKILL.md 의 top-level helper 섹션 + `tests/test_quant_scanBacktest.py` + `Quant.scanBacktest` 메서드 (`__init__.py`) + `BacktestResult.scanContext` 필드 5 곳을 같은 변경에서 갱신한다.
