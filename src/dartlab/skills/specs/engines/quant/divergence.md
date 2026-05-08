---
id: "engines.quant.divergence"
title: "Quant - 괴리"
kind: curated
scope: builtin
status: observed
category: engines
purpose: "quant 엔진의 괴리 축 응용 — 재무-기술적 괴리 진단."
whenToUse:
  - "quant"
  - "divergence"
  - "괴리"
  - "재무-기술적 괴리 진단"
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
  - "dartlab://skills/engines.quant.divergence"
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
  - "재무 vs 가격 괴리 한 신호로 매수 / 매도 단정 금지 — 산업 / 매크로 환경 동반."
  - "괴리 정도 (mean reversion) 와 시장 효율성 가정 명시 없이 인용 금지."
failureModes:
  - "재무 (분기 / 연간) 와 가격 (일별) 데이터 빈도 차이"
  - "괴리 신호 발생 시점과 mean reversion 시점 (3 개월~5 년) 차이"
  - "산업별 정상 P/B 또는 P/E 분포 차이 무시"
  - "자본구조 변경 (자사주 매입 / 증자) 영향 미반영"
  - "장기 구조적 괴리 (가치함정) vs 단기 변동 혼동"
examples:
  - "삼성전자 재무 vs 가격 괴리"
  - "P/B 와 ROE 의 mean reversion 추적"
  - "EPS 추세 vs 주가 추세 분리"
  - "괴리 신호 + 산업 환경 결합"
linkedSkills:
  - engines.quant
  - engines.analysis.valuation
  - engines.quant.signalReview
  - engines.quant.value
source:
  type: manual_skill
  format: markdown
lastUpdated: '2026-05-07'
---

## 엔진 역할

quant 엔진의 괴리 축 응용 skill — 재무-기술적 괴리 진단. fundamental 그룹. SSOT 는 `_AXIS_REGISTRY` (`src/dartlab/quant/__init__.py`).

## 공개 호출 방식

```python
import dartlab

# 1. 문자열 호출
result = dartlab.quant("divergence", "005930")

# 2. accessor 호출 (동등)
result = dartlab.quant.divergence("005930")
```

## 호출 동작

종목 005930 의 가격 · 재무 · 시계열 snapshot 을 읽어 괴리 축 계산을 수행한다. 재무-기술적 괴리 진단. 결손 / 비교 불가 케이스는 결과 dict 또는 DataFrame 의 `flags` / null 로 표현하며 0 으로 채우지 않는다. 자세한 동작은 base SKILL `engines.quant` + `_AXIS_REGISTRY['divergence'].fn` 함수 docstring 참조.

## 대표 반환 형태

fundamental 그룹 표준에 따른 dict 또는 DataFrame 반환. 공통 키:

- `stockCode` / `corpName`: 대상 종목 (해당 시)
- `latestAsOf` / `priceDate`: 데이터 기준일
- 축 고유 metric / score / verdict / rank column (정확한 spec 은 `_AXIS_REGISTRY['divergence'].fn` 함수 docstring 검산)
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
