---
id: "engines.quant.entry"
title: "Quant - 진입진단"
kind: curated
scope: builtin
status: observed
category: engines
purpose: "quant 엔진의 진입진단 축 응용 — 현재 시점 진입/청산/스톱 진단 (백테스트 안 돌림)."
whenToUse:
  - "quant"
  - "entry"
  - "진입진단"
  - "현재 시점 진입/청산/스톱 진단 (백테스트 안 돌림)"
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
  - "dartlab://skills/engines.quant.entry"
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
  - "진입진단 결과를 백테스트 검증으로 오인 금지 — 본 axis 는 실시간 진단만."
  - "스톱 / 청산 가격을 단일 룰만으로 단정 금지 — 변동성 / 리스크 한도 동반."
failureModes:
  - "현재 시점 진단 결과의 후행 검증 (OOS) 부재"
  - "진입 / 청산 룰의 lookback 윈도우 (20D / 60D) 의존성"
  - "스톱 폭 (ATR / 고정 %) 기준 차이"
  - "거래비용 / 슬리피지 미반영"
  - "단일 종목 진단을 포트폴리오 결정으로 단순 확장"
examples:
  - "삼성전자 현 시점 진입 진단"
  - "스톱 가격 + 청산 가격 진단"
  - "ATR 기반 스톱 폭 계산"
  - "진입 진단 + 백테스트 후속"
linkedSkills:
  - engines.quant
  - engines.quant.signals
  - engines.quant.signalReview
  - engines.quant.backtest
source:
  type: manual_skill
  format: markdown
lastUpdated: '2026-05-07'
---

## 엔진 역할

quant 엔진의 진입진단 축 응용 skill — 현재 시점 진입/청산/스톱 진단 (백테스트 안 돌림). strategy 그룹. SSOT 는 `_AXIS_REGISTRY` (`src/dartlab/quant/__init__.py`).

## 공개 호출 방식

```python
import dartlab

# 1. 문자열 호출
result = dartlab.quant("entry", "005930")

# 2. accessor 호출 (동등)
result = dartlab.quant.entry("005930")
```

## 호출 동작

종목 005930 의 가격 · 재무 · 시계열 snapshot 을 읽어 진입진단 축 계산을 수행한다. 현재 시점 진입/청산/스톱 진단 (백테스트 안 돌림). 결손 / 비교 불가 케이스는 결과 dict 또는 DataFrame 의 `flags` / null 로 표현하며 0 으로 채우지 않는다. 자세한 동작은 base SKILL `engines.quant` + `_AXIS_REGISTRY['entry'].fn` 함수 docstring 참조.

## 대표 반환 형태

strategy 그룹 표준에 따른 dict 또는 DataFrame 반환. 공통 키:

- `stockCode` / `corpName`: 대상 종목 (해당 시)
- `latestAsOf` / `priceDate`: 데이터 기준일
- 축 고유 metric / score / verdict / rank column (정확한 spec 은 `_AXIS_REGISTRY['entry'].fn` 함수 docstring 검산)
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
