---
title: Company.show capability view
skillId: capability:Company.show
category: capability
---

# Company.show capability view

공개 capability `Company.show`를 찾고 실행에 연결하기 위한 generated skill view.

## Metadata

- id: `capability:Company.show`
- category: `capability`
- kind: `generated`
- status: `observed`
- Pyodide: `unknown`

## When To Use

- topic 의 데이터를 반환 — 내부 구현 (사용자는 ``c.show`` 호출).
- "분기 손익" → ``c.show("IS")`` "연간 손익" → ``c.show("IS", freq="Y")`` "별도 재무상태표" → ``c.show("BS", scope="separate")`` "2023년 손익" → ``c.show("IS", period="2023")`` "배당 정보" → ``c.show("dividend")`` "주요주주/최대주주" → ``c.show("majorHolder")``

## Capability Refs

- `Company.show`

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
