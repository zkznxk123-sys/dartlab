---
title: industry 산업 분석 엔진
skillId: basic.industry
category: basic
---

# industry 산업 분석 엔진

DartLab `industry` 엔진의 역할과 capability 묶음을 찾기 위한 generated basic engine skill.

## Metadata

- id: `basic.industry`
- category: `basic`
- kind: `generated`
- status: `observed`
- Pyodide: `unknown`

## When To Use

- AI는 industry를 섹터/밸류체인 맥락 엔진으로 보고 기업 지표와 산업 driver를 분리해 연결한다.
- 산업지도를 조회한다. / AI 역할: AI는 industry를 섹터/밸류체인 맥락 엔진으로 보고 기업 지표와 산업 driver를 분리해 연결한다. When: 개별 기업 지표를 산업 공정, 밸류체인, peer 맥락으로 해석할 때. How: industry() 로 산업 목록 확인 → industry(industryId) 로 공정별 기업 위치 확인 → analysis/scan 근거와 연결.
- 이 회사의 밸류체인 산업 내 위치를 분석한다.
- 산업 taxonomy universe를 먼저 고정한 뒤 scan으로 같은 축 수익성 evidence를 만든다

## Capability Refs

- `industry`
- `Company.industry`
- `scan.industry`

## Required Evidence

- industry
- universe
- target
- metric
- value

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

- AI 역할: AI는 industry를 섹터/밸류체인 맥락 엔진으로 보고 기업 지표와 산업 driver를 분리해 연결한다.
- 이 skill은 엔진 능력 지도다. API 상세는 capabilityRefs의 docstring/generated capability에서 확인한다.
- 필요 입력, 반환 형태, 단위, 실제 반환 키를 이 skill에 중복하지 않는다.
- 분석 중 생성한 숫자·날짜·표·한계는 ref로 남겨 최종 답변 검산에 연결한다.

## Forbidden

- API parameters/returns/unit/actual return keys를 SkillSpec에 중복하지 않는다.
- workbench tool 사용법을 basic engine skill에 넣지 않는다.
