---
title: gather 데이터 수집 엔진
skillId: basic.gather
category: basic
---

# gather 데이터 수집 엔진

DartLab `gather` 엔진의 역할과 capability 묶음을 찾기 위한 generated basic engine skill.

## Metadata

- id: `basic.gather`
- category: `basic`
- kind: `generated`
- status: `observed`
- Pyodide: `unknown`

## When To Use

- AI는 gather를 외부 데이터 수집 진입점으로 보고 데이터 신선도, 시장, 수집 가능 범위를 먼저 확인한다.
- 외부 시장 데이터 수집 — 주가·수급·거시지표·뉴스 4 축. / AI 역할: AI는 gather를 외부 데이터 수집 진입점으로 보고 데이터 신선도, 시장, 수집 가능 범위를 먼저 확인한다. When: 분석 엔진에 필요한 외부 데이터를 수집할 때. How: gather → analysis/quant 파이프라인. gather("price") 는 quant 의 데이터 원천. gather("macro") 는 macro 엔진과 상호 보완 (raw 데이터 vs 분석
- 수급
- 내부자거래
- KRX 회사별 시계열
- KRX 지수 일별 매매현황 (시장군별 전체 지수 패키지)
- 거시지표
- 뉴스

## Capability Refs

- `gather`
- `gather.flow`
- `gather.insider`
- `gather.krx`
- `gather.krxIndex`
- `gather.macro`
- `gather.news`
- `gather.ownership`
- `gather.peers`
- `gather.price`
- `gather.sector`

## Required Evidence

- asOf
- period
- universe
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

- AI 역할: AI는 gather를 외부 데이터 수집 진입점으로 보고 데이터 신선도, 시장, 수집 가능 범위를 먼저 확인한다.
- 이 skill은 엔진 능력 지도다. API 상세는 capabilityRefs의 docstring/generated capability에서 확인한다.
- 필요 입력, 반환 형태, 단위, 실제 반환 키를 이 skill에 중복하지 않는다.
- 분석 중 생성한 숫자·날짜·표·한계는 ref로 남겨 최종 답변 검산에 연결한다.

## Forbidden

- API parameters/returns/unit/actual return keys를 SkillSpec에 중복하지 않는다.
- workbench tool 사용법을 basic engine skill에 넣지 않는다.
