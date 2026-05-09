---
id: "engines.quant.walkforward"
title: "Quant - 워크포워드"
kind: curated
scope: builtin
status: observed
category: engines
purpose: "quant 엔진의 워크포워드 축 응용 — Lopez de Prado 슬라이딩 OOS Sharpe + DSR + PBO."
whenToUse:
  - "quant"
  - "walkforward"
  - "워크포워드"
  - "Lopez de Prado 슬라이딩 OOS Sharpe + DSR + PBO"
inputs:
  - "종목코드 또는 종목 리스트"
  - "기준 기간"
  - "benchmark / 가정 (해당 시)"
outputs:
  - "축별 dict 또는 DataFrame"
  - "evidence refs"
  - "한계와 가정"
capabilityRefs:
  - "quant"
  - "Company.quant"
knowledgeRefs:
  - "engines.quant"
  - "engines.gather"
  - "engines.analysis"
sourceRefs:
  - "dartlab://skills/engines.quant.walkforward"
requiredEvidence:
  - "target"
  - "period"
  - "metric"
  - "benchmark"
  - "valueRef"
  - "dateRef"
  - "executionRef"
expectedOutputs:
  - "공개 호출"
  - "대표 반환 형태"
  - "검증 결과"
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
forbidden:
  - "성과 보장 표현 금지."
  - "기간 / benchmark / 가정 명시 없이 수익률 인용 금지."
  - "정량 신호를 인과 분석 결론으로 제시 금지."
  - "Walk-forward OOS Sharpe 결과의 슬라이딩 윈도우 / 학습 기간 명시 없이 인용 금지."
  - "DSR (Deflated Sharpe Ratio) / PBO (Probability of Backtest Overfitting) 미산출 시 OOS 결과 단정 금지."
failureModes:
  - "슬라이딩 윈도우 길이 (1Y vs 3Y) 의 학습 데이터 불충분 위험"
  - "OOS 기간 (3M vs 1Y) 별 Sharpe 변동성"
  - "PBO 계산의 partition 수 의존성"
  - "DSR 의 trial 수 (number of strategies tried) 모호"
  - "데이터 스누핑 (전체 룰 테스트 후 walk-forward 적용)"
examples:
  - "스타일 전략 walk-forward 검증"
  - "슬라이딩 OOS Sharpe 계산"
  - "PBO + DSR 결합 검증"
  - "walk-forward + 백테스트 비교"
linkedSkills:
  - engines.quant
  - engines.quant.backtest
  - engines.quant.signalReview
  - engines.quant.strategy
source:
  type: manual_skill
  format: markdown
lastUpdated: '2026-05-07'
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

기본 호출은 정적 Rule 슬라이스 — 같은 entry/exit 시계열을 IS/OOS 에 그대로 적용. forecast 모델처럼 *IS fit + OOS predict* 패턴은 ``walk_forward(close, rule=None, rule_factory=...)`` 로 호출.

```python
from dartlab.quant.forecast import forecastRuleFactory
from dartlab.quant.strategy.backtest import walk_forward

factory = forecastRuleFactory(threshold=0.002, models=["ar1"])
bt = walk_forward(close, rule=None, rule_factory=factory, train=120, test=20, step=20)
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
