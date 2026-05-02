---
title: Company capability view
skillId: capability:Company
category: capability
---

# Company capability view

공개 capability `Company`를 찾고 실행에 연결하기 위한 generated skill view.

## Metadata

- id: `capability:Company`
- category: `capability`
- kind: `generated`
- status: `observed`
- Pyodide: `unknown`

## When To Use

- **사람의 최상위 관문** — 종목 하나의 모든 엔진에 접근하는 파사드.
- AI 역할: AI는 Company를 단일 종목 분석의 라우터로 보고 대상 식별, 사용 가능한 topic, 하위 엔진 선택을 정한다. "삼성전자 재무제표" -> c = Company("005930"); c.show("IS") "사업 개요 보여줘" -> c.show("businessOverview") "어떤 데이터 있어?" -> c.index 또는 c.topics "출처 추적" -> c.trace("revenue") "기간 변화" -> c.diff() "종합평가" -> c.analysis("financial", "종합평가") "스토리 보고서" -> c.story() "Apple 분석" -> Company("AAPL") (자동 EDGAR 라우팅)

## Capability Refs

- `Company`

## Required Evidence

- sourceRef

## Expected Outputs

- capability-backed execution or limitation

## Runtime Compatibility

| runtime | status | notes |
|---|---:|---|
| `server` | `supported` |  |
| `localPython` | `supported` |  |
| `mcp` | `supported` |  |
| `webAi` | `limited` | 웹 AI는 Pyodide/HF snapshot 가능 범위에 따른다. |
| `pyodide` | `unknown` | Generated capability view는 API 사용법만 나타낸다.; Pyodide 가능 여부는 curated/user SkillSpec 또는 ops/pyodide.md를 확인한다. |

## Procedure

- capability ref의 공개 docstring/generated capability를 확인한다.
- 필요 입력과 반환 형태는 SkillSpec이 아니라 capability ref에서 읽는다.
- 실제 계산이나 조회 결과는 작업대 실행 결과 ref로 남긴다.

## Forbidden

- API parameters/returns를 SkillSpec에 중복하지 않는다.
