---
title: quant 엔진 가격·팩터 사용 지도
skillId: engines.quantUsage
category: engines
---

# quant 엔진 가격·팩터 사용 지도

가격, 모멘텀, 변동성, benchmark, factor 신호를 quant로 분리해 해석하는 절차를 설명한다.

## Metadata

- id: `engines.quantUsage`
- category: `engines`
- kind: `curated`
- status: `unverified`
- Pyodide: `limited`

## When To Use

- 주가 모멘텀, 변동성, 베타, benchmark 대비 성과가 궁금할 때
- 재무 분석과 가격 신호를 분리해서 투자 논제를 만들 때
- credit이나 analysis 결과를 시장 가격 신호로 교차 검증할 때

## Capability Refs

- `quant`
- `Company.quant`
- `gather`
- `analysis`
- `credit`

## Dataset Refs

- market.price

## Required Evidence

- target
- period
- benchmark
- metric
- value
- table

## Expected Outputs

- price signal evidence
- benchmark context
- technical versus fundamental distinction

## Runtime Compatibility

| runtime | status | notes |
|---|---:|---|
| `server` | `supported` |  |
| `localPython` | `supported` |  |
| `mcp` | `supported` |  |
| `webAi` | `limited` | Web AI는 사용 가능한 price snapshot과 브라우저 런타임 범위에 따른다. |
| `pyodide` | `limited` | 최신 price provider 접근과 긴 시계열 수집은 서버 경유가 필요할 수 있다. |

## Guide

## 가능한 분석

- quant를 쓰면 “회사가 좋은가”와 “시장이 어떻게 가격을 매기는가”를 분리할 수 있다.
- 모멘텀, 변동성, benchmark, factor 신호를 나누면 재무 해석과 가격 해석이 섞이지 않는다.

## 절차

- `basic.quant`와 `quant` capability에서 축과 benchmark 관련 guide를 확인한다.
- 질문이 기술적 신호, 리스크, factor, 가치 보조 신호 중 어디에 속하는지 정한다.
- period와 benchmark를 evidence로 고정한다.
- 재무/신용 질문이면 quant를 보조 근거로 쓰고, 주가 질문이면 quant를 주 근거로 쓴다.
- 최종 답변은 가격 신호와 재무 결론을 별도 문장으로 분리한다.

## Forbidden

- API parameters/returns를 SkillSpec에 중복하지 않는다.
- quant 신호만으로 재무 건전성이나 내재가치를 단정하지 않는다.
