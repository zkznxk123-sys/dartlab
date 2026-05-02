---
title: 퀀트 신호 교차검토
skillId: quantSignalReview
category: finance
---

# 퀀트 신호 교차검토

가격, 변동성, 밸류에이션, 모멘텀 신호를 같은 기준일에서 확인해 계량 판단을 보조한다.

## Metadata

- id: `quantSignalReview`
- category: `finance`
- kind: `curated`
- status: `unverified`
- Pyodide: `limited`

## When To Use

- 이 종목 기술적으로 어떤지
- 모멘텀과 변동성 같이 봐줘

## Capability Refs

- `Company.quant`
- `quant`

## Required Evidence

- target
- metric
- latestAsOf
- table

## Expected Outputs

- 신호 요약
- 근거 표
- 한계

## Runtime Compatibility

| runtime | status | notes |
|---|---:|---|
| `server` | `supported` |  |
| `localPython` | `supported` |  |
| `mcp` | `supported` |  |
| `webAi` | `limited` |  |
| `pyodide` | `limited` | gather("price") 같은 외부 가격 API 호출은 브라우저 CORS 때문에 사용하지 않는다.; 가격 데이터가 없으면 재무/valuation-lite 기반 보조 신호로 제한한다. |

## Guide

## 절차

- 대상과 가격 데이터 기준일을 확인한다.
- quant capability의 사용 가능한 metric을 확인한다.
- 모멘텀/변동성/밸류에이션 신호를 같은 기준으로 계산한다.

## Forbidden

- 근거 없는 매수/매도 단정
