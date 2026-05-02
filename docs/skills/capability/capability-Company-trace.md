---
title: Company.trace capability view
skillId: capability:Company.trace
category: capability
---

# Company.trace capability view

공개 capability `Company.trace`를 찾고 실행에 연결하기 위한 generated skill view.

## Metadata

- id: `capability:Company.trace`
- category: `capability`
- kind: `generated`
- status: `observed`
- Pyodide: `unknown`

## When To Use

- topic 데이터의 출처(docs/finance/report)와 선택 근거 추적.
- "이 데이터 어디서 온 거야?" → c.trace("BS") "데이터 출처 확인" → c.trace(topic)

## Capability Refs

- `Company.trace`

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
