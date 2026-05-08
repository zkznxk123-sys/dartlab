---
id: "engines.analysis.scorecard"
title: "Analysis - 종합평가"
kind: curated
scope: builtin
status: observed
category: engines
purpose: "analysis 엔진의 종합평가 축 응용 — 재무 상태를 한마디로."
whenToUse:
  - "analysis"
  - "종합평가"
  - "재무 상태를 한마디로"
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
  - "dartlab://skills/engines.analysis.scorecard"
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
  - scorecard 5 영역 (수익성·안정성·성장성·효율성·현금흐름) 가중치 미명시 금지.
  - 등급 (A-F) 임계값을 산업 평균 미참조 적용 금지.
failureModes:
  - 5 영역 가중치를 동일 (20% × 5) 로 단정 — 산업·성장 단계별 가중치 다름
  - 등급 임계값 (A=top 20% / B=21-40% / ...) 의 산업별 차이 무시
  - 결손 영역 처리 — 빈 영역을 평균값으로 채우면 등급 왜곡
  - 일회성 손익으로 *수익성* 영역만 일시 등급 변동
  - 신생 회사 (5 영역 데이터 부족) scorecard 적용 무리
examples:
  - 삼성전자 scorecard A-F
  - 5 영역 등급 분포
  - 산업 평균 대비 등급
  - 분기별 scorecard 변동
  - 신생 회사 scorecard 한계
linkedSkills:
  - engines.analysis.profitability
  - engines.analysis.stability
  - engines.analysis.growth
  - engines.analysis.cashflow
  - engines.story
source:
  type: manual_skill
  format: markdown
lastUpdated: '2026-05-07'
---

## 엔진 역할

analysis 엔진의 종합평가 축 응용 skill — 재무 상태를 한마디로. SSOT 는 `_AXIS_REGISTRY` (`src/dartlab/analysis/financial/__init__.py`).

## 공개 호출 방식

```python
import dartlab

c = dartlab.Company("005930")

# 1. 가이드 확인 (선택)
c.analysis()

# 2. 실제 axis 실행
result = c.analysis("financial", "종합평가")

# 3. 모듈 함수형 (대안)
result = dartlab.analysis("financial", "종합평가", company=c)
```

## 호출 동작

Company 의 finance/disclosure/market snapshot 을 읽어 종합평가 축 계산 항목을 산출한다. 결손 값은 0 으로 채우지 않고 `flags`, `assumptions`, `dataAsOf`, 빈 history, null 로 표현한다. 자세한 동작은 base SKILL `engines.analysis` 의 `## 호출 동작` 참조.

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
