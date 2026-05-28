---
id: runtime.streaming
title: Streaming — chat-native 응답 패턴 SSOT
kind: curated
scope: observed
category: runtime
purpose: dartlab agent (`ai/agent.py`) chat-native streaming 응답 패턴 SSOT. tool_use / text 블록 stream + 사용자 partial render. Anthropic Messages API streaming 표준.
whenToUse:
  - streaming
  - chat-native streaming
  - partial render
  - tool_use stream
  - SSE
inputs:
  - 사용자 메시지
  - tool registry
outputs:
  - streamed response (SSE)
  - tool_use blocks
toolRefs: []
knowledgeRefs:
  - runtime.toolComposition
sourceRefs:
  - dartlab://skills/runtime.streaming
requiredEvidence:
  - skillRef
  - executionRef
runtimeCompatibility:
  server:
    status: supported
  localPython:
    status: supported
  mcp:
    status: supported
  webAi:
    status: supported
  pyodide:
    status: limited
linkedSkills:
  - runtime.toolComposition
  - runtime.channel
---

## stream event 분류

| event | 의미 | 사용자 render |
|---|---|---|
| `message_start` | 응답 시작 | spinner / 시작 표시 |
| `content_block_start` | 블록 시작 (text 또는 tool_use) | 빈 컨테이너 |
| `content_block_delta` | 블록 partial | partial text 또는 tool_use partial |
| `content_block_stop` | 블록 완료 | 컨테이너 close |
| `message_delta` | 메타 (usage / stop_reason) | usage 표시 |
| `message_stop` | 응답 종료 | spinner stop |

## 사용자 UX

- text 블록: token-by-token render (typewriter).
- tool_use 블록: tool 이름 + arguments partial → 실행 트리거 시점에 사용자 알림.
- evidence GATE 결과 → 사용자에게 검증 통과 표시.

## 강행 룰

1. 모든 응답 → SSE streaming (non-streaming 모드 X).
2. tool_use 결과 → 다음 turn 으로 자동 pipeline (사용자 confirm 없음).
3. evidence GATE 실패 시 → 사용자 거부 표시 + 재시도 옵션.

## 안티패턴

- streaming 비활성화 (전체 응답 wait → 사용자 UX 저하).
- tool_use 결과 fully wait 후 text 시작 (parallel render 가능).

## 기본 검증

- SSE event 순서 정합 (message_start → block_start → block_delta+ → block_stop → message_stop).
- tool_use 블록의 `input` JSON 정합.
- usage 메타 (`input_tokens`, `output_tokens`, `cache_creation_input_tokens`) 동행.
