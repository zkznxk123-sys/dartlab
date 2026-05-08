---
id: "engines.quant.riskText"
title: "Quant - 리스크텍스트"
kind: curated
scope: builtin
status: observed
category: engines
purpose: "quant 엔진의 리스크텍스트 축 응용 — 리스크 팩터 출현/소멸 텍스트 델타."
whenToUse:
  - "quant"
  - "riskText"
  - "리스크텍스트"
  - "리스크 팩터 출현/소멸 텍스트 델타"
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
  - "dartlab://skills/engines.quant.riskText"
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
  - "리스크 팩터 텍스트 출현 / 소멸 한 신호로 가격 인과 단정 금지."
  - "텍스트 분석 한국어 NLP 모델 / 사전 명시 없이 점수 인용 금지."
failureModes:
  - "리스크 팩터 정의 (정형 vs 비정형) 모호"
  - "사업보고서 / 분기보고서 시점 갱신 차이"
  - "한국어 NLP 의 도메인 어휘 (재무) 정확도 한계"
  - "텍스트 길이 / 빈도 정규화 누락"
  - "리스크 팩터 출현이 회사 의도 (defensive disclosure) 인지 실제 위험인지 구분 한계"
examples:
  - "삼성전자 리스크 팩터 시계열"
  - "신규 리스크 출현 검출"
  - "기존 리스크 소멸 검출"
  - "텍스트 + 정량 지표 결합"
linkedSkills:
  - engines.quant
  - engines.quant.toneChange
  - engines.analysis.disclosureChange
  - engines.gather.news
source:
  type: manual_skill
  format: markdown
lastUpdated: '2026-05-07'
---

## 엔진 역할

quant 엔진의 리스크텍스트 축 응용 skill — 리스크 팩터 출현/소멸 텍스트 델타. text 그룹. SSOT 는 `_AXIS_REGISTRY` (`src/dartlab/quant/__init__.py`).

## 공개 호출 방식

```python
import dartlab

# 1. 문자열 호출
result = dartlab.quant("riskText", "005930")

# 2. accessor 호출 (동등)
result = dartlab.quant.riskText("005930")
```

## 호출 동작

종목 005930 의 가격 · 재무 · 시계열 snapshot 을 읽어 리스크텍스트 축 계산을 수행한다. 리스크 팩터 출현/소멸 텍스트 델타. 결손 / 비교 불가 케이스는 결과 dict 또는 DataFrame 의 `flags` / null 로 표현하며 0 으로 채우지 않는다. 자세한 동작은 base SKILL `engines.quant` + `_AXIS_REGISTRY['riskText'].fn` 함수 docstring 참조.

## 대표 반환 형태

text 그룹 표준에 따른 dict 또는 DataFrame 반환. 공통 키:

- `stockCode` / `corpName`: 대상 종목 (해당 시)
- `latestAsOf` / `priceDate`: 데이터 기준일
- 축 고유 metric / score / verdict / rank column (정확한 spec 은 `_AXIS_REGISTRY['riskText'].fn` 함수 docstring 검산)
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
