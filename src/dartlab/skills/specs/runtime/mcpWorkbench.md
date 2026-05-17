---
id: runtime.mcpWorkbench
title: MCP 외부 AI Workbench 연결
kind: curated
scope: builtin
status: unverified
category: runtime
purpose: MCP 클라이언트가 DartLab skill resolver와 workbench action을 같은 방식으로 쓰게 한다.
whenToUse:
  - MCP에서 DartLab 쓰기
  - 외부 AI가 DartLab skill 검색
inputs:
  - MCP client
outputs:
  - canonical workbench flow
  - skill search flow
toolRefs:
  - search_reference
  - InspectDataset
  - EngineCall
  - RunPython
  - finalize_answer
requiredEvidence:
  - skillRef
  - execution
expectedOutputs:
  - MCP setup guide
runtimeCompatibility:
  server:
    status: supported
  localPython:
    status: supported
  mcp:
    status: supported
  webAi:
    status: unsupported
  pyodide:
    status: unsupported
    limitations:
      - MCP stdio는 브라우저 Pyodide runtime이 아니라 로컬/서버 프로세스 경로다.
failureModes:
  - legacy engine tool을 기본 표면으로 안내
forbidden:
  - MCP에서 skills 의미론을 새로 정의
examples:
  - MCP에서 DartLab skill을 어떻게 쓰나
source:
  type: curated_markdown
  owner: dartlab
lastUpdated: "2026-05-02"
---

## 절차

- MCP 기본 표면은 workbench action과 skill resolver다.
- 먼저 `searchDartlabSkills` 또는 `search_reference`로 목적 skill을 찾는다.
- API 상세가 필요하면 capability ref를 확인한다.
- 계산은 `RunPython`으로 실행하고 `finalize_answer`에서 ref 검산을 통과한다.
- legacy engine tool은 compatibility 옵션이 켜진 경우에만 사용한다.

