---
id: "engines.analysis.revenueStructure"
title: "Analysis - 수익구조"
kind: curated
scope: builtin
status: observed
category: engines
purpose: "analysis 엔진의 수익구조 축 응용 — 이 회사는 무엇으로 돈을 버는가."
whenToUse:
  - "analysis"
  - "수익구조"
  - "이 회사는 무엇으로 돈을 버는가"
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
  - "dartlab://skills/engines.analysis.revenueStructure"
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
  - 사업부별 / 지역별 / 제품별 매출 분리 미명시 답변 금지.
  - 외화 매출 비중 무시 금지 — 환율 변동 영향 별도 표기.
failureModes:
  - 사업부 segment 정의 변경 (회사 재편) 시 시계열 단절 미반영
  - 지역별 매출 분리에서 *수출* vs *해외 자회사* 차이 무시
  - 제품 mix 변화 (신제품 출시) 영향을 가격 변동으로 오해
  - 일회성 대형 계약 (M&A 인수 후 매출 통합) 영향 미분리
  - 외화 매출 환율 영향 (환산 vs 거래) 미명시
examples:
  - 삼성전자 사업부별 매출
  - 지역별 매출 (수출 비중)
  - 제품 mix 변화 (반도체 vs 모바일 vs 가전)
  - 환율 영향 분리
  - 신규 사업 매출 비중 추세
linkedSkills:
  - engines.analysis.revenueForecast
  - engines.analysis.growth
  - engines.analysis.macroSensitivity
source:
  type: manual_skill
  format: markdown
lastUpdated: '2026-05-07'
---

## 엔진 역할

analysis 엔진의 수익구조 축 응용 skill — 이 회사는 무엇으로 돈을 버는가. SSOT 는 `_AXIS_REGISTRY` (`src/dartlab/analysis/financial/__init__.py`).

## 공개 호출 방식

```python
import dartlab

c = dartlab.Company("005930")

# 1. 가이드 확인 (선택)
c.analysis()

# 2. 실제 axis 실행
result = c.analysis("financial", "수익구조")

# 3. 모듈 함수형 (대안)
result = dartlab.analysis("financial", "수익구조", company=c)
```

## 호출 동작

Company 의 finance/disclosure/market snapshot 을 읽어 수익구조 축 계산 항목을 산출한다. 결손 값은 0 으로 채우지 않고 `flags`, `assumptions`, `dataAsOf`, 빈 history, null 로 표현한다. 자세한 동작은 base SKILL `engines.analysis` 의 `## 호출 동작` 참조.

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
