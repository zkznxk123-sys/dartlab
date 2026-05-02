---
title: DartLab Skills / Runtime
description: Local Python, Pyodide, Web AI, MCP, VSCode 같은 실행 환경별 제약과 근거 흐름.
---

# Runtime

Local Python, Pyodide, Web AI, MCP, VSCode 같은 실행 환경별 제약과 근거 흐름.

## [데이터 가용성 확인](runtime/runtime-dataAvailabilityCheck)

분석 전에 dataset, Company topic, snapshot 최신성, 실행 가능 runtime을 확인한다.

- id: `runtime.dataAvailabilityCheck`
- status: `unverified`
- pyodide: `supported`

## [MCP 외부 AI Workbench 연결](runtime/runtime-mcpWorkbench)

MCP 클라이언트가 DartLab skill resolver와 workbench action을 같은 방식으로 쓰게 한다.

- id: `runtime.mcpWorkbench`
- status: `unverified`
- pyodide: `unsupported`

## [Pyodide / Web AI 실행 범위](runtime/runtime-pyodideBrowser)

브라우저에서 가능한 DartLab skill과 제한을 구분한다.

- id: `runtime.pyodideBrowser`
- status: `unverified`
- pyodide: `supported`

## [Skill 개발과 엔진 조합 루프](runtime/runtime-skillDevelopmentLoop)

기본 엔진 capability를 조합해 엔진에 직접 정의되지 않은 분석 절차를 만들고 audit 결과를 docstring 또는 SkillSpec 개선으로 되돌리는 체계다.

- id: `runtime.skillDevelopmentLoop`
- status: `unverified`
- pyodide: `limited`

## [Workbench 근거 생성과 검산 흐름](runtime/runtime-workbenchEvidenceFlow)

skill 절차를 실행 결과 ref와 최종 검산으로 연결하는 공통 작업 흐름이다.

- id: `runtime.workbenchEvidenceFlow`
- status: `unverified`
- pyodide: `limited`
