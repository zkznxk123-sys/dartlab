---
title: 미국 기업 EDGAR 분석
skillId: usEdgarCompanyReview
category: finance
---

# 미국 기업 EDGAR 분석

미국 ticker 또는 EDGAR 공시 질문을 Company, EDGAR filings, 재무 근거로 분석한다.

## Metadata

- id: `usEdgarCompanyReview`
- category: `finance`
- kind: `curated`
- status: `unverified`
- Pyodide: `limited`

## When To Use

- 미국 주식 분석
- EDGAR filings
- 10-K 10-Q 공시 확인
- AAPL NVDA TSLA 같은 ticker 질문

## Capability Refs

- `OpenEdgar`
- `Company.analysis`
- `Company.show`
- `Company.filings`
- `Company.liveFilings`
- `Company.readFiling`
- `Company.quant`

## Required Evidence

- target
- period
- metric
- table
- basis

## Expected Outputs

- filing-backed thesis
- 재무 근거 표
- 한계

## Runtime Compatibility

| runtime | status | notes |
|---|---:|---|
| `server` | `supported` |  |
| `localPython` | `supported` |  |
| `mcp` | `supported` |  |
| `webAi` | `limited` |  |
| `pyodide` | `limited` | SEC live API와 신규 filings 조회는 서버 또는 로컬 Python 경로에서 수행한다. |

## Guide

## 절차

- ticker를 식별하고 EDGAR Company 경로가 가능한지 확인한다.
- Company.analysis, show, filings capability를 찾아 재무와 공시 근거를 분리한다.
- filing claim은 접수일, form, 제목 또는 본문 ref에 묶는다.
- fiscal period가 있는 경우 calendar period와 혼동하지 않도록 기준을 밝힌다.

## Forbidden

- ticker 식별 없이 미국 기업 분석 시작
- EDGAR 근거 없는 10-K/10-Q 판단
