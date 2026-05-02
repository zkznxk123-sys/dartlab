---
title: Company.governance capability view
skillId: capability:Company.governance
category: capability
---

# Company.governance capability view

공개 capability `Company.governance`를 찾고 실행에 연결하기 위한 generated skill view.

## Metadata

- id: `capability:Company.governance`
- category: `capability`
- kind: `generated`
- status: `observed`
- Pyodide: `unknown`

## When To Use

- 지배구조 분석 (이사회, 감사위원, 최대주주).
- "지배구조 분석" → c.governance() "사외이사 비율은?" → c.governance() "전체 상장사 거버넌스 비교" → c.governance("all")

## Capability Refs

- `Company.governance`

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
