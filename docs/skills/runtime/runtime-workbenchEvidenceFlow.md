---
title: Workbench 근거 생성과 검산 흐름
skillId: runtime.workbenchEvidenceFlow
category: runtime
---

# Workbench 근거 생성과 검산 흐름

skill 절차를 실행 결과 ref와 최종 검산으로 연결하는 공통 작업 흐름이다.

## Metadata

- id: `runtime.workbenchEvidenceFlow`
- category: `runtime`
- kind: `curated`
- status: `unverified`
- Pyodide: `limited`

## When To Use

- 실행하고 근거 남기기
- 검산하고 답변 마무리
- evidence ref 만들기
- run_python 결과를 답변 근거로 쓰기

## Required Evidence

- skillRef
- execution
- table

## Expected Outputs

- 검산 가능한 답변 초안
- refs
- limits

## Runtime Compatibility

| runtime | status | notes |
|---|---:|---|
| `server` | `supported` |  |
| `localPython` | `supported` |  |
| `mcp` | `supported` |  |
| `webAi` | `limited` |  |
| `pyodide` | `limited` | 브라우저에서는 선택한 skill과 dataset snapshot 범위 안에서만 실행한다. |

## Guide

## 절차

- 선택한 skill의 requiredEvidence를 실행 전 체크리스트로 둔다.
- dataset이 필요한 질문은 먼저 inspect 단계로 schema, latest, metric 후보를 확인한다.
- 계산은 실행 결과가 table/value/date ref를 만들 수 있게 수행한다. 표를 만들 때 `metric`은 숫자 컬럼으로 두고, 날짜·라벨·식별자는 `meta`, `asOf`, `period`, `target` 또는 별도 문자열 컬럼으로 둔다.
- `emit_result`는 run_python prelude가 제공하는 예약 helper다. 직접 `def emit_result`로 만들거나 다른 값으로 덮어쓰지 않는다.
- 기능 설명이나 API 사용법처럼 계산이 필요 없는 질문은 run_python으로 가짜 evidence table을 만들지 않는다. skill/capability ref를 근거로 좁은 설명을 제출한다.
- 시각화는 table ref가 있고 2개 이상 비교 가능한 값이 있을 때만 만든다.
- 최종 답변은 evidence refs와 limits를 함께 제출해 검산을 통과시킨다.

## Forbidden

- tool call transcript를 최종 답변으로 노출
- 근거 없는 숫자 claim
- 단일값 chart
- run_python 코드 안에서 emit_result를 재정의
