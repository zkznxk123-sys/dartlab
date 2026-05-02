---
title: Company.gather capability view
skillId: capability:Company.gather
category: capability
---

# Company.gather capability view

공개 capability `Company.gather`를 찾고 실행에 연결하기 위한 generated skill view.

## Metadata

- id: `capability:Company.gather`
- category: `capability`
- kind: `generated`
- status: `observed`
- Pyodide: `unknown`

## When To Use

- 외부 시장 데이터 수집 — 4축 (price/flow/macro/news).
- When: 주가·수급·거시지표·뉴스 원본 데이터가 필요할 때. How: axis 로 데이터 종류 지정. 무인자 = 가이드. "주가 데이터" → c.gather("price") "외국인/기관 수급" → c.gather("flow") "거시경제 지표" → c.gather("macro") "뉴스 수집" → c.gather("news") 또는 c.news() Verified: gather("news") → 뉴스 목록 + 헤드라인 해석 (observed via ai-ask, 2026-04-25 — 정식 Phase P 판정 아님)

## Capability Refs

- `Company.gather`

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
