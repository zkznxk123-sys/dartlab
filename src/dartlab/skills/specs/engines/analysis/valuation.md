---
id: "engines.analysis.valuation"
title: "Analysis - 가치평가"
kind: curated
scope: builtin
status: observed
category: engines
purpose: "analysis 엔진의 가치평가 축 응용 — 이 회사의 적정 가치는 얼마인가."
whenToUse:
  - 가치평가
  - valuation
  - 적정가
  - 목표가
  - DCF
  - DDM
  - RIM
  - PER
  - PBR
  - PSR
  - 멀티플
  - 적정 시가총액
  - relative value
inputs:
  - Company 또는 종목코드
  - 기준 기간
  - 할인율 / 성장률 가정 (overrides)
outputs:
  - 축별 dict (valuationSummary · targetPrice · relativeValue · dcf · ddm · rim · sensitivity)
  - evidence refs
  - 가정 표 (할인율 · 성장률 · 베타 · 영구성장률)
  - 민감도 표
capabilityRefs:
  - "analysis"
  - "Company.analysis"
knowledgeRefs:
  - "engines.analysis"
  - "engines.company"
  - "engines.data.foundation"
sourceRefs:
  - "dartlab://skills/engines.analysis.valuation"
requiredEvidence:
  - "target"
  - "period"
  - "metric"
  - "tableRef"
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
  - 근거 없는 숫자를 만들지 않는다.
  - 결손값을 0 으로 채우지 않는다.
  - 단일 axis 결과를 최종 투자 결론으로 제시하지 않는다.
  - DCF 할인율·성장률·영구성장률 가정 ref 없이 적정가 단정 금지.
  - 산업별 멀티플 차이 무시 금지 (제조 PER 평균 vs 금융 PBR 평균 vs 바이오 PSR 평균).
  - 단일 멀티플 (PER) 만으로 적정가 결론 금지 — DCF + 멀티플 + RIM 교차 검증.
failureModes:
  - 가정 (할인율 · 성장률) ref 없이 DCF 결과 인용
  - peer 멀티플 비교 시 같은 산업 분기 미적용 (제조사 vs 금융사 PER 단순 비교)
  - 바이오/플랫폼 같은 적자 회사에 PER 적용 (PSR 또는 EV/Sales 권장)
  - 지주회사에 단일 회사 DCF 적용 (NAV 기반 SOTP 권장)
  - 영구성장률 g 가 명목 GDP 성장률 초과 (수학적으로 비현실적)
  - sensitivity 표 없이 단일 적정가 — 가정 한 변수 흔들림에 취약
examples:
  - 삼성전자 적정 가치 산출
  - DCF 가치평가 + 민감도
  - PER PBR 멀티플 비교
  - 산업 평균 PER 대비 위치
  - 신한지주 PBR 기반 평가 (금융사 — PER 아님)
  - 영구성장률 가정에 따른 적정가 변동
linkedSkills:
  - engines.quant.damodaranValuation
  - engines.analysis.valuationBand
  - engines.analysis.profitability
  - engines.analysis.growth
  - engines.scan.valuation
source:
  type: manual_skill
  format: markdown
lastUpdated: '2026-05-07'
---

## 엔진 역할

analysis 엔진의 가치평가 축 응용 skill — 이 회사의 적정 가치는 얼마인가. SSOT 는 `_AXIS_REGISTRY` (`src/dartlab/analysis/financial/__init__.py`).

## 공개 호출 방식

```python
import dartlab

c = dartlab.Company("005930")

# 1. 가이드 확인 (선택)
c.analysis()

# 2. 실제 axis 실행
result = c.analysis("valuation", "가치평가")

# 3. 모듈 함수형 (대안)
result = dartlab.analysis("valuation", "가치평가", company=c)
```

## 호출 동작

Company 의 finance/disclosure/market snapshot 을 읽어 가치평가 축 계산 항목을 산출한다. 결손 값은 0 으로 채우지 않고 `flags`, `assumptions`, `dataAsOf`, 빈 history, null 로 표현한다. 자세한 동작은 base SKILL `engines.analysis` 의 `## 호출 동작` 참조.

## 대표 반환 형태

dict 반환. 공통 키:

- `items`: 축별 계산 항목과 결과
- `history`: 기간별 시계열
- `displayHints`: 표/차트 표시 힌트
- `turningPoints`: 전환점 (해당 시)
- `dataAsOf`, `assumptions`, `flags`: 데이터 기준일, 가정, 결손/이상 신호
- `_summary`: 사람이 읽을 요약
- `tableRef` / `valueRef` / `dateRef` / `executionRef`: evidence 참조

전체 반환 키는 base SKILL `engines.analysis` 표 + `_analysisImpl` docstring 으로 검산.

## 기본 실행 순서

1. 대상, 기간, 원천 데이터 확정.
2. 위 공개 호출을 그대로 실행.
3. `dataAsOf`, 결손 값, `flags`, `assumptions` 점검.
4. 숫자 claim 은 `tableRef` / `valueRef` / `dateRef` / `executionRef` 에 묶음.
5. 다축 보고서 조립은 `engines.story` 또는 상위 recipe 가 담당.

## 기본 검증

이 skill 은 공개 실행 문서다. 본 axis 호출 방식, 대표 반환 키, 오류/제한 동작이 변경되면 같은 변경에서 본 파일을 갱신한다. SSOT 는 `_AXIS_REGISTRY` (`src/dartlab/analysis/financial/__init__.py`).
