---
id: "engines.quant.regime"
title: "Quant - 레짐"
kind: curated
scope: builtin
status: observed
category: engines
purpose: "quant 엔진의 레짐 축 응용 — Hamilton 2-state HMM (bull/bear), 추세추종 신호."
whenToUse:
  - "quant"
  - "regime"
  - "레짐"
  - "Hamilton 2-state HMM (bull/bear), 추세추종 신호"
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
  - "dartlab://skills/engines.quant.regime"
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
  - "Hamilton 2-state HMM (bull / bear) 의 학습 윈도우 의존성 명시 없이 인용 금지."
  - "현재 레짐 추정 (Viterbi) 결과를 미래 레짐 예측으로 단정 금지."
failureModes:
  - "HMM 모수 추정 (EM) 의 local optima 의존성"
  - "학습 윈도우 길이 (5Y vs 10Y) 별 레짐 식별 차이"
  - "2-state 가정의 KR 시장 적합성 (3-state 필요 가능성)"
  - "레짐 전환 신호와 후행 검증 (lag) 무시"
  - "벤치마크 (KOSPI vs 섹터) 별 레짐 차이"
examples:
  - "KR 시장 레짐 (bull / bear) 시계열"
  - "현재 레짐 추정 (Viterbi)"
  - "레짐별 자산 영향"
  - "추세추종 신호 + 레짐 결합"
linkedSkills:
  - engines.quant
  - engines.macro.cycle
  - engines.quant.style
  - engines.quant.signalReview
source:
  type: manual_skill
  format: markdown
lastUpdated: '2026-05-07'
---

## 엔진 역할

quant 엔진의 레짐 축 응용 skill — Hamilton 2-state HMM (bull/bear), 추세추종 신호. technical 그룹. SSOT 는 `_AXIS_REGISTRY` (`src/dartlab/quant/__init__.py`).

## 공개 호출 방식

```python
import dartlab

# 1. 문자열 호출
result = dartlab.quant("regime", "005930")

# 2. accessor 호출 (동등)
result = dartlab.quant.regime("005930")
```

## 호출 동작

종목 005930 의 가격 · 재무 · 시계열 snapshot 을 읽어 레짐 축 계산을 수행한다. Hamilton 2-state HMM (bull/bear), 추세추종 신호. 결손 / 비교 불가 케이스는 결과 dict 또는 DataFrame 의 `flags` / null 로 표현하며 0 으로 채우지 않는다. 자세한 동작은 base SKILL `engines.quant` + `_AXIS_REGISTRY['regime'].fn` 함수 docstring 참조.

## 대표 반환 형태

technical 그룹 표준에 따른 dict 또는 DataFrame 반환. 공통 키:

- `stockCode` / `corpName`: 대상 종목 (해당 시)
- `latestAsOf` / `priceDate`: 데이터 기준일
- 축 고유 metric / score / verdict / rank column (정확한 spec 은 `_AXIS_REGISTRY['regime'].fn` 함수 docstring 검산)
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
