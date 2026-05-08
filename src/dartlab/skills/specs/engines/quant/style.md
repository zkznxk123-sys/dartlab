---
id: "engines.quant.style"
title: "Quant - 스타일"
kind: curated
scope: builtin
status: observed
category: engines
purpose: "quant 엔진의 스타일 축 응용 — 8 검증된 스타일 프리셋 일괄/단일 백테스트 (시총 의존 0)."
whenToUse:
  - "quant"
  - "style"
  - "스타일"
  - "8 검증된 스타일 프리셋 일괄/단일 백테스트 (시총 의존 0)"
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
  - "dartlab://skills/engines.quant.style"
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
  - "8 검증된 스타일 프리셋 결과를 절대 점수로 단정 금지 — KR 시장 reproducibility 차이 고려."
  - "스타일 (가치 / 모멘텀 / 퀄리티 / 저변동) 명시 없이 단일 결과 인용 금지."
failureModes:
  - "스타일 정의 (Fama-French vs MSCI) 차이"
  - "리밸런싱 빈도 (월 / 분기) 별 결과 변동"
  - "스타일 간 상관 (가치-모멘텀) 변화 무시"
  - "백테스트 기간 (2010s vs 2020s) 의 스타일 효과 차이"
  - "거래비용 / 슬리피지 미반영"
examples:
  - "8 스타일 프리셋 일괄 백테스트"
  - "단일 스타일 (가치) 백테스트"
  - "스타일 + size 결합"
  - "스타일 결과 + 매크로 cycle 결합"
linkedSkills:
  - engines.quant
  - engines.quant.factor
  - engines.quant.value
  - engines.quant.momentum
  - engines.quant.quality
source:
  type: manual_skill
  format: markdown
lastUpdated: '2026-05-07'
---

## 엔진 역할

quant 엔진의 스타일 축 응용 skill — 8 검증된 스타일 프리셋 일괄/단일 백테스트 (시총 의존 0). strategy 그룹. SSOT 는 `_AXIS_REGISTRY` (`src/dartlab/quant/__init__.py`).

## 공개 호출 방식

```python
import dartlab

# 1. 문자열 호출 (횡단면 / 시장 레벨 — 종목 불필요)
result = dartlab.quant("style")

# 2. accessor 호출 (동등)
result = dartlab.quant.style()
```

## 호출 동작

전종목 universe 의 가격 · 재무 · 시계열 snapshot 을 읽어 스타일 축 계산을 수행한다. 8 검증된 스타일 프리셋 일괄/단일 백테스트 (시총 의존 0). 결손 / 비교 불가 케이스는 결과 dict 또는 DataFrame 의 `flags` / null 로 표현하며 0 으로 채우지 않는다. 자세한 동작은 base SKILL `engines.quant` + `_AXIS_REGISTRY['style'].fn` 함수 docstring 참조.

## 대표 반환 형태

strategy 그룹 표준에 따른 dict 또는 DataFrame 반환. 공통 키:

- `stockCode` / `corpName`: 대상 종목 (해당 시)
- `latestAsOf` / `priceDate`: 데이터 기준일
- 축 고유 metric / score / verdict / rank column (정확한 spec 은 `_AXIS_REGISTRY['style'].fn` 함수 docstring 검산)
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
