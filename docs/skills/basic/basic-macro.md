---
title: macro 거시 분석 엔진
skillId: basic.macro
category: basic
---

# macro 거시 분석 엔진

DartLab `macro` 엔진의 역할과 capability 묶음을 찾기 위한 generated basic engine skill.

## Metadata

- id: `basic.macro`
- category: `basic`
- kind: `generated`
- status: `observed`
- Pyodide: `unknown`

## When To Use

- AI는 macro를 시장 환경과 기업/섹터 해석을 연결하는 엔진으로 보고 asOf, 지표, 방향성 근거를 고정한다.
- 매크로 분석 실행. / AI 역할: AI는 macro를 시장 환경과 기업/섹터 해석을 연결하는 엔진으로 보고 asOf, 지표, 방향성 근거를 고정한다. When: 종목 분석 전 경제 환경을 먼저 파악할 때. Company 없이 사용 가능. How: 6막 인과의 최상위 — macro(사이클) → scan(업종) → analysis(기업) 순서. story macro/crisis 타입이 macro 종합 → analys
- 시장 매크로 (6막 인과 — 사이클/재고/기업/정책/유동성/심리/시나리오). KR 자동 위임. / When: 거시경제 환경·사이클 판단이 필요할 때. How: axis 로 분석 영역 지정. 무인자 = 가이드. "매크로" → c.macro() "경기 사이클" → c.macro("사이클") "위기 진단" → c.macro("위기") "2008 시나리오" → c.macro("시나리오", "2008 금융위기") Verified: macro("사이클") → CLI + 사분면 + 금리 + 유동성 +
- 자산
- 기업집계
- 위기
- 사이클
- 예측

## Capability Refs

- `macro`
- `Company.macro`
- `macro.assets`
- `macro.corporate`
- `macro.crisis`
- `macro.cycle`
- `macro.forecast`
- `macro.inventory`
- `macro.liquidity`
- `macro.rates`
- `macro.scenario`
- `macro.sentiment`
- `macro.summary`
- `macro.trade`

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

- AI 역할: AI는 macro를 시장 환경과 기업/섹터 해석을 연결하는 엔진으로 보고 asOf, 지표, 방향성 근거를 고정한다.
- 이 skill은 엔진 능력 지도다. API 상세는 capabilityRefs의 docstring/generated capability에서 확인한다.
- 필요 입력, 반환 형태, 단위, 실제 반환 키를 이 skill에 중복하지 않는다.
- 분석 중 생성한 숫자·날짜·표·한계는 ref로 남겨 최종 답변 검산에 연결한다.

## Forbidden

- API parameters/returns/unit/actual return keys를 SkillSpec에 중복하지 않는다.
- workbench tool 사용법을 basic engine skill에 넣지 않는다.
