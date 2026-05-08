---
id: "engines.macro.forecast"
title: "Macro - 예측"
kind: curated
scope: builtin
status: observed
category: engines
purpose: "macro 엔진의 예측 축 응용 — LEI + Cleveland Fed 침체확률 + Sahm + Hamilton RS + GaR."
whenToUse:
  - "macro"
  - "forecast"
  - "예측"
  - "LEI + Cleveland Fed 침체확률 + Sahm + Hamilton RS + GaR"
inputs:
  - "market (KR / US, default KR)"
  - "axis 옵션 / scenario / overrides"
outputs:
  - "축별 dict 또는 DataFrame"
  - "evidence refs"
  - "한계와 가정"
capabilityRefs:
  - "macro"
knowledgeRefs:
  - "engines.macro"
  - "engines.gather"
  - "engines.story"
sourceRefs:
  - "dartlab://skills/engines.macro.forecast"
requiredEvidence:
  - "market"
  - "indicator"
  - "dateRef"
  - "valueRef"
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
  - "기준일 / source 없는 매크로 숫자 인용 금지."
  - "기업 재무 분석을 macro 로 대체하지 않는다."
  - "macro 결과를 analysis 내부 계산처럼 섞지 않는다."
  - "침체확률 한 모델 (Cleveland Fed) 결과를 다른 모델 (Sahm / GaR) 검증 없이 인용 금지."
  - "LEI / Sahm 등 미국 지표를 KR 시장에 그대로 적용 금지 — KR composite leading index 분리."
failureModes:
  - "LEI 의 산업 구성 차이 (미국 vs 한국) 미반영"
  - "Sahm 룰 (실업률 3 개월 평균 - 12 개월 최저) 의 KR 적용 적합성 미명시"
  - "Hamilton RS (Regime Switching) 의 학습 기간 의존성 무시"
  - "GaR (Growth-at-Risk) 분포 추정의 신뢰구간 미언급"
  - "예측 모델 간 시그널 충돌 시 단일 모델 선택 사유 없음"
examples:
  - "Cleveland Fed 침체확률 추이"
  - "Sahm 룰 + KR 실업률 적용"
  - "LEI 6 개월 변화율 + 침체 신호"
  - "GaR 5% 분위 충격 시나리오"
linkedSkills:
  - engines.macro
  - engines.macro.cycle
  - engines.macro.crisis
  - engines.macro.summary
source:
  type: manual_skill
  format: markdown
lastUpdated: '2026-05-07'
---

## 엔진 역할

macro 엔진의 예측 축 응용 skill — LEI + Cleveland Fed 침체확률 + Sahm + Hamilton RS + GaR. 6막 — 예측. SSOT 는 `_AXIS_REGISTRY` (`src/dartlab/macro/__init__.py`).

## 공개 호출 방식

```python
import dartlab

# 1. KR 시장
result = dartlab.macro("forecast", market="KR")

# 2. US 시장
result = dartlab.macro("forecast", market="US")
```

## 호출 동작

market 의 외부 SSOT (HF prebuild · ECOS · FRED) 를 읽어 예측 축 신호 / 레짐 / 한계를 산출한다. 결손 / 비교 불가 indicator 는 결과 dict 의 `flags` / null 로 표현하며 0 으로 채우지 않는다. Company 단위 재무 해석은 `engines.analysis` 로 분리. 자세한 동작은 base SKILL `engines.macro` + `_AXIS_REGISTRY['forecast'].fn` 함수 docstring 참조.

## 대표 반환 형태

dict 또는 DataFrame 반환. 공통 키:

- `market`: 대상 시장 (KR / US)
- `latestAsOf` / `date`: 데이터 기준일
- `indicator` / `value` / `unit`: 핵심 지표
- `signal` / `regime` / `score`: 축 고유 판정
- `source` / `basis`: 데이터 출처 + 근거
- `assumptions` / `flags`: 가정 · 결손 / 이상 신호

전체 키는 base SKILL `engines.macro` 표 + `_AXIS_REGISTRY['forecast'].fn` 함수 docstring 으로 검산.

## 기본 실행 순서

1. market (KR / US), 기준일, 옵션 (scenario · overrides) 확정.
2. 위 공개 호출 그대로 실행.
3. `latestAsOf` · `indicator` · `flags` · `assumptions` 점검.
4. 숫자 claim 은 `valueRef` / `dateRef` / `executionRef` 에 묶음.
5. 다축 narrative 조립은 `engines.story`. 시장 macro vs 기업 재무 (analysis) 는 분리 유지.

## 기본 검증

이 skill 은 공개 실행 문서다. 본 axis 호출 방식, 반환 키, 오류 / 제한 동작이 변경되면 같은 변경에서 본 파일을 갱신한다. SSOT 는 `_AXIS_REGISTRY` (`src/dartlab/macro/__init__.py`) + 함수 docstring.
