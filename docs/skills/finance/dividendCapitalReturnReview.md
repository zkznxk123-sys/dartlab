---
title: 배당과 주주환원 분석
skillId: dividendCapitalReturnReview
category: finance
---

# 배당과 주주환원 분석

배당, 자사주, 총환원율을 이익과 현금흐름의 지속 가능성 관점에서 분석한다.

## Metadata

- id: `dividendCapitalReturnReview`
- category: `finance`
- kind: `curated`
- status: `unverified`
- Pyodide: `limited`

## When To Use

- 배당 매력 분석
- 주주환원 정책 점검
- 자사주와 배당 지속 가능성

## Capability Refs

- `Company.capital`
- `Company.analysis`
- `Company.show`
- `scan.dividendTrend`
- `scan.cashflow`

## Required Evidence

- target
- period
- metric
- table

## Expected Outputs

- shareholder return thesis
- 배당/자사주 근거
- 지속 가능성 한계

## Runtime Compatibility

| runtime | status | notes |
|---|---:|---|
| `server` | `supported` |  |
| `localPython` | `supported` |  |
| `mcp` | `supported` |  |
| `webAi` | `limited` |  |
| `pyodide` | `limited` | 공시 당일 신규 주주환원 이벤트는 live filings가 가능한 서버 경로에서 보강한다. |

## Guide

## 절차

- Company.capital과 현금흐름 관련 capability를 함께 확인한다.
- 배당성향, 배당수익률, 자사주, 총환원율을 기간별 표로 만든다.
- 지속 가능성은 이익과 OCF/FCF 근거가 있을 때만 판단한다.
- 주가 또는 배당 기준일 한계를 답변에 남긴다.

## Forbidden

- 근거 없는 배당 지속 가능성 단정
- 주가 기준일 없는 배당수익률 판단
