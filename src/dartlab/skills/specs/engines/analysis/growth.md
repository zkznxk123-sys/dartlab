---
id: "engines.analysis.growth"
title: "Analysis - 성장성"
kind: curated
scope: builtin
status: observed
category: engines
purpose: "analysis 엔진의 성장성 축 응용 — 이 회사는 얼마나 빨리 성장하는가."
whenToUse:
  - 성장성
  - 매출 성장
  - 영업이익 성장
  - YoY
  - CAGR
  - 분기별 증가율
  - 성장 패턴
inputs:
  - Company 또는 종목코드
  - 기준 기간 (분기·연)
outputs:
  - 축별 dict (revenueGrowth · profitGrowth · growthPattern)
  - YoY · CAGR 시계열
  - evidence refs
  - 한계와 가정
capabilityRefs:
  - "analysis"
  - "Company.analysis"
knowledgeRefs:
  - "engines.analysis"
  - "engines.company"
  - "engines.data.foundation"
sourceRefs:
  - "dartlab://skills/engines.analysis.growth"
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
  - 결손값 0 대체 금지 — 빈 분기는 skip + flag.
  - 단일 axis 결과로 투자 결론 단정 금지.
  - YoY 와 CAGR 정의 미명시 답변 금지 — 기준 기간 (3 년/5 년) + 시작 base 명시.
  - 사이클 회사 (반도체·조선·정유) 의 단일 분기 YoY 로 추세 단정 금지 — 4 분기 이동 평균 권장.
failureModes:
  - YoY 가 base effect (전년 동기 일회성 비용/매출) 로 왜곡됨을 미고려
  - CAGR 산정 시작 분기가 cycle peak/trough 인 경우 결과 왜곡
  - 한 분기 spike 를 구조적 성장으로 오해
  - 인수합병 (M&A) 영향 미분리 — 유기적 성장 vs 인수 성장 구분 필요
  - 외화 매출 회사 환율 변동 영향 미분리 — 원화 매출 vs USD 매출 분리
  - 신생 회사 (상장 2 년 이내) 에 5 년 CAGR 적용 시도
examples:
  - 삼성전자 성장성 분석
  - 매출 YoY 추세 (분기별)
  - 5 년 CAGR (매출 / 영업이익)
  - 유기적 성장 vs M&A 성장 분리
  - 사이클 peak/trough 영향 평가
  - 신생 회사 (2 년 미만) 성장 분석
linkedSkills:
  - engines.analysis.profitability
  - engines.analysis.revenueForecast
  - engines.analysis.predictionSignal
  - engines.scan.growth
source:
  type: manual_skill
  format: markdown
lastUpdated: '2026-05-07'
---

## 엔진 역할

analysis 엔진의 성장성 축 응용 skill — 이 회사는 얼마나 빨리 성장하는가. SSOT 는 `_AXIS_REGISTRY` (`src/dartlab/analysis/financial/__init__.py`).

## 공개 호출 방식

```python
import dartlab

c = dartlab.Company("005930")

# 1. 가이드 확인 (선택)
c.analysis()

# 2. 실제 axis 실행
result = c.analysis("financial", "성장성")

# 3. 모듈 함수형 (대안)
result = dartlab.analysis("financial", "성장성", company=c)
```

## 호출 동작

Company 의 finance/disclosure/market snapshot 을 읽어 성장성 축 계산 항목을 산출한다. 결손 값은 0 으로 채우지 않고 `flags`, `assumptions`, `dataAsOf`, 빈 history, null 로 표현한다. 자세한 동작은 base SKILL `engines.analysis` 의 `## 호출 동작` 참조.

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
