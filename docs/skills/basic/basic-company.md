---
title: Company 기업 분석 엔진
skillId: basic.company
category: basic
---

# Company 기업 분석 엔진

DartLab `company` 엔진의 역할과 capability 묶음을 찾기 위한 generated basic engine skill.

## Metadata

- id: `basic.company`
- category: `basic`
- kind: `generated`
- status: `observed`
- Pyodide: `unknown`

## When To Use

- AI는 Company를 단일 종목 분석의 라우터로 보고 대상 식별, 사용 가능한 topic, 하위 엔진 선택을 정한다.
- **사람의 최상위 관문** — 종목 하나의 모든 엔진에 접근하는 파사드. / AI 역할: AI는 Company를 단일 종목 분석의 라우터로 보고 대상 식별, 사용 가능한 topic, 하위 엔진 선택을 정한다. "삼성전자 재무제표" -> c = Company("005930"); c.show("IS") "사업 개요 보여줘" -> c.show("businessOverview") "어떤 데이터 있어?" -> c.index 또는 c.topics "출처 추적" -> c.trac
- 재무제표 완전 분석 — 14축, 단일 종목 심층 (내부 구현). / AI 역할: AI는 analysis를 단일 기업 재무·가치·리스크 해석 엔진으로 보고 axis/subaxis와 필요한 재무 evidence를 선택한다. When: 특정 종목의 재무 심층 분석이 필요할 때. How: axis 로 분석 영역, sub 로 세부 축 지정. "14축 분석 뭐가 있어?" → c.analysis() (가이드 반환) "수익구조 분석해줘" → c.analysis("finan
- LLM에게 이 기업에 대해 질문. / "영업이익률 분석해줘" → c.ask("영업이익률 추세는?") "AI한테 질문하고 싶어" → c.ask("질문") "스트리밍으로 답변받기" → c.ask("질문", stream=True)
- 감사 리스크 종합 분석. / "감사의견 확인" → c.audit() "감사인 바뀌었어?" → c.audit()["auditorChanges"] "계속기업 의문은?" → c.audit()["goingConcern"]
- DART 종목코드(6자) 또는 한글 회사명이면 처리 가능.
- 주주환원 분석 (배당, 자사주, 총환원율). / "배당 정보" → c.capital() 또는 c.show("dividend") "주주환원율은?" → c.capital() "전체 상장사 배당 비교" → c.capital("all")
- 6막 인과 가중치 — 수익구조→수익성→현금흐름→자금조달→자산배치→가치평가 amplify/dampen/neutral. / "인과 체인" → c.causalWeights() "어느 막이 약해" → 결과의 direction='dampen' 필터

## Capability Refs

- `Company`
- `Company.analysis`
- `Company.ask`
- `Company.audit`
- `Company.canHandle`
- `Company.capital`
- `Company.causalWeights`
- `Company.codeName`
- `Company.contextSlices`
- `Company.credit`
- `Company.currency`
- `Company.debt`
- `Company.diff`
- `Company.disclosure`
- `Company.facts`
- `Company.filings`
- `Company.fiscalYearEnd`
- `Company.gather`
- `Company.governance`
- `Company.index`
- `Company.industry`
- `Company.keywordTrend`
- `Company.listing`
- `Company.liveFilings`
- `Company.macro`
- `Company.market`
- `Company.narrativeDiff`
- `Company.network`
- `Company.news`
- `Company.priority`
- `Company.quant`
- `Company.rank`
- `Company.rawDocs`
- `Company.rawFinance`
- `Company.rawReport`
- `Company.readFiling`
- `Company.resolve`
- `Company.retrievalBlocks`
- `Company.search`
- `Company.sections`
- `Company.sector`
- `Company.sectorParams`
- `Company.select`
- `Company.show`
- `Company.sources`
- `Company.status`
- `Company.story`
- `Company.storyTree`
- `Company.table`
- `Company.topics`
- `Company.topicSummaries`
- `Company.trace`
- `Company.update`
- `Company.validateStory`
- `Company.valuationImpact`
- `Company.view`
- `Company.watch`
- `Company.workforce`

## Required Evidence

- target
- metric
- period
- value

## Expected Outputs

- engine AI role
- engine capability map
- capability-backed evidence refs

## Runtime Compatibility

| runtime | status | notes |
|---|---:|---|
| `server` | `supported` |  |
| `localPython` | `supported` |  |
| `mcp` | `supported` |  |
| `webAi` | `limited` | 실제 실행 가능 여부는 연결된 capability와 dataset skill을 함께 확인한다. |
| `pyodide` | `unknown` | 엔진 지도 자체는 조회 가능하다. 실행 가능 여부는 조합되는 skill과 capability별 runtimeCompatibility를 따른다. |

## Procedure

- AI 역할: AI는 Company를 단일 종목 분석의 라우터로 보고 대상 식별, 사용 가능한 topic, 하위 엔진 선택을 정한다.
- 이 skill은 엔진 능력 지도다. API 상세는 capabilityRefs의 docstring/generated capability에서 확인한다.
- 필요 입력, 반환 형태, 단위, 실제 반환 키를 이 skill에 중복하지 않는다.
- 분석 중 생성한 숫자·날짜·표·한계는 ref로 남겨 최종 답변 검산에 연결한다.

## Forbidden

- API parameters/returns/unit/actual return keys를 SkillSpec에 중복하지 않는다.
- workbench tool 사용법을 basic engine skill에 넣지 않는다.
