---
title: gather 엔진 데이터 수집 사용 지도
skillId: engines.gatherUsage
category: engines
---

# gather 엔진 데이터 수집 사용 지도

주가, 수급, 뉴스, 거시 원자료가 필요할 때 gather를 분석 엔진의 evidence 공급원으로 쓰는 절차를 설명한다.

## Metadata

- id: `engines.gatherUsage`
- category: `engines`
- kind: `curated`
- status: `unverified`
- Pyodide: `limited`

## When To Use

- 주가 추이, 수급, 뉴스, 금리 원자료가 필요할 때
- quant나 macro 해석 전에 raw data 기준일을 확인해야 할 때
- 분석 결과에 최신 시장 데이터 보강이 필요할 때

## Capability Refs

- `gather`
- `Company.gather`
- `quant`
- `macro`

## Dataset Refs

- market.price
- market.flow
- macro.raw

## Required Evidence

- target
- metric
- period
- latestAsOf
- table

## Expected Outputs

- raw market data table
- freshness disclosure
- downstream engine input refs

## Runtime Compatibility

| runtime | status | notes |
|---|---:|---|
| `server` | `supported` |  |
| `localPython` | `supported` |  |
| `mcp` | `supported` |  |
| `webAi` | `limited` | 웹에서는 네트워크와 provider 허용 범위에 따라 일부 축만 가능하다. |
| `pyodide` | `limited` | 외부 네트워크 provider와 CORS 제약이 있을 수 있다.; 서버 snapshot이 없는 최신 데이터는 unavailable 처리한다. |

## Guide

## 가능한 분석

- gather를 쓰면 분석 엔진이 없는 원자료성 질문, 최신성 확인, 시장 데이터 보강이 가능하다.
- raw table을 먼저 ref로 남기면 quant/macro/story가 만든 해석과 원천 데이터를 분리할 수 있다.

## 절차

- `basic.gather`와 `gather` capability에서 축별 데이터 가능 범위를 확인한다.
- 질문이 raw data 요청인지, 해석 요청인지 분리한다.
- raw data면 gather 결과 자체를 표 evidence로 남긴다.
- 해석 요청이면 gather 결과를 quant, macro, analysis의 보조 evidence로 연결한다.
- latestAsOf, provider, 빈 결과 또는 네트워크 한계를 최종 답변 한계에 포함한다.

## Forbidden

- API parameters/returns를 SkillSpec에 중복하지 않는다.
- 수집 실패를 추정값으로 대체하지 않는다.
