---
id: "engines.analysis.capitalAllocation"
title: "Analysis - 자본배분"
kind: curated
scope: builtin
status: observed
category: engines
purpose: "analysis 엔진의 자본배분 축 응용 — 번 돈을 어디에 쓰는가."
whenToUse:
  - "analysis"
  - "자본배분"
  - "번 돈을 어디에 쓰는가"
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
  - "dartlab://skills/engines.analysis.capitalAllocation"
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
  - capex / 배당 / 자사주 / M&A 분류 미명시 답변 금지.
  - 자사주 매입과 자사주 소각 동치 처리 금지 — 소각만 EPS 영구 제거.
failureModes:
  - capex 강도 (capex/매출) 의 산업별 차이 무시 (제조 高 / 서비스 低)
  - 일회성 M&A 지출을 정기 capex 로 분류 — 별도 표시 권장
  - 자사주 *매입* (treasury) 과 *소각* (cancel) 영향 차이 무시
  - 배당성향 (payout ratio) 의 분모를 EPS vs FCF 혼용
  - 인수합병 영업권 발생 후 손상 (impairment) 위험 미언급
examples:
  - 삼성전자 자본배분 4 분류
  - capex / 배당 / 자사주 / M&A 비중
  - 배당성향 추세
  - 자사주 매입 vs 소각 영향
  - capex 사이클과 FCF
linkedSkills:
  - engines.analysis.cashflow
  - engines.analysis.investmentEfficiency
  - recipes.dividend.capitalReturn
  - engines.scan.capital
source:
  type: manual_skill
  format: markdown
lastUpdated: '2026-05-07'
---

## 엔진 역할

analysis 엔진의 자본배분 축 응용 skill — 번 돈을 어디에 쓰는가. SSOT 는 `_AXIS_REGISTRY` (`src/dartlab/analysis/financial/__init__.py`).

## 공개 호출 방식

```python
import dartlab

c = dartlab.Company("005930")

# 1. 가이드 확인 (선택)
c.analysis()

# 2. 실제 axis 실행
result = c.analysis("financial", "자본배분")

# 3. 모듈 함수형 (대안)
result = dartlab.analysis("financial", "자본배분", company=c)
```

## 호출 동작

Company 의 finance/disclosure/market snapshot 을 읽어 자본배분 축 계산 항목을 산출한다. 결손 값은 0 으로 채우지 않고 `flags`, `assumptions`, `dataAsOf`, 빈 history, null 로 표현한다. 자세한 동작은 base SKILL `engines.analysis` 의 `## 호출 동작` 참조.

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
