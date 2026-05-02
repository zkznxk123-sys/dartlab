---
title: ask capability view
skillId: capability:ask
category: capability
---

# ask capability view

공개 capability `ask`를 찾고 실행에 연결하기 위한 generated skill view.

## Metadata

- id: `capability:ask`
- category: `capability`
- kind: `generated`
- status: `observed`
- Pyodide: `unknown`

## When To Use

- AI 에게 질문. LLM 이 DartLab 을 읽고 실행한 뒤 검산해 답한다.
- "삼성전자 수익성 분석" -> dartlab.ask("삼성전자 수익성 분석해줘") "삼성 vs SK하이닉스" -> dartlab.ask("삼성전자와 SK하이닉스 비교") "반도체 업황" -> dartlab.ask("반도체 업황 어때") (종목 불필요)

## Capability Refs

- `ask`

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
