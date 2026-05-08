---
id: "engines.analysis.investmentEfficiency"
title: "Analysis - 투자효율"
kind: curated
scope: builtin
status: observed
category: engines
purpose: "analysis 엔진의 투자효율 축 응용 — 투자가 가치를 만드는가."
whenToUse:
  - "analysis"
  - "투자효율"
  - "투자가 가치를 만드는가"
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
  - "dartlab://skills/engines.analysis.investmentEfficiency"
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
  - ROIC 분모 (투자자본) 정의 (영업자산 vs 순영업자산 vs IC) 미명시 금지.
  - WACC 가정 ref 없이 ROIC - WACC 스프레드 단정 금지.
failureModes:
  - ROIC 분모 정의 차이 (영업자산 vs 순영업자산) 미명시
  - NOPAT 계산 시 세율 (실효세율 vs 명목세율) 미명시
  - 일회성 자산 손상 (impairment) 영향으로 ROIC 일시 왜곡
  - 신생 회사 (capex 미흡수) 의 ROIC 음수를 단정으로 오해
  - WACC 추정 베타 기간 (3년/5년) 미명시
  - 영업권 포함/제외 (asset 분모) 회사간 차이 무시
examples:
  - 삼성전자 ROIC vs WACC 스프레드
  - 5 년 ROIC 추세
  - 산업 평균 ROIC 대비
  - 영업권 포함 vs 제외 비교
  - capex 사이클과 ROIC 변동
linkedSkills:
  - engines.analysis.profitability
  - engines.analysis.capitalAllocation
  - engines.analysis.valuation
  - engines.quant.damodaranValuation
source:
  type: manual_skill
  format: markdown
lastUpdated: '2026-05-07'
---

## 엔진 역할

analysis 엔진의 투자효율 축 응용 skill — 투자가 가치를 만드는가. SSOT 는 `_AXIS_REGISTRY` (`src/dartlab/analysis/financial/__init__.py`).

## 공개 호출 방식

```python
import dartlab

c = dartlab.Company("005930")

# 1. 가이드 확인 (선택)
c.analysis()

# 2. 실제 axis 실행
result = c.analysis("financial", "투자효율")

# 3. 모듈 함수형 (대안)
result = dartlab.analysis("financial", "투자효율", company=c)
```

## 호출 동작

Company 의 finance/disclosure/market snapshot 을 읽어 투자효율 축 계산 항목을 산출한다. 결손 값은 0 으로 채우지 않고 `flags`, `assumptions`, `dataAsOf`, 빈 history, null 로 표현한다. 자세한 동작은 base SKILL `engines.analysis` 의 `## 호출 동작` 참조.

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
