---
id: engines.company
title: Company
kind: curated
scope: builtin
status: observed
category: engines
purpose: Company 엔진은 종목코드 하나를 target으로 고정하고 재무, 공시, 검색, 분석, 신용, 수집, 퀀트, 매크로, 스토리, 산업 연결을 제공하는 facade 실행 스킬이다. 트리거 — '회사 분석', '단일 기업', '005930', 'Company.show'.
whenToUse:
  - Company
  - company
  - 단일 기업 분석
  - show
  - disclosure
  - filings
  - analysis
  - credit
  - gather
  - quant
  - macro
  - story
inputs:
  - stockCode 또는 ticker
  - topic
  - period
  - axis
outputs:
  - Company 객체
  - topic DataFrame
  - 하위 엔진 결과
  - evidence refs
capabilityRefs:
  - Company
  - Company.show
  - Company.select
  - Company.trace
  - Company.analysis
  - Company.credit
  - Company.gather
  - Company.quant
  - Company.macro
  - Company.story
knowledgeRefs:
  - start.dartlabSkillOs
  - engines.analysis
  - engines.credit
  - engines.gather
  - engines.quant
  - engines.macro
  - engines.story
sourceRefs:
  - dartlab://skills/engines.company
requiredEvidence:
  - target
  - period
  - topic
  - tableRef
  - valueRef
  - dateRef
  - executionRef
expectedOutputs:
  - 대상 기업
  - 공개 호출
  - topic/axis
  - 반환 타입과 근거
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
failureModes:
  - 종목코드/market을 확정하지 않고 분석을 시작함
  - show topic과 analysis axis를 혼동함
  - 원자료 조회 결과를 분석 결론으로 바로 말함
forbidden:
  - target 없는 Company 작업을 완료 처리하지 않는다.
  - table/value/date ref 없이 숫자를 말하지 않는다.
  - 공개 메서드, 반환 형태, 하위 엔진 연결이 바뀌었는데 이 skill을 갱신하지 않은 상태로 완료 처리하지 않는다.
examples:
  - 삼성전자 재무제표 조회
  - 미국 기업 공시와 분석 연결
  - 단일 기업 story 생성
  - dartlab.Company 사용법
  - 005930 분석 시작
  - AAPL EDGAR 재무 분석
  - 단일 기업 sections 가로화
  - 기간 간 텍스트 변화 (diff) 추적
procedure:
  - dartlab.Company(code) 로 종목코드 또는 ticker 로 facade 생성.
  - c.sections 또는 c.topics 로 사용 가능한 topic 확인.
  - c.show(topic) 으로 단일 topic 본문 (source priority — finance > report > docs).
  - 깊이 분석은 c.analysis · c.credit · c.quant · c.macro · c.story 같은 하위 엔진.
  - 답변에 target · period · topic · tableRef · valueRef · dateRef · executionRef 묶음.
linkedSkills:
  - engines.company.sections
  - engines.analysis
  - engines.scan
  - engines.story
  - engines.credit
source:
  type: manual_skill
  format: markdown
lastUpdated: '2026-05-07'
---

## 엔진 역할

`Company`는 DartLab의 단일 기업 facade다. 사용자는 종목코드나 ticker로 `Company`를 만들고, 이 객체에서 원자료 조회, 공시 탐색, 분석, 신용, gather, quant, macro, story를 호출한다.

한국 DART 회사와 미국 EDGAR 회사 모두 같은 facade 패턴을 따른다. 세부 topic/컬럼은 시장과 provider별로 다를 수 있으므로 반환값의 source와 기준일을 확인한다.

## 공개 호출 방식

```python
import dartlab

c = dartlab.Company("005930")

raw = c.show("BS")
selected = c.select("매출액")
trace = c.trace("영업이익")

analysis = c.analysis("financial", "수익성")
credit = c.credit()
price = c.gather("price")
quant = c.quant("모멘텀")
macro = c.macro("사이클")                          # 시장 매크로 (사이클/위기/시나리오/유동성/심리)
sensitivity = c.analysis("macro", "매크로민감도")  # 기업 단위 매크로 민감도는 analysis 엔진
story = c.story()
industry = c.industry()
```

## 호출 동작

Company 생성 시 target과 market/provider를 확정한다. 이후 `show/select/trace`는 원자료 조회, `analysis/credit/quant/macro/story`는 하위 엔진 호출, `gather`는 보조 데이터 수집, `disclosure/liveFilings/readFiling`은 공시 접근을 담당한다.

무인자 또는 topic 누락 호출은 가능한 topic/axis 가이드를 반환할 수 있다. 데이터가 없으면 결손을 0으로 채우지 않고 빈 DataFrame, `None`, flags, 제한 메시지로 표현한다.

## 전체 축/메서드 목록

| method | 담당 | 대표 호출 |
| --- | --- | --- |
| search/listing/resolve/codeName/status | 기업 식별/목록 | `dartlab.Company.search("삼성전자")` |
| filings/disclosure/liveFilings/readFiling | 공시 목록/본문 | `c.disclosure()` |
| rawDocs/rawFinance/rawReport | raw parquet 접근 | `c.rawFinance()` |
| sections/show/select/trace/diff | 원자료 조회/추적/비교 | `c.show("BS")` |
| keywordTrend/news/watch | 텍스트/뉴스/감시 | `c.news()` |
| story/validateStory/storyTree/narrativeDiff | 보고서/스토리 | `c.story()` |
| analysis | 재무/가치/전망 분석 | `c.analysis("financial", "수익성")` |
| credit | 신용/부실위험 | `c.credit()` |
| gather | 외부/보조 데이터 | `c.gather("price")` |
| quant | 정량 분석 | `c.quant("모멘텀")` |
| macro | 시장 매크로 (사이클/위기/시나리오/유동성/심리, KR 자동) | `c.macro("사이클")` |
| table/topics/sources/index/facts | 탐색 메타 | `c.index()` |
| retrievalBlocks/contextSlices/ask | AI 컨텍스트/질의 | `c.ask("질문")` |
| sector/rank/audit/market/currency/fiscalYearEnd | 회사 메타/검증 | `c.market()` |
| network/governance/workforce/capital/debt | scan view 연결 | `c.governance()` |
| causalWeights/valuationImpact/industry/view | story/industry/view 연결 | `c.industry()` |

## 대표 반환 형태

Company 메서드는 topic별 DataFrame, dict/list, 하위 엔진 결과 객체, 또는 `None`을 반환한다.

```text
stockCode/ticker, companyName, market, period/date,
topic/axis, source, metric, value, unit,
tableRef, valueRef, dateRef, executionRef
```

`show/select/trace`는 원자료 기반 table/selection/lineage가 중심이고, `analysis/credit/quant/macro/story`는 각 엔진의 반환 계약을 따른다.

## evidence 기준

단일 기업 답변은 target, period, topic/axis, tableRef, valueRef, dateRef, executionRef를 남긴다. 공시나 뉴스는 filing id, URL/source, 접수일/게시일을 함께 확인한다.

## 기본 실행 순서

1. `dartlab.Company(code_or_ticker)`로 target을 고정한다.
2. 원자료 확인이면 `show/select/trace`, 심층 분석이면 하위 엔진 메서드를 고른다.
3. 반환값의 기준일, source, 결손/flags를 확인한다.
4. 숫자 claim은 valueRef/tableRef에 묶는다.
5. 여러 축을 조합하는 최종 서술은 `story`로 넘긴다.

## 기본 검증

스킬은 공개 실행 문서다. Company 공개 메서드, 하위 엔진 연결, 대표 반환 형태가 바뀌면 이 파일과 관련 응용 스킬을 같은 변경에서 갱신한다.
