---
id: runtime.README
title: Runtime 카테고리 hub
purpose: dartlab skills/specs/runtime/ 카테고리 진입점.
kind: curated
category: runtime
status: curated
requiredEvidence: []
expectedOutputs: []
runtimeCompatibility:
  pyodide:
    status: supported
  server:
    status: supported
  localPython:
    status: supported
  mcp:
    status: supported
  webAi:
    status: supported
whenToUse:
  - runtime 카테고리 시작점
---

# Skill OS — `runtime/` 카테고리 hub

> 실행 환경 spec. MCP server / pyodide 브라우저 / Workbench 흐름 등 *어디서 어떻게* 돌릴까.

---

## 추천 진입 순서

| 순서 | spec | 무엇을 |
|------|------|--------|
| 1 | [python.md](python.md) | Python 표준 실행 환경 |
| 2 | [workbenchEvidenceFlow.md](workbenchEvidenceFlow.md) | AI Workbench 5 패스 + evidence/ref 흐름 |
| 3 | [mcp.md](mcp.md) | MCP server 진입점 — 외부 LLM 도구 호출 |
| 4 | [mcpWorkbench.md](mcpWorkbench.md) | MCP 안 Workbench 운영 |
| 5 | [notebooks.md](notebooks.md) | Marimo / Jupyter 노트북 |
| 6 | [pyodide.md](pyodide.md) · [pyodideBrowser.md](pyodideBrowser.md) | 브라우저 Python 실행 |
| 7 | [providerProtocol.md](providerProtocol.md) | provider DI Protocol (DART/EDGAR/EDINET 추가 시) |
| 8 | [channel.md](channel.md) | 외부 채널 (블로그 / SNS / 차트 export) |
| 9 | [dataAvailabilityCheck.md](dataAvailabilityCheck.md) | 데이터 신선도 점검 |
| 10 | [untrustedContent.md](untrustedContent.md) | 외부 본문 untrusted 마커 강제 (보안 KPI) |

---

## 다음 카테고리

- **start/** — 첫 진입
- **operation/** — 운영 설계 SSOT
- **engines/** — 15 분석 엔진
- **recipes/** — 분석 recipe lifecycle

---

## 관련

- [SCHEMA.md](../SCHEMA.md) — Skill OS schema
- [TODO.md](../../../../../TODO.md) T10-5 — 본 hub 생성 트랙
- T2-5 (보안) — untrustedContent.md 강제 정합
- T11 (AI/LLM) — workbenchEvidenceFlow.md + mcp.md 본진
