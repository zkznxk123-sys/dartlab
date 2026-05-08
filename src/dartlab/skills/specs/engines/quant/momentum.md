---
id: "engines.quant.momentum"
title: "Quant - 모멘텀"
kind: curated
scope: builtin
status: observed
category: engines
purpose: "quant 엔진의 모멘텀 축 응용 — 12-1개월 횡단면, 시계열 모멘텀, 52주 신고가 비율."
whenToUse:
  - "quant"
  - "momentum"
  - "모멘텀"
  - "12-1개월 횡단면, 시계열 모멘텀, 52주 신고가 비율"
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
  - "dartlab://skills/engines.quant.momentum"
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
  - 성과 보장 표현 금지.
  - 기간 / benchmark / 가정 명시 없이 수익률 인용 금지.
  - 정량 신호를 인과 분석 결론으로 제시 금지.
  - 단일 lookback 기간 (3개월 또는 6개월) 모멘텀만으로 *추세* 단정 금지 — 다중 기간 cross-check.
  - 거래량 약한 (ADTV 낮은) 종목의 모멘텀 신호 신뢰도 명시 없이 인용 금지.
failureModes:
  - 12-1 모멘텀 (academic) 과 단순 12 모멘텀 (산업) 혼동
  - 벤치마크 (KOSPI · 섹터) 비교 (상대 모멘텀) 누락 — 시장 전체 추세와 분리 필요
  - 사이클 회사의 cycle peak 모멘텀 = trough 시작 신호 가능성
  - 거래량 spike 동반 안 한 모멘텀의 false signal
  - 배당락 / 액면분할 영향 미보정
examples:
  - 삼성전자 12-1 모멘텀
  - 다중 기간 (3개월·6개월·12개월) 비교
  - 벤치마크 대비 상대 모멘텀
  - 거래량 spike 동반 모멘텀
  - 사이클 phase 별 모멘텀 해석
linkedSkills:
  - engines.quant.signalReview
  - engines.quant.regime
  - engines.quant.benchmark
  - engines.gather.price
source:
  type: manual_skill
  format: markdown
lastUpdated: '2026-05-07'
---

## 엔진 역할

quant 엔진의 모멘텀 축 응용 skill — 12-1개월 횡단면, 시계열 모멘텀, 52주 신고가 비율. technical 그룹. SSOT 는 `_AXIS_REGISTRY` (`src/dartlab/quant/__init__.py`).

## 공개 호출 방식

```python
import dartlab

# 1. 문자열 호출
result = dartlab.quant("momentum", "005930")

# 2. accessor 호출 (동등)
result = dartlab.quant.momentum("005930")
```

## 호출 동작

종목 005930 의 가격 · 재무 · 시계열 snapshot 을 읽어 모멘텀 축 계산을 수행한다. 12-1개월 횡단면, 시계열 모멘텀, 52주 신고가 비율. 결손 / 비교 불가 케이스는 결과 dict 또는 DataFrame 의 `flags` / null 로 표현하며 0 으로 채우지 않는다. 자세한 동작은 base SKILL `engines.quant` + `_AXIS_REGISTRY['momentum'].fn` 함수 docstring 참조.

## 대표 반환 형태

technical 그룹 표준에 따른 dict 또는 DataFrame 반환. 공통 키:

- `stockCode` / `corpName`: 대상 종목 (해당 시)
- `latestAsOf` / `priceDate`: 데이터 기준일
- 축 고유 metric / score / verdict / rank column (정확한 spec 은 `_AXIS_REGISTRY['momentum'].fn` 함수 docstring 검산)
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
