---
title: 기업 6막 인과 분석
skillId: companyCausalReview
category: finance
---

# 기업 6막 인과 분석

한 기업을 경제, 섹터, 기업, 재무, 가치 신호의 연결로 검토한다.

## Metadata

- id: `companyCausalReview`
- category: `finance`
- kind: `curated`
- status: `unverified`
- Pyodide: `limited`

## When To Use

- 특정 기업의 종합 분석
- 수익성, 안정성, 성장성, 경쟁력 판단

## Capability Refs

- `Company.analysis`
- `Company.show`
- `Company.quant`
- `Company.story`
- `scan`
- `macro`

## Required Evidence

- target
- period
- metric
- table

## Expected Outputs

- thesis
- 근거 표
- 리스크
- 한계

## Runtime Compatibility

| runtime | status | notes |
|---|---:|---|
| `server` | `supported` |  |
| `localPython` | `supported` |  |
| `mcp` | `supported` |  |
| `webAi` | `limited` |  |
| `pyodide` | `limited` | live gather, 외부 macro API, OAuth ask는 브라우저 CORS/인증 제약으로 제외한다. |

## Guide

## 절차

- 기업 식별과 사용 가능한 Company topic을 확인한다.
- macro, scan 또는 industry 맥락이 필요한지 reference에서 확인한다.
- Company.analysis와 원본 show 결과를 실행해 수치 근거를 만든다.
- 판단 claim은 대상, 기간, metric, value ref에 묶는다.

## Forbidden

- 근거 없는 투자판단
- 숫자 없는 재무 판단
