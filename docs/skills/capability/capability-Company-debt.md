---
title: Company.debt capability view
skillId: capability:Company.debt
category: capability
---

# Company.debt capability view

공개 capability `Company.debt`를 찾고 실행에 연결하기 위한 generated skill view.

## Metadata

- id: `capability:Company.debt`
- category: `capability`
- kind: `generated`
- status: `observed`
- Pyodide: `unknown`

## When To Use

- 부채 구조 분석 (차입금, 부채비율, 만기 구조).
- "부채 구조 분석" → c.debt() "부채비율은?" → c.debt() 또는 c.show("ratios") "전체 상장사 부채 비교" → c.debt("all")

## Capability Refs

- `Company.debt`

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
