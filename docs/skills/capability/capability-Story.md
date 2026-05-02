---
title: Story capability view
skillId: capability:Story
category: capability
---

# Story capability view

공개 capability `Story`를 찾고 실행에 연결하기 위한 generated skill view.

## Metadata

- id: `capability:Story`
- category: `capability`
- kind: `generated`
- status: `observed`
- Pyodide: `unknown`

## When To Use

- 보고서 조합기 — 6 엔진 블록을 조합하여 6막 구조화 보고서 생성.
- AI 역할: AI는 story를 검증된 engine output을 보고서 섹션으로 조립하는 엔진으로 보고 원자료 없이 새 claim을 만들지 않는다. When: 종목의 종합 분석 보고서가 필요할 때. How: 11 타입 중 선택 — full(전체), executive(경영진 요약), credit(신용), valuation(가치평가), growth(성장), crisis(위기), audit(감사), dividend(배당), governance(지배구조), macro(매크로), thesis(투자논제). Verified: credit 타입 → credit + analysis(안정성,현금흐름,자금조달) 조합 (observed via ai-ask, 2026-04-25 — 정식 Phase P 판정 아님) audit 타입 → analysis(이익품질,재무정합성) + 감사의견 (observed via ai-ask, 2026-04-25 — 정식 Phase P 판정 아님) governance 타입 →

## Capability Refs

- `Story`

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
