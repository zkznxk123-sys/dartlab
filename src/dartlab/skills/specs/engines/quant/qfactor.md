---
id: "engines.quant.qfactor"
title: "Quant - q-factor"
kind: curated
scope: builtin
status: observed
category: engines
purpose: "quant 엔진의 q-factor 축 응용 — Hou-Xue-Zhang 2015 — ROE + (−assetGrowth) composite, 수익성×보수투자."
whenToUse:
  - "quant"
  - "qfactor"
  - "q-factor"
  - "Hou-Xue-Zhang 2015 — ROE + (−assetGrowth) composite, 수익성×보수투자"
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
  - "dartlab://skills/engines.quant.qfactor"
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
  - "Hou-Xue-Zhang q-factor 미국 표본 결과를 KR 시장 동일 가정으로 인용 금지."
  - "ROE + (-assetGrowth) 합성 가중치 명시 없이 결과 비교 금지."
failureModes:
  - "ROE 의 분모 (평균자본 vs 기말자본) 차이로 점수 변동"
  - "assetGrowth 정의 (총자산 vs 영업자산) 모호"
  - "q-factor 의 KR 시장 reproducibility 차이"
  - "합성 가중치 (50:50) 임의 선택"
  - "산업별 정상 ROE / assetGrowth 분포 차이 무시"
examples:
  - "q-factor 합성 랭킹 상위"
  - "ROE + (-assetGrowth) 결합"
  - "산업별 q-factor 분포"
  - "q-factor + value 결합"
linkedSkills:
  - engines.quant
  - engines.quant.factor
  - engines.quant.quality
  - engines.quant.style
source:
  type: manual_skill
  format: markdown
lastUpdated: '2026-05-07'
---

## 엔진 역할

quant 엔진의 q-factor 축 응용 skill — Hou-Xue-Zhang 2015 — ROE + (−assetGrowth) composite, 수익성×보수투자. fundamental 그룹. SSOT 는 `_AXIS_REGISTRY` (`src/dartlab/quant/__init__.py`).

## 공개 호출 방식

```python
import dartlab

# 1. 문자열 호출 (횡단면 / 시장 레벨 — 종목 불필요)
result = dartlab.quant("qfactor")

# 2. accessor 호출 (동등)
result = dartlab.quant.qfactor()
```

## 호출 동작

전종목 universe 의 가격 · 재무 · 시계열 snapshot 을 읽어 q-factor 축 계산을 수행한다. Hou-Xue-Zhang 2015 — ROE + (−assetGrowth) composite, 수익성×보수투자. 결손 / 비교 불가 케이스는 결과 dict 또는 DataFrame 의 `flags` / null 로 표현하며 0 으로 채우지 않는다. 자세한 동작은 base SKILL `engines.quant` + `_AXIS_REGISTRY['qfactor'].fn` 함수 docstring 참조.

## 대표 반환 형태

fundamental 그룹 표준에 따른 dict 또는 DataFrame 반환. 공통 키:

- `stockCode` / `corpName`: 대상 종목 (해당 시)
- `latestAsOf` / `priceDate`: 데이터 기준일
- 축 고유 metric / score / verdict / rank column (정확한 spec 은 `_AXIS_REGISTRY['qfactor'].fn` 함수 docstring 검산)
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
