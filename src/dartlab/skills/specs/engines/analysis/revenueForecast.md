---
id: "engines.analysis.revenueForecast"
title: "Analysis - 매출전망"
kind: curated
scope: builtin
status: observed
category: engines
purpose: "analysis 엔진의 매출전망 축 응용 — 이 회사의 매출은 어디로 가며 재무는 어떻게 변하는가."
whenToUse:
  - "analysis"
  - "매출전망"
  - "이 회사의 매출은 어디로 가며 재무는 어떻게 변하는가"
inputs:
  - "Company 또는 종목코드"
  - "기준 기간"
outputs:
  - "축별 dict"
  - "evidence refs"
  - "한계와 가정"
capabilityRefs:
  - "analysis"
  - "Company.analysis"
knowledgeRefs:
  - "engines.analysis"
  - "engines.company"
  - "engines.data.foundation"
sourceRefs:
  - "dartlab://skills/engines.analysis.revenueForecast"
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
  - 매출 전망의 가정 (수량 · 단가 · mix · 환율) 분리 미명시 금지.
  - 단일 시나리오 (best case 만) 답변 금지 — base / upside / downside 3 시나리오.
failureModes:
  - 컨센서스 평균을 그대로 인용 — 분포 (median vs mean) + 애널리스트 수 분리 필요
  - 가정 (수량 · 단가) 변경 시 매출 전망 민감도 미산출
  - 사이클 회사의 cycle peak 기준 forecast → trough 시 큰 빗나감
  - 신생 회사의 5 년 forecast — 표본 부족 한계 명시 필요
  - 외화 매출 환율 가정 미명시
examples:
  - 삼성전자 매출 전망 base/upside/downside
  - 가정 (수량/단가/환율) 민감도
  - 컨센서스 분포 + 애널리스트 수
  - 사이클 phase 별 forecast 한계
  - 신생 회사 forecast 한계 명시
linkedSkills:
  - engines.analysis.predictionSignal
  - engines.analysis.growth
  - engines.gather.revenueConsensus
  - engines.gather.consensus
source:
  type: manual_skill
  format: markdown
lastUpdated: '2026-05-07'
---

## 엔진 역할

analysis 엔진의 매출전망 축 응용 skill — 이 회사의 매출은 어디로 가며 재무는 어떻게 변하는가. SSOT 는 `_AXIS_REGISTRY` (`src/dartlab/analysis/financial/__init__.py`).

## 공개 호출 방식

```python
import dartlab

c = dartlab.Company("005930")

# 1. 가이드 확인 (선택)
c.analysis()

# 2. 실제 axis 실행
result = c.analysis("forecast", "매출전망")

# 3. 모듈 함수형 (대안)
result = dartlab.analysis("forecast", "매출전망", company=c)
```

## 호출 동작

Company 의 finance/disclosure/market snapshot 을 읽어 매출전망 축 계산 항목을 산출한다. 결손 값은 0 으로 채우지 않고 `flags`, `assumptions`, `dataAsOf`, 빈 history, null 로 표현한다. 자세한 동작은 base SKILL `engines.analysis` 의 `## 호출 동작` 참조.

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
