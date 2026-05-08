---
id: "engines.analysis.valuationBand"
title: "Analysis - 밸류에이션밴드"
kind: curated
scope: builtin
status: observed
category: engines
purpose: "analysis 엔진의 밸류에이션밴드 축 응용 — PER/PBR이 과거 대비 어디에 있는가."
whenToUse:
  - "analysis"
  - "밸류에이션밴드"
  - "PER/PBR이 과거 대비 어디에 있는가"
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
  - "dartlab://skills/engines.analysis.valuationBand"
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
  - 5y / 10y range 명시 없이 *밴드 상단/하단* 답변 금지.
  - 산업 평균 멀티플과 밴드 동일시 금지 — 같은 회사 historical 밴드.
failureModes:
  - 5 년 vs 10 년 range 차이 미명시 — 사이클 1 회 (5 년) vs 2 회 (10 년)
  - PER 음수 (적자 분기) 포함 시 range 왜곡 — 음수 분기 제외 표시
  - cycle peak 시점 PER 낮음 = *저평가* 오해 (cycle 회사)
  - 회계 기준 변경 (K-IFRS 도입) 후 멀티플 단절
  - 분기 vs 연 멀티플 혼용
examples:
  - 삼성전자 PER 5y 밴드
  - PER vs PBR 5y range
  - cycle peak/trough 위치
  - 산업 평균 멀티플과 historical 밴드 분리
  - 회계 기준 변경 후 밴드 단절
linkedSkills:
  - engines.analysis.valuation
  - engines.scan.valuation
  - engines.quant.value
source:
  type: manual_skill
  format: markdown
lastUpdated: '2026-05-07'
---

## 엔진 역할

analysis 엔진의 밸류에이션밴드 축 응용 skill — PER/PBR이 과거 대비 어디에 있는가. SSOT 는 `_AXIS_REGISTRY` (`src/dartlab/analysis/financial/__init__.py`).

## 공개 호출 방식

```python
import dartlab

c = dartlab.Company("005930")

# 1. 가이드 확인 (선택)
c.analysis()

# 2. 실제 axis 실행
result = c.analysis("macro", "밸류에이션밴드")

# 3. 모듈 함수형 (대안)
result = dartlab.analysis("macro", "밸류에이션밴드", company=c)
```

## 호출 동작

Company 의 finance/disclosure/market snapshot 을 읽어 밸류에이션밴드 축 계산 항목을 산출한다. 결손 값은 0 으로 채우지 않고 `flags`, `assumptions`, `dataAsOf`, 빈 history, null 로 표현한다. 자세한 동작은 base SKILL `engines.analysis` 의 `## 호출 동작` 참조.

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
