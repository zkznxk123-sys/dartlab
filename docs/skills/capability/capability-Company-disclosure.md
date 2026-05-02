---
title: Company.disclosure capability view
skillId: capability:Company.disclosure
category: capability
---

# Company.disclosure capability view

공개 capability `Company.disclosure`를 찾고 실행에 연결하기 위한 generated skill view.

## Metadata

- id: `capability:Company.disclosure`
- category: `capability`
- kind: `generated`
- status: `observed`
- Pyodide: `unknown`

## When To Use

- **[단일 종목 전용]** OpenDART 공시 목록 조회. **stockCode 필수**.
- 단일 종목: "삼성전자 최근 공시 뭐 나왔어?" → c.disclosure(days=30) 전종목: "최근 어떤 회사들이 자사주 매입했어?" → dartlab.search("자기주식 취득")

## Capability Refs

- `Company.disclosure`

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
