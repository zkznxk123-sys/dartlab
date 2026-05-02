---
title: 공시 이벤트 중요도 검토
skillId: disclosureEventReview
category: finance
---

# 공시 이벤트 중요도 검토

기업 공시 목록과 가능한 경량 본문 근거를 확인해 중요한 이벤트 후보와 한계를 구분한다.

## Metadata

- id: `disclosureEventReview`
- category: `finance`
- kind: `curated`
- status: `unverified`
- Pyodide: `limited`

## When To Use

- 최근 공시 중요한 내용
- DART 공시 영향 또는 리스크 질문

## Capability Refs

- `Company.disclosure`
- `Company.liveFilings`
- `Company.readFiling`

## Required Evidence

- target
- period
- table
- basis

## Expected Outputs

- 중요 공시 후보
- 판단 근거
- 제목 기준 또는 본문 기준 한계

## Runtime Compatibility

| runtime | status | notes |
|---|---:|---|
| `server` | `supported` |  |
| `localPython` | `supported` |  |
| `mcp` | `supported` |  |
| `webAi` | `limited` |  |
| `pyodide` | `limited` | liveFilings와 DART OpenAPI 직접 호출은 CORS 때문에 사용하지 않는다.; 본문 미조회 상태에서는 제목/프리빌드 기준 한계로 표시한다. |

## Guide

## 절차

- 공시 목록의 접수일, 제목, 유형을 확인한다.
- 가능한 경우 경량 본문 조회로 제목 기준 판단을 보강한다.
- 본문 미조회 상태에서는 제목 기준 우선순위라고 명시한다.

## Forbidden

- 본문 근거 없는 영향 단정
