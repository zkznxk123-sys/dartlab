---
title: scan 횡단 분석 엔진
skillId: basic.scan
category: basic
---

# scan 횡단 분석 엔진

DartLab `scan` 엔진의 역할과 capability 묶음을 찾기 위한 generated basic engine skill.

## Metadata

- id: `basic.scan`
- category: `basic`
- kind: `generated`
- status: `observed`
- Pyodide: `unknown`

## When To Use

- AI는 scan을 전종목 횡단 비교와 스크리닝 엔진으로 보고 universe, metric, 기간, rank 근거를 만든다.
- 축(axis)별 전종목 횡단분석. / AI 역할: AI는 scan을 전종목 횡단 비교와 스크리닝 엔진으로 보고 universe, metric, 기간, rank 근거를 만든다. When: 특정 종목 심층 분석 전, 업종·시장 내 상대 위치를 파악할 때. How: scan 으로 전체 분포를 보고 → analysis 로 개별 종목 심층 분석. story credit/governance/audit 타입에서 scan 데이터를 동종업계 비
- 계정
- 감사리스크
- 주주환원
- 현금흐름
- 부채구조
- 공시리스크

## Capability Refs

- `scan`
- `scan.account`
- `scan.audit`
- `scan.capital`
- `scan.cashflow`
- `scan.debt`
- `scan.disclosureRisk`
- `scan.dividendTrend`
- `scan.efficiency`
- `scan.fields`
- `scan.governance`
- `scan.growth`
- `scan.industry`
- `scan.insider`
- `scan.liquidity`
- `scan.macroBeta`
- `scan.market`
- `scan.network`
- `scan.profitability`
- `scan.quality`
- `scan.ratio`
- `scan.screen`
- `scan.valuation`
- `scan.workforce`

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

- AI 역할: AI는 scan을 전종목 횡단 비교와 스크리닝 엔진으로 보고 universe, metric, 기간, rank 근거를 만든다.
- 이 skill은 엔진 능력 지도다. API 상세는 capabilityRefs의 docstring/generated capability에서 확인한다.
- 필요 입력, 반환 형태, 단위, 실제 반환 키를 이 skill에 중복하지 않는다.
- 분석 중 생성한 숫자·날짜·표·한계는 ref로 남겨 최종 답변 검산에 연결한다.

## Forbidden

- API parameters/returns/unit/actual return keys를 SkillSpec에 중복하지 않는다.
- workbench tool 사용법을 basic engine skill에 넣지 않는다.
