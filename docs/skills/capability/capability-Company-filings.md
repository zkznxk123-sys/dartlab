---
title: Company.filings capability view
skillId: capability:Company.filings
category: capability
---

# Company.filings capability view

공개 capability `Company.filings`를 찾고 실행에 연결하기 위한 generated skill view.

## Metadata

- id: `capability:Company.filings`
- category: `capability`
- kind: `generated`
- status: `observed`
- Pyodide: `unknown`

## When To Use

- 공시 문서 목록 + DART 뷰어 링크.
- "이 회사 공시 목록 보여줘" → c.filings() "어떤 보고서가 있어?" → c.filings()로 보유 문서 확인

## Capability Refs

- `Company.filings`

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
