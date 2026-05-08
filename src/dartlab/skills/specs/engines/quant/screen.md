---
id: "engines.quant.screen"
title: "Quant - 스크린"
kind: curated
scope: builtin
status: observed
category: engines
purpose: "quant 엔진의 스크린 축 응용 — 팩터 스크리닝 프리셋 (가치/모멘텀/퀄리티/저변동)."
whenToUse:
  - "quant"
  - "screen"
  - "스크린"
  - "팩터 스크리닝 프리셋 (가치/모멘텀/퀄리티/저변동)"
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
  - "dartlab://skills/engines.quant.screen"
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
  - "스크리너 결과 상위 종목을 곧바로 매수 추천으로 제시 금지 — 정성 검토 + 분석 파이프라인 후속 필수."
  - "스타일 (가치 / 모멘텀 / 퀄리티 / 저변동) 명시 없이 단일 시장 평균 비교 금지."
failureModes:
  - "단일 팩터 (PER 만 / PBR 만) 스크리닝의 가치함정 (value trap)"
  - "외국 시장 발견된 팩터를 KR 시장에 그대로 적용"
  - "스크리닝 universe (전종목 vs KOSPI200) 차이로 결과 변동"
  - "팩터 정의 (사용자 가치 vs Fama-French) 차이 미명시"
  - "리밸런싱 주기와 turnover (회전율 / 거래비용) 무시"
examples:
  - "가치 팩터 스크리닝 (PBR + ROE 결합)"
  - "모멘텀 12-1 팩터 상위 50 종목"
  - "저변동성 (vol min) + 퀄리티 결합"
  - "스크리너 결과 + 정성 검토 권장"
linkedSkills:
  - engines.quant
  - engines.quant.factor
  - engines.scan.screen
  - engines.quant.value
  - engines.quant.quality
source:
  type: manual_skill
  format: markdown
lastUpdated: '2026-05-07'
---

## 엔진 역할

quant 엔진의 스크린 축 응용 skill — 팩터 스크리닝 프리셋 (가치/모멘텀/퀄리티/저변동). crossSection 그룹. SSOT 는 `_AXIS_REGISTRY` (`src/dartlab/quant/__init__.py`).

## 공개 호출 방식

```python
import dartlab

# 1. 문자열 호출 (횡단면 / 시장 레벨 — 종목 불필요)
result = dartlab.quant("screen")

# 2. accessor 호출 (동등)
result = dartlab.quant.screen()
```

## 호출 동작

전종목 universe 의 가격 · 재무 · 시계열 snapshot 을 읽어 스크린 축 계산을 수행한다. 팩터 스크리닝 프리셋 (가치/모멘텀/퀄리티/저변동). 결손 / 비교 불가 케이스는 결과 dict 또는 DataFrame 의 `flags` / null 로 표현하며 0 으로 채우지 않는다. 자세한 동작은 base SKILL `engines.quant` + `_AXIS_REGISTRY['screen'].fn` 함수 docstring 참조.

## 대표 반환 형태

crossSection 그룹 표준에 따른 dict 또는 DataFrame 반환. 공통 키:

- `stockCode` / `corpName`: 대상 종목 (해당 시)
- `latestAsOf` / `priceDate`: 데이터 기준일
- 축 고유 metric / score / verdict / rank column (정확한 spec 은 `_AXIS_REGISTRY['screen'].fn` 함수 docstring 검산)
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
