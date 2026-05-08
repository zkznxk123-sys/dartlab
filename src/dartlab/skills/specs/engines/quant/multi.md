---
id: "engines.quant.multi"
title: "Quant - 멀티자산"
kind: curated
scope: builtin
status: observed
category: engines
purpose: "quant 엔진의 멀티자산 축 응용 — 멀티 종목 포트폴리오 백테스트 (equal/inv_vol/risk_parity 가중)."
whenToUse:
  - "quant"
  - "multi"
  - "멀티자산"
  - "멀티 종목 포트폴리오 백테스트 (equal/inv_vol/risk_parity 가중)"
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
  - "dartlab://skills/engines.quant.multi"
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
  - "포트폴리오 가중 (equal / inv_vol / risk_parity) 명시 없이 결과 비교 금지."
  - "리밸런싱 주기 (monthly / quarterly) 명시 없이 누적수익률 인용 금지."
failureModes:
  - "포트폴리오 종목 수 (5 vs 30) 별 분산효과 차이 무시"
  - "거래비용 / 슬리피지 미반영"
  - "inv_vol / risk_parity 의 vol 추정 윈도우 (60D vs 252D) 차이"
  - "리밸런싱 빈도와 거래비용 trade-off 미언급"
  - "백테스트 기간이 한 가지 시장국면 (강세장 only) 으로 편향"
examples:
  - "5 종목 동일가중 포트폴리오 백테스트"
  - "inverse-volatility 가중 포트폴리오"
  - "risk-parity 가중 multi-asset"
  - "월별 리밸런싱 효과"
linkedSkills:
  - engines.quant
  - engines.quant.allocation
  - engines.quant.riskparity
  - engines.quant.backtest
source:
  type: manual_skill
  format: markdown
lastUpdated: '2026-05-07'
---

## 엔진 역할

quant 엔진의 멀티자산 축 응용 skill — 멀티 종목 포트폴리오 백테스트 (equal/inv_vol/risk_parity 가중). strategy 그룹. SSOT 는 `_AXIS_REGISTRY` (`src/dartlab/quant/__init__.py`).

## 공개 호출 방식

```python
import dartlab

# 1. 문자열 호출 (포트폴리오 — 종목 리스트)
result = dartlab.quant("multi", ["005930", "000660"])

# 2. accessor 호출 (동등)
result = dartlab.quant.multi(["005930", "000660"])
```

## 호출 동작

포트폴리오 종목 리스트 의 가격 · 재무 · 시계열 snapshot 을 읽어 멀티자산 축 계산을 수행한다. 멀티 종목 포트폴리오 백테스트 (equal/inv_vol/risk_parity 가중). 결손 / 비교 불가 케이스는 결과 dict 또는 DataFrame 의 `flags` / null 로 표현하며 0 으로 채우지 않는다. 자세한 동작은 base SKILL `engines.quant` + `_AXIS_REGISTRY['multi'].fn` 함수 docstring 참조.

## 대표 반환 형태

strategy 그룹 표준에 따른 dict 또는 DataFrame 반환. 공통 키:

- `stockCode` / `corpName`: 대상 종목 (해당 시)
- `latestAsOf` / `priceDate`: 데이터 기준일
- 축 고유 metric / score / verdict / rank column (정확한 spec 은 `_AXIS_REGISTRY['multi'].fn` 함수 docstring 검산)
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
