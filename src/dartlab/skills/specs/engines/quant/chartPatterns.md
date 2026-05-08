---
id: "engines.quant.chartPatterns"
title: "Quant - 차트패턴"
kind: curated
scope: builtin
status: observed
category: engines
purpose: "quant 엔진의 차트패턴 축 응용 — 거시 차트 패턴 — W/M/H&S/삼중/원형 (자동 인식 + 목표가)."
whenToUse:
  - "quant"
  - "chartPatterns"
  - "차트패턴"
  - "거시 차트 패턴 — W/M/H&S/삼중/원형 (자동 인식 + 목표가)"
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
  - "dartlab://skills/engines.quant.chartPatterns"
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
  - "차트 패턴 인식 결과를 자동 매수 / 매도 신호로 단정 금지 — 거래량 / 시장 환경 동반 검토."
  - "목표가 (target price) 를 패턴만으로 단언 금지 — fundamental anchor 동반."
failureModes:
  - "패턴 인식 알고리즘의 false positive 비율 무시"
  - "거래량 부족 (illiquid) 종목의 패턴 신뢰도 저하"
  - "패턴 시점 (intraday vs daily vs weekly) 별 의미 차이"
  - "사후 패턴 매칭 (data snooping) 의 과적합"
  - "매크로 / 섹터 환경과 단일 차트 패턴의 인과 단순화"
examples:
  - "헤드앤숄더 패턴 자동 인식"
  - "이중바닥 (W) + 거래량 동반"
  - "삼각수렴 패턴 + breakout"
  - "원형 패턴 형성 + 시장 환경"
linkedSkills:
  - engines.quant
  - engines.quant.pattern
  - engines.quant.indicators
  - engines.quant.signals
source:
  type: manual_skill
  format: markdown
lastUpdated: '2026-05-07'
---

## 엔진 역할

quant 엔진의 차트패턴 축 응용 skill — 거시 차트 패턴 — W/M/H&S/삼중/원형 (자동 인식 + 목표가). technical 그룹. SSOT 는 `_AXIS_REGISTRY` (`src/dartlab/quant/__init__.py`).

## 공개 호출 방식

```python
import dartlab

# 1. 문자열 호출
result = dartlab.quant("chartPatterns", "005930")

# 2. accessor 호출 (동등)
result = dartlab.quant.chartPatterns("005930")
```

## 호출 동작

종목 005930 의 가격 · 재무 · 시계열 snapshot 을 읽어 차트패턴 축 계산을 수행한다. 거시 차트 패턴 — W/M/H&S/삼중/원형 (자동 인식 + 목표가). 결손 / 비교 불가 케이스는 결과 dict 또는 DataFrame 의 `flags` / null 로 표현하며 0 으로 채우지 않는다. 자세한 동작은 base SKILL `engines.quant` + `_AXIS_REGISTRY['chartPatterns'].fn` 함수 docstring 참조.

## 대표 반환 형태

technical 그룹 표준에 따른 dict 또는 DataFrame 반환. 공통 키:

- `stockCode` / `corpName`: 대상 종목 (해당 시)
- `latestAsOf` / `priceDate`: 데이터 기준일
- 축 고유 metric / score / verdict / rank column (정확한 spec 은 `_AXIS_REGISTRY['chartPatterns'].fn` 함수 docstring 검산)
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
