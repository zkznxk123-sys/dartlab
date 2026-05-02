---
title: 신용 위험 분석
skillId: creditRiskReview
category: finance
---

# 신용 위험 분석

기업의 재무 안정성, 차입 부담, 현금흐름 방어력을 신용 관점에서 점검한다.

## Metadata

- id: `creditRiskReview`
- category: `finance`
- kind: `curated`
- status: `unverified`
- Pyodide: `limited`

## When To Use

- 기업 신용 위험
- 재무 안정성 분석
- 부채와 이자보상 위험

## Capability Refs

- `Company.credit`
- `credit`
- `Company.analysis`
- `Company.show`
- `scan.debt`
- `scan.cashflow`

## Required Evidence

- target
- period
- metric
- table

## Expected Outputs

- credit thesis
- 위험 요인
- 완화 요인
- 한계

## Runtime Compatibility

| runtime | status | notes |
|---|---:|---|
| `server` | `supported` |  |
| `localPython` | `supported` |  |
| `mcp` | `supported` |  |
| `webAi` | `limited` |  |
| `pyodide` | `limited` | 신용등급 외부 실시간 조회는 서버 또는 로컬 Python 환경에서만 가능하다. |

## Guide

## 절차

- Company.credit와 재무 안정성 관련 capability를 확인한다.
- 부채, 이자보상, 영업현금흐름, 유동성 지표를 같은 기간 기준으로 만든다.
- 위험 요인과 완화 요인을 별도 ref로 구분한다.
- 금융업이면 일반 부채비율 해석 한계를 남긴다.

## Forbidden

- 근거 없는 등급 단정
- 결손값을 0으로 간주
