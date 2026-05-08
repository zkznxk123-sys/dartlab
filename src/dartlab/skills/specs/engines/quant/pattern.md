---
id: "engines.quant.pattern"
title: "Quant - 패턴"
kind: curated
scope: builtin
status: observed
category: engines
purpose: "quant 엔진의 패턴 축 응용 — 캔들스틱 10종 + zigzag 기반 지지/저항."
whenToUse:
  - "quant"
  - "pattern"
  - "패턴"
  - "캔들스틱 10종 + zigzag 기반 지지/저항"
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
  - "dartlab://skills/engines.quant.pattern"
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
  - "캔들스틱 한 봉으로 추세 단정 금지 — 거래량 / 다음 봉 confirmation 필수."
  - "지지 / 저항선 자동 탐지 결과를 단언 금지 — zigzag 파라미터 의존."
failureModes:
  - "캔들스틱 패턴 (도지 / 망치 / 잉걸리프 등) 의 false positive 비율"
  - "zigzag depth 파라미터 (5% vs 10%) 별 지지 / 저항 상이"
  - "intraday vs daily vs weekly 시간 프레임별 의미 차이"
  - "거래량 동반 없는 패턴의 신뢰도 저하"
  - "사후 패턴 매칭 / 과적합"
examples:
  - "캔들 10 종 패턴 시계열"
  - "zigzag 지지 / 저항"
  - "캔들 + 거래량 결합"
  - "daily vs weekly 프레임 비교"
linkedSkills:
  - engines.quant
  - engines.quant.chartPatterns
  - engines.quant.indicators
  - engines.quant.signals
source:
  type: manual_skill
  format: markdown
lastUpdated: '2026-05-07'
---

## 엔진 역할

quant 엔진의 패턴 축 응용 skill — 캔들스틱 10종 + zigzag 기반 지지/저항. technical 그룹. SSOT 는 `_AXIS_REGISTRY` (`src/dartlab/quant/__init__.py`).

## 공개 호출 방식

```python
import dartlab

# 1. 문자열 호출
result = dartlab.quant("pattern", "005930")

# 2. accessor 호출 (동등)
result = dartlab.quant.pattern("005930")
```

## 호출 동작

종목 005930 의 가격 · 재무 · 시계열 snapshot 을 읽어 패턴 축 계산을 수행한다. 캔들스틱 10종 + zigzag 기반 지지/저항. 결손 / 비교 불가 케이스는 결과 dict 또는 DataFrame 의 `flags` / null 로 표현하며 0 으로 채우지 않는다. 자세한 동작은 base SKILL `engines.quant` + `_AXIS_REGISTRY['pattern'].fn` 함수 docstring 참조.

## 대표 반환 형태

technical 그룹 표준에 따른 dict 또는 DataFrame 반환. 공통 키:

- `stockCode` / `corpName`: 대상 종목 (해당 시)
- `latestAsOf` / `priceDate`: 데이터 기준일
- 축 고유 metric / score / verdict / rank column (정확한 spec 은 `_AXIS_REGISTRY['pattern'].fn` 함수 docstring 검산)
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
