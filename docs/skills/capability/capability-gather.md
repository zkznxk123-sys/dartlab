---
title: gather capability view
skillId: capability:gather
category: capability
---

# gather capability view

공개 capability `gather`를 찾고 실행에 연결하기 위한 generated skill view.

## Metadata

- id: `capability:gather`
- category: `capability`
- kind: `generated`
- status: `observed`
- Pyodide: `unknown`

## When To Use

- 외부 시장 데이터 수집 — 주가·수급·거시지표·뉴스 4 축.
- AI 역할: AI는 gather를 외부 데이터 수집 진입점으로 보고 데이터 신선도, 시장, 수집 가능 범위를 먼저 확인한다. When: 분석 엔진에 필요한 외부 데이터를 수집할 때. How: gather → analysis/quant 파이프라인. gather("price") 는 quant 의 데이터 원천. gather("macro") 는 macro 엔진과 상호 보완 (raw 데이터 vs 분석 결과). Verified: gather("news") → 뉴스 목록 + 헤드라인 해석 (observed via ai-ask, 2026-04-25 — 정식 Phase P 판정 아님) See Also quant : 주가 기반 정량 분석 — gather("price") 데이터 소비. macro : 거시 분석 — gather("macro") raw 데이터의 분석 결과. scan : 전종목 비교 — 사전 빌드 데이터와 gather 실시간 데이터 상호 보완.

## Capability Refs

- `gather`

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
