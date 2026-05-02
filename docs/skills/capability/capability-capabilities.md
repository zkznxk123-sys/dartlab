---
title: capabilities capability view
skillId: capability:capabilities
category: capability
---

# capabilities capability view

공개 capability `capabilities`를 찾고 실행에 연결하기 위한 generated skill view.

## Metadata

- id: `capability:capabilities`
- category: `capability`
- kind: `generated`
- status: `observed`
- Pyodide: `unknown`

## When To Use

- dartlab 전체 기능 카탈로그 조회.
- "dartlab 뭐 할 수 있어?" -> capabilities() "분석 기능 뭐 있어?" -> capabilities("analysis") "scan 어떻게 써?" -> capabilities("scan") "재무건전성 관련 API?" -> capabilities(search="재무건전성")

## Capability Refs

- `capabilities`

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
