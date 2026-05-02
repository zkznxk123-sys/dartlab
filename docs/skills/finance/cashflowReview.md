---
title: 현금흐름 분석
skillId: cashflowReview
category: finance
---

# 현금흐름 분석

영업현금흐름, 투자, 재무활동, 이익의 현금 전환을 점검한다.

## Metadata

- id: `cashflowReview`
- category: `finance`
- kind: `curated`
- status: `unverified`
- Pyodide: `limited`

## When To Use

- 현금흐름 분석
- 이익은 나는데 현금이 부족한지
- FCF와 운전자본 변화

## Capability Refs

- `Company.analysis`
- `Company.show`
- `scan.cashflow`
- `scan.quality`
- `Company.credit`

## Required Evidence

- target
- period
- metric
- table

## Expected Outputs

- cashflow thesis
- CF 근거 표
- 이익 품질
- 한계

## Runtime Compatibility

| runtime | status | notes |
|---|---:|---|
| `server` | `supported` |  |
| `localPython` | `supported` |  |
| `mcp` | `supported` |  |
| `webAi` | `limited` |  |
| `pyodide` | `limited` | 세부 운전자본 주석이 없는 snapshot에서는 원인 판단을 제한한다. |

## Guide

## 절차

- CF, IS, BS 관련 capability를 확인하고 같은 기간 기준으로 묶는다.
- OCF, capex, FCF, 순이익 또는 운전자본 변동을 표로 만든다.
- 현금흐름 품질 claim은 이익과 현금의 차이를 보여주는 ref에 묶는다.
- 세부 주석이 없으면 원인 판단을 제한한다.

## Forbidden

- CF 표 없이 현금 창출력 단정
- 결손값을 0으로 대체
