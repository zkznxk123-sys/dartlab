---
id: "engines.analysis.assetStructure"
title: "Analysis - 자산구조"
kind: curated
scope: builtin
status: observed
category: engines
purpose: "analysis 엔진의 자산구조 축 응용 — 조달한 돈으로 뭘 준비했는가."
whenToUse:
  - 자산구조
  - 자산 구성
  - 현금성 자산
  - 재고
  - 매출채권
  - 유형자산
  - 투자자산 비중
inputs:
  - Company 또는 종목코드
  - 기준 기간
outputs:
  - 축별 dict (assetMix · liquidAssets · operatingAssets)
  - evidence refs
  - 자산 회전 시그널
capabilityRefs:
  - "analysis"
  - "Company.analysis"
knowledgeRefs:
  - "engines.analysis"
  - "engines.company"
  - "engines.data.foundation"
sourceRefs:
  - "dartlab://skills/engines.analysis.assetStructure"
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
  - 산업별 정상 자산 비중 차이 무시 금지 (제조 유형자산 高 / IT 무형자산 高 / 금융 금융자산 高).
  - 별도 vs 연결 재무제표 혼용 금지 — scope 명시.
failureModes:
  - 산업별 자산 구성 차이 무시 — 제조사 (유형자산 40%+) vs IT (무형자산·현금) vs 금융 (대출채권)
  - 재고 자산 증가를 *판매 부진* 또는 *생산 확대* 둘 중 하나로 단정 — 재고/매출 비율 + 유형 (원재료/재공품/제품) 분리 필요
  - 매출채권 증가를 매출 성장 신호로 단정 — DSO 동시 확인
  - 무형자산 증가가 *영업권 (인수 후)* 인지 *개발비 자본화* 인지 구분
  - 일회성 자산 매각 (ICF +) 영향 미고려
examples:
  - 삼성전자 자산 구성 분석
  - 재고 + 매출채권 운전자본 추세
  - 유형자산 capex 강도
  - 무형자산 (영업권 vs 개발비) 분리
  - 산업 평균 대비 자산 회전
linkedSkills:
  - engines.analysis.cashflow
  - engines.analysis.efficiency
  - engines.analysis.investmentEfficiency
source:
  type: manual_skill
  format: markdown
lastUpdated: '2026-05-07'
---

## 엔진 역할

analysis 엔진의 자산구조 축 응용 skill — 조달한 돈으로 뭘 준비했는가. SSOT 는 `_AXIS_REGISTRY` (`src/dartlab/analysis/financial/__init__.py`).

## 공개 호출 방식

```python
import dartlab

c = dartlab.Company("005930")

# 1. 가이드 확인 (선택)
c.analysis()

# 2. 실제 axis 실행
result = c.analysis("financial", "자산구조")

# 3. 모듈 함수형 (대안)
result = dartlab.analysis("financial", "자산구조", company=c)
```

## 호출 동작

Company 의 finance/disclosure/market snapshot 을 읽어 자산구조 축 계산 항목을 산출한다. 결손 값은 0 으로 채우지 않고 `flags`, `assumptions`, `dataAsOf`, 빈 history, null 로 표현한다. 자세한 동작은 base SKILL `engines.analysis` 의 `## 호출 동작` 참조.

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
