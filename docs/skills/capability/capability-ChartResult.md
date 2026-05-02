---
title: ChartResult capability view
skillId: capability:ChartResult
category: capability
---

# ChartResult capability view

공개 capability `ChartResult`를 찾고 실행에 연결하기 위한 generated skill view.

## Metadata

- id: `capability:ChartResult`
- category: `capability`
- kind: `generated`
- status: `observed`
- Pyodide: `unknown`

## When To Use

- chart() 반환 객체 — 시각화 + 렌더링.
- AI 역할: AI는 ChartResult/viz를 이미 검증된 표를 시각 설명으로 바꾸는 엔진으로 보고 단일값·무근거 차트를 만들지 않는다. When: SelectResult나 DataFrame 기반 근거를 차트로 설명해야 할 때. How: 표의 기간/series/value 근거가 충분한지 먼저 확인하고, chart() 결과의 spec을 최종 답변 ref와 연결한다.

## Capability Refs

- `ChartResult`

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
