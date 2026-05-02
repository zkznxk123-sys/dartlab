---
title: quant capability view
skillId: capability:quant
category: capability
---

# quant capability view

공개 capability `quant`를 찾고 실행에 연결하기 위한 generated skill view.

## Metadata

- id: `capability:quant`
- category: `capability`
- kind: `generated`
- status: `observed`
- Pyodide: `unknown`

## When To Use

- 가격 기반 정량 분석 — 8 그룹 30+ 축 (기술·리스크·팩터·백테스트·알파).
- AI 역할: AI는 quant를 가격·팩터·시계열 신호 엔진으로 보고 기간, benchmark, 수익률/변동성 근거를 분리한다. When: 주가 기반 기술적 신호·팩터·리스크를 정량 분석할 때. How: quant("판단") 으로 종합 신호 확인 → 세부 축으로 근거 파악. quant("벤치마크") 로 시장·섹터·스타일 benchmarkStack 을 확인한다. beta/residual/factor/BAB 는 기본 market mode를 유지하고, benchmarkMode="sector" 또는 "style" 로 상대 기준을 명시 전환한다. analysis(재무) + quant(기술) 조합이 story full/valuation 타입의 핵심. credit 과 함께 사용 시 altman/piotroski 로 부도 위험 교차 검증. Verified: quant("판단") → RSI/ADX/MACD/볼린저/상대강도 + 종합 판정 (observed via ai-ask, 2026-04-25 —

## Capability Refs

- `quant`

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
