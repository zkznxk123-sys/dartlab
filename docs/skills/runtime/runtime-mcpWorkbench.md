---
title: MCP 외부 AI Workbench 연결
skillId: runtime.mcpWorkbench
category: runtime
---

# MCP 외부 AI Workbench 연결

MCP 클라이언트가 DartLab skill resolver와 workbench action을 같은 방식으로 쓰게 한다.

## Metadata

- id: `runtime.mcpWorkbench`
- category: `runtime`
- kind: `curated`
- status: `unverified`
- Pyodide: `unsupported`

## When To Use

- MCP에서 DartLab 쓰기
- 외부 AI가 DartLab skill 검색

## Required Evidence

- skillRef
- execution

## Expected Outputs

- MCP setup guide

## Runtime Compatibility

| runtime | status | notes |
|---|---:|---|
| `server` | `supported` |  |
| `localPython` | `supported` |  |
| `mcp` | `supported` |  |
| `webAi` | `unsupported` |  |
| `pyodide` | `unsupported` | MCP stdio는 브라우저 Pyodide runtime이 아니라 로컬/서버 프로세스 경로다. |

## Guide

## 절차

- MCP 기본 표면은 workbench action과 skill resolver다.
- 먼저 `searchDartlabSkills` 또는 `search_reference`로 목적 skill을 찾는다.
- API 상세가 필요하면 capability ref를 확인한다.
- 계산은 `run_python`으로 실행하고 `finalize_answer`에서 ref 검산을 통과한다.
- legacy engine tool은 compatibility 옵션이 켜진 경우에만 사용한다.

## Forbidden

- MCP에서 skills 의미론을 새로 정의
