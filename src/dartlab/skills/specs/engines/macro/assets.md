---
id: "engines.macro.assets"
title: "Macro - 자산"
kind: curated
scope: builtin
status: observed
category: engines
purpose: "macro 엔진의 자산 축 응용 — 5대 자산 심층 해석 + Cu/Au + BEI 4분면."
whenToUse:
  - "macro"
  - "assets"
  - "자산"
  - "5대 자산 심층 해석 + Cu/Au + BEI 4분면"
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
  - "dartlab://skills/engines.macro.assets"
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
  - 기준일 / source 없는 매크로 숫자 인용 금지.
  - 기업 재무 분석을 macro 로 대체하지 않는다.
  - macro 결과를 analysis 내부 계산처럼 섞지 않는다.
  - 5 대 자산 (주식·채권·원자재·통화·부동산) 분류 미명시 답변 금지.
  - Cu/Au 비율 단일값으로 *경기 사이클* 단정 금지.
failureModes:
  - 5 대 자산의 시장 (KR vs US) 단위 혼용
  - Cu/Au 비율의 cycle phase 별 의미 변화 무시
  - BEI (breakeven inflation) 4 분면 (성장 vs 인플레) 단순 인과
  - 자산 간 상관관계 동결 가정
examples:
  - 5 대 자산 동향
  - Cu/Au 비율 cycle 분면
  - BEI 4 분면 (성장·인플레)
  - 자산 상관관계 변동
linkedSkills:
  - engines.macro
  - engines.macro.summary
  - engines.macro.sentiment
source:
  type: manual_skill
  format: markdown
lastUpdated: '2026-05-07'
---

## 엔진 역할

macro 엔진의 자산 축 응용 skill — 5대 자산 심층 해석 + Cu/Au + BEI 4분면. 5막 — 자산. SSOT 는 `_AXIS_REGISTRY` (`src/dartlab/macro/__init__.py`).

## 공개 호출 방식

```python
import dartlab

# 1. KR 시장
result = dartlab.macro("assets", market="KR")

# 2. US 시장
result = dartlab.macro("assets", market="US")
```

## 호출 동작

market 의 외부 SSOT (HF prebuild · ECOS · FRED) 를 읽어 자산 축 신호 / 레짐 / 한계를 산출한다. 결손 / 비교 불가 indicator 는 결과 dict 의 `flags` / null 로 표현하며 0 으로 채우지 않는다. Company 단위 재무 해석은 `engines.analysis` 로 분리. 자세한 동작은 base SKILL `engines.macro` + `_AXIS_REGISTRY['assets'].fn` 함수 docstring 참조.

## 대표 반환 형태

dict 또는 DataFrame 반환. 공통 키:

- `market`: 대상 시장 (KR / US)
- `latestAsOf` / `date`: 데이터 기준일
- `indicator` / `value` / `unit`: 핵심 지표
- `signal` / `regime` / `score`: 축 고유 판정
- `source` / `basis`: 데이터 출처 + 근거
- `assumptions` / `flags`: 가정 · 결손 / 이상 신호

전체 키는 base SKILL `engines.macro` 표 + `_AXIS_REGISTRY['assets'].fn` 함수 docstring 으로 검산.

## 기본 실행 순서

1. market (KR / US), 기준일, 옵션 (scenario · overrides) 확정.
2. 위 공개 호출 그대로 실행.
3. `latestAsOf` · `indicator` · `flags` · `assumptions` 점검.
4. 숫자 claim 은 `valueRef` / `dateRef` / `executionRef` 에 묶음.
5. 다축 narrative 조립은 `engines.story`. 시장 macro vs 기업 재무 (analysis) 는 분리 유지.

## 기본 검증

이 skill 은 공개 실행 문서다. 본 axis 호출 방식, 반환 키, 오류 / 제한 동작이 변경되면 같은 변경에서 본 파일을 갱신한다. SSOT 는 `_AXIS_REGISTRY` (`src/dartlab/macro/__init__.py`) + 함수 docstring.
