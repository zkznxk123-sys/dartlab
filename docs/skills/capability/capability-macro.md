---
title: macro capability view
skillId: capability:macro
category: capability
---

# macro capability view

공개 capability `macro`를 찾고 실행에 연결하기 위한 generated skill view.

## Metadata

- id: `capability:macro`
- category: `capability`
- kind: `generated`
- status: `observed`
- Pyodide: `unknown`

## When To Use

- 매크로 분석 실행.
- AI 역할: AI는 macro를 시장 환경과 기업/섹터 해석을 연결하는 엔진으로 보고 asOf, 지표, 방향성 근거를 고정한다. When: 종목 분석 전 경제 환경을 먼저 파악할 때. Company 없이 사용 가능. How: 6막 인과의 최상위 — macro(사이클) → scan(업종) → analysis(기업) 순서. story macro/crisis 타입이 macro 종합 → analysis(안정성, 현금흐름) 순서로 조합. Verified: macro("사이클") → CLI + 사분면 + 금리 + 유동성 + 심리 (observed via ai-ask, 2026-04-25 — 정식 Phase P 판정 아님) macro + analysis 조합 → 경제 고려한 논제 검증 (observed via ai-ask, 2026-04-25 — 정식 Phase P 판정 아님) See Also scan : 전종목 횡단 — macro 사이클에 따른 업종별 영향 비교. quant : 시장 심리·변동

## Capability Refs

- `macro`

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
