---
title: viz 시각 설명 엔진
skillId: basic.viz
category: basic
---

# viz 시각 설명 엔진

DartLab `viz` 엔진의 역할과 capability 묶음을 찾기 위한 generated basic engine skill.

## Metadata

- id: `basic.viz`
- category: `basic`
- kind: `generated`
- status: `observed`
- Pyodide: `unknown`

## When To Use

- AI는 ChartResult/viz를 이미 검증된 표를 시각 설명으로 바꾸는 엔진으로 보고 단일값·무근거 차트를 만들지 않는다.
- chart() 반환 객체 — 시각화 + 렌더링. / AI 역할: AI는 ChartResult/viz를 이미 검증된 표를 시각 설명으로 바꾸는 엔진으로 보고 단일값·무근거 차트를 만들지 않는다. When: SelectResult나 DataFrame 기반 근거를 차트로 설명해야 할 때. How: 표의 기간/series/value 근거가 충분한지 먼저 확인하고, chart() 결과의 spec을 최종 답변 ref와 연결한다.

## Capability Refs

- `ChartResult`

## Expected Outputs

- engine AI role
- engine capability map
- capability-backed evidence refs

## Runtime Compatibility

| runtime | status | notes |
|---|---:|---|
| `server` | `supported` |  |
| `localPython` | `supported` |  |
| `mcp` | `supported` |  |
| `webAi` | `limited` | 실제 실행 가능 여부는 연결된 capability와 dataset skill을 함께 확인한다. |
| `pyodide` | `unknown` | 엔진 지도 자체는 조회 가능하다. 실행 가능 여부는 조합되는 skill과 capability별 runtimeCompatibility를 따른다. |

## Procedure

- AI 역할: AI는 ChartResult/viz를 이미 검증된 표를 시각 설명으로 바꾸는 엔진으로 보고 단일값·무근거 차트를 만들지 않는다.
- 이 skill은 엔진 능력 지도다. API 상세는 capabilityRefs의 docstring/generated capability에서 확인한다.
- 필요 입력, 반환 형태, 단위, 실제 반환 키를 이 skill에 중복하지 않는다.
- 분석 중 생성한 숫자·날짜·표·한계는 ref로 남겨 최종 답변 검산에 연결한다.

## Forbidden

- API parameters/returns/unit/actual return keys를 SkillSpec에 중복하지 않는다.
- workbench tool 사용법을 basic engine skill에 넣지 않는다.
