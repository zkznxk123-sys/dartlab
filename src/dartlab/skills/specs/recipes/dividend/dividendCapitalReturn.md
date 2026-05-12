---
id: recipes.dividend.dividendCapitalReturn
title: 배당과 주주환원 분석
kind: recipe
scope: builtin
status: unverified
category: recipes
purpose: 배당, 자사주, 총환원율을 자본배분 + 현금흐름 + 수익성 축의 결합으로 점검하는 다단 응용.
whenToUse:
  - 배당 매력 분석
  - 주주환원 정책 점검
  - 자사주와 배당 지속 가능성
inputs:
  - 기업명 또는 종목코드
outputs:
  - capital return thesis
  - 배당/환원 표
  - 지속 가능성
capabilityRefs:
  - Company.analysis
  - Company.show
toolRefs:
  - search_reference
  - RunPython
  - finalize_answer
knowledgeRefs:
  - engines.analysis
  - engines.analysis.capitalAllocation
  - engines.analysis.cashflow
  - engines.analysis.profitability
linkedSkills:
  - engines.analysis.capitalAllocation
  - engines.analysis.cashflow
  - engines.analysis.profitability
recipeSteps:
  - skillId: engines.analysis.capitalAllocation
    note: 번 돈을 어디에 쓰는가 — 배당 / 자사주 / 재투자 비중 확인.
  - skillId: engines.analysis.cashflow
    note: OCF / FCF 가 환원 정책을 지속 가능하게 받쳐주는지.
  - skillId: engines.analysis.profitability
    note: 이익률과 ROE 가 환원 여력을 만들어내는지.
sourceRefs:
  - dartlab://skills/recipes.dividend.dividendCapitalReturn
requiredEvidence:
  - target
  - period
  - metric
  - table
expectedOutputs:
  - shareholder return thesis
  - 배당/자사주 근거
  - 지속 가능성 한계
visualGuidance:
  - 배당성향, 배당수익률, 총환원율 시계열 표가 있을 때만 chart를 만든다.
runtimeCompatibility:
  server:
    status: supported
  localPython:
    status: supported
  mcp:
    status: supported
  webAi:
    status: limited
  pyodide:
    status: limited
    dataSources:
      - HuggingFace dartlab-data dart/finance/{stockCode}.parquet
      - HuggingFace dartlab-data dart/report/{stockCode}.parquet
      - HuggingFace dartlab-data dart/scan/finance-lite.parquet
    requiredSetup:
      - 배당/자본 관련 Company snapshot 또는 scan prebuild를 확인한다.
    limitations:
      - 공시 당일 신규 주주환원 이벤트는 live filings가 가능한 서버 경로에서 보강한다.
failureModes:
  - 배당수익률만 보고 매력 단정 — payout ratio + FCF 커버리지 동반
  - 이익과 현금흐름 지속 가능성 확인 누락 — 분모를 EPS vs FCF 차이 명시
  - 일회성 자사주 매입을 반복 정책으로 단정 — 5 년 시계열로 추세 확인
  - 자사주 *매입* (treasury) vs *소각* (cancel) 차이 무시 — 소각만 EPS 영구 제거
  - 배당락 주가 영향 미반영 — adjusted vs raw 가격 명시
  - 외국인 보유 비중 변화에 따른 배당 압력 미고려
forbidden:
  - 근거 없는 배당 지속 가능성 단정 금지.
  - 주가 기준일 없는 배당수익률 판단 금지.
  - 배당성향 (payout ratio) 분모 (EPS vs FCF) 미명시 금지.
  - 자사주 매입 vs 소각 동치 처리 금지.
examples:
  - 삼성전자 주주환원 정책
  - 배당성향 + 배당수익률 + 자사주 환원율
  - 산업 평균 환원율 대비
  - 자사주 매입 vs 소각 영향
  - 5 년 환원 추세 + FCF 커버리지
linkedSkills:
  - engines.analysis.capitalAllocation
  - engines.analysis.cashflow
  - engines.analysis.profitability
  - engines.scan.capital
  - engines.scan.dividendTrend
source:
  type: manual_skill
  format: markdown
lastUpdated: '2026-05-07'
---

## 엔진 역할

본 skill 은 단일 axis 응용이 아니라 자본배분 + 현금흐름 + 수익성 세 축을 묶는 **recipe** 다. 각 axis 호출은 base SKILL `engines.analysis` 와 자식 응용 skill 에서 한다. 본 skill 은 묶음 절차와 판정 게이트만 제공한다.

## 연계 절차

1. engines.analysis.capitalAllocation — 자본배분 (배당 / 자사주 / 재투자 비중) 시계열 확인.
2. engines.analysis.cashflow — OCF / FCF 시계열로 환원 재원의 지속 가능성 검산.
3. engines.analysis.profitability — ROE / 이익률 시계열로 환원 여력의 원천 확인.

## 판정 게이트

- 배당성향 / 총환원율 만으로 결론 짓지 않는다. 위 3 축 결과가 모두 일관되어야 "지속 가능" claim 을 허용.
- OCF &lt; 배당총액인 기간이 있으면 그 자체를 evidence 로 남기고 "차입 의존" flag.
- 자사주 매입은 일회성 / 반복 정책 구분 — 최근 3~5 기간의 빈도 + 평균 규모를 함께 본다.

## 기본 검증

claim 은 기간·metric·값을 포함하며 각 claim 은 해당 axis 결과의 `tableRef` / `valueRef` / `dateRef` 에 직접 묶는다. 본 recipe 는 base SKILL 또는 자식 axis skill 의 호출 방식·반환 키가 변경되면 같은 변경에서 갱신한다.

## 공개 호출 방식

```python
import dartlab

c = dartlab.Company("005930")

capital = c.analysis("financial", "자본배분")
cashflow = c.analysis("financial", "현금흐름")
profitability = c.analysis("financial", "수익성")
dividend = c.show("dividend")

emit_result({
    "target": "005930",
    "capitalAllocation": capital,
    "cashflow": cashflow,
    "profitability": profitability,
    "dividend": dividend,
})
```

## 호출 동작

1. 자본배분에서 배당·자사주·재투자 비중을 확인한다.
2. 현금흐름에서 OCF / FCF 가 환원 재원을 받치는지 검산한다.
3. 수익성에서 ROE / margin 추세가 환원 여력과 일치하는지 본다.
4. `show("dividend")` raw 표로 DPS, payout, 기준일을 확인한다.
