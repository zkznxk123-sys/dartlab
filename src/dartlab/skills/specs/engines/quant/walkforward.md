---
id: engines.quant.walkforward
title: Quant Walk-forward Validation
category: engines
kind: curated
status: observed
purpose: 전략 walk-forward — train/test window 슬라이딩, in-sample overfitting 회피.
sourceRefs:
  - dartlab://skills/engines.quant.walkforward
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
  - 전략 walk-forward 검증
  - in-sample overfitting 회피
  - train/test window 슬라이딩
---

## 엔진 역할

quant 엔진의 워크포워드 축 응용 skill — Lopez de Prado 슬라이딩 OOS Sharpe + DSR + PBO. strategy 그룹. SSOT 는 `_AXIS_REGISTRY` (`src/dartlab/quant/__init__.py`).

## 공개 호출 방식

```python
import dartlab

# 1. 문자열 호출
result = dartlab.quant("walkforward", "005930")

# 2. accessor 호출 (동등)
result = dartlab.quant.walkforward("005930")
```

## 호출 동작

종목 005930 의 가격 · 재무 · 시계열 snapshot 을 읽어 워크포워드 축 계산을 수행한다. Lopez de Prado 슬라이딩 OOS Sharpe + DSR + PBO. 결손 / 비교 불가 케이스는 결과 dict 또는 DataFrame 의 `flags` / null 로 표현하며 0 으로 채우지 않는다. 자세한 동작은 base SKILL `engines.quant` + `_AXIS_REGISTRY['walkforward'].fn` 함수 docstring 참조.

### rule_factory 옵션 (forecast OOS 검증)

기본 호출은 정적 Rule 슬라이스 — 같은 entry/exit 시계열을 IS/OOS 에 그대로 적용. forecast 모델처럼 *IS fit + OOS predict* 패턴은 ``walkForward(close, rule=None, rule_factory=...)`` 로 호출.

```python
from dartlab.quant.benchmark.forecast import forecastRuleFactory
from dartlab.quant.strategy.backtest import walkForward

factory = forecastRuleFactory(threshold=0.002, models=["ar1"])
bt = walkForward(close, rule=None, rule_factory=factory, train=120, test=20, step=20)
bt.cpcv["refit_count"]   # fold 마다 재학습 횟수 (= n_folds)
bt.cpcv["is_sharpes"]    # IS 학습 fold 별 Sharpe
bt.cpcv["oos_sharpes"]   # OOS 검증 fold 별 Sharpe
```

`rule_factory(is_close, oos_len) -> Rule` 시그니처. 반환 Rule 의 length 는 정확히 `train + test`. 어긋나면 `BacktestResult(status="error", reason="length 불일치")`.

## 대표 반환 형태

strategy 그룹 표준에 따른 dict 또는 DataFrame 반환. 공통 키:

- `stockCode` / `corpName`: 대상 종목 (해당 시)
- `latestAsOf` / `priceDate`: 데이터 기준일
- 축 고유 metric / score / verdict / rank column (정확한 spec 은 `_AXIS_REGISTRY['walkforward'].fn` 함수 docstring 검산)
- `flags` / `assumptions`: 결손 · 가정

전체 키는 base SKILL `engines.quant` 표 + 함수 docstring 으로 검산.

## 기본 실행 순서

1. 대상 종목 (또는 종목 리스트), 기준일, benchmark 확정.
2. 위 공개 호출 그대로 실행.
3. `latestAsOf` / 결손 종목 / `flags` / `assumptions` 점검.
4. 숫자 claim 은 `valueRef` / `dateRef` / `executionRef` 에 묶음.
5. 다축 narrative 조립은 `engines.story` 또는 상위 recipe 가 담당.

## 기본 검증

이 skill 은 공개 실행 문서다. 본 axis 호출 방식, 반환 키, 오류 / 제한 동작이 변경되면 같은 변경에서 본 파일을 갱신한다. SSOT 는 `_AXIS_REGISTRY` (`src/dartlab/quant/__init__.py`) + 함수 docstring.
