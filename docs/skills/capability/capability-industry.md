---
title: industry capability view
skillId: capability:industry
category: capability
---

# industry capability view

공개 capability `industry`를 찾고 실행에 연결하기 위한 generated skill view.

## Metadata

- id: `capability:industry`
- category: `capability`
- kind: `generated`
- status: `observed`
- Pyodide: `unknown`

## When To Use

- 산업지도를 조회한다.
- AI 역할: AI는 industry를 섹터/밸류체인 맥락 엔진으로 보고 기업 지표와 산업 driver를 분리해 연결한다. When: 개별 기업 지표를 산업 공정, 밸류체인, peer 맥락으로 해석할 때. How: industry() 로 산업 목록 확인 → industry(industryId) 로 공정별 기업 위치 확인 → analysis/scan 근거와 연결.

## Capability Refs

- `industry`

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
