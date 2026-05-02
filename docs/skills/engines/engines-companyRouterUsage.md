---
title: Company 엔진 라우터 사용 지도
skillId: engines.companyRouterUsage
category: engines
---

# Company 엔진 라우터 사용 지도

단일 종목 질문에서 Company를 대상 식별과 하위 엔진 선택 라우터로 쓰는 절차를 설명한다.

## Metadata

- id: `engines.companyRouterUsage`
- category: `engines`
- kind: `curated`
- status: `unverified`
- Pyodide: `limited`

## When To Use

- 종목 하나를 분석할 때 어떤 엔진부터 써야 하는지 모를 때
- 회사명, 종목코드, ticker를 Company 기준으로 정규화해야 할 때
- 사업/재무/공시/주가/신용/산업 근거를 한 종목에 묶어야 할 때

## Capability Refs

- `Company`
- `Company.index`
- `Company.show`
- `Company.trace`
- `Company.diff`
- `Company.analysis`
- `Company.credit`
- `Company.quant`
- `Company.story`
- `Company.industry`

## Dataset Refs

- dart.finance
- dart.docs
- edgar.filings

## Required Evidence

- target
- availableTopics
- source
- period
- table

## Expected Outputs

- target-normalized company context
- engine routing plan
- capability-backed evidence refs

## Runtime Compatibility

| runtime | status | notes |
|---|---:|---|
| `server` | `supported` |  |
| `localPython` | `supported` |  |
| `mcp` | `supported` |  |
| `webAi` | `limited` | Web AI는 연결된 dataset snapshot과 provider 범위에 따른다. |
| `pyodide` | `limited` | EDGAR live filing과 일부 네트워크 수집은 서버 경유가 필요할 수 있다. |

## Guide

## 가능한 분석

- Company는 종목 하나를 중심으로 공시, 재무, 분석, 신용, 주가, 산업 맥락을 묶는 라우터다.
- `index/topics`로 사용 가능한 evidence 표면을 먼저 확인하면 없는 데이터 추정이 줄어든다.
- `show/trace/diff`는 원문/표/기간 변화 확인, `analysis/credit/quant/industry/story`는 해석 엔진 연결에 쓴다.

## 절차

- `basic.company`와 `Company` capability에서 AI 역할과 provider 범위를 확인한다.
- 질문의 target을 회사명, 종목코드, ticker 중 하나로 정규화한다.
- `Company.index`, `Company.topics`, `Company.show` 계열 capability로 실제 가용 topic과 source를 확인한다.
- 질문 의도별 하위 엔진을 선택한다: 재무 원인 분석은 analysis, 상환능력은 credit, 가격 신호는 quant, 산업 맥락은 industry, 보고서 조합은 story.
- 최종 답변에는 target, period, source, 사용한 하위 엔진, 한계를 evidence ref로 남긴다.

## Forbidden

- Company capability의 API schema를 SkillSpec에 중복하지 않는다.
- target, period, source 없는 단일 종목 결론을 내지 않는다.
