---
title: 가치평가 가정 분해 검토
skillId: damodaranValuationReview
category: finance
---

# 가치평가 가정 분해 검토

성장, 마진, 재투자, 할인율, 터미널 가정을 분해해 가치평가 민감도와 한계를 검토한다.

## Metadata

- id: `damodaranValuationReview`
- category: `finance`
- kind: `curated`
- status: `unverified`
- Pyodide: `limited`

## When To Use

- 다모다란식 가치평가
- DCF 가정과 민감도 점검

## Capability Refs

- `Company.analysis`
- `Company.show`
- `Company.quant`
- `macro`

## Required Evidence

- target
- period
- metric
- table
- basis

## Expected Outputs

- valuation assumptions
- sensitivity table
- limits

## Runtime Compatibility

| runtime | status | notes |
|---|---:|---|
| `server` | `supported` |  |
| `localPython` | `supported` |  |
| `mcp` | `supported` |  |
| `webAi` | `limited` |  |
| `pyodide` | `limited` | 할인율, 금리, 시장가격 등 live macro/price 보강은 서버 환경에서 수행한다. |

## Guide

## 절차

- 매출 성장률과 마진 추세를 실제 재무 데이터로 확인한다.
- 재투자율 또는 자본효율 가정의 근거를 확인한다.
- 할인율 또는 매크로 가정의 출처와 기준일을 밝힌다.
- 단일 목표가가 아니라 민감도 표와 한계를 함께 제시한다.

## Forbidden

- 출처 없는 할인율
- 민감도 없는 DCF 결론
