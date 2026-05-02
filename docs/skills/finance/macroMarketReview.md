---
title: 거시 시장 환경 점검
skillId: macroMarketReview
category: finance
---

# 거시 시장 환경 점검

금리, 환율, 경기, 유동성 질문을 기업 분석의 상위 맥락으로 연결한다.

## Metadata

- id: `macroMarketReview`
- category: `finance`
- kind: `curated`
- status: `unverified`
- Pyodide: `limited`

## When To Use

- 금리 환율 매크로
- 경기 사이클과 시장 동향
- 기업 분석 전에 거시 환경을 먼저 확인

## Capability Refs

- `macro`
- `Company.macro`
- `scan`
- `gather.macro`

## Required Evidence

- latestAsOf
- metric
- table
- basis

## Expected Outputs

- macro thesis
- 기준일
- 영향 경로
- 한계

## Runtime Compatibility

| runtime | status | notes |
|---|---:|---|
| `server` | `supported` |  |
| `localPython` | `supported` |  |
| `mcp` | `supported` |  |
| `webAi` | `limited` |  |
| `pyodide` | `limited` | live FRED, 환율, 금리 API 호출은 브라우저 CORS/인증 제약으로 제외한다. |

## Guide

## 절차

- macro와 관련 dataset 후보를 찾고 최신 관측일을 확인한다.
- 금리, 환율, 유동성, 지수 중 질문에 필요한 metric을 같은 기준일로 묶는다.
- 기업 질문이 함께 있으면 macro에서 섹터, Company, 재무로 이어지는 영향 경로를 제한적으로 연결한다.
- 데이터 기준일과 live API 미사용 한계를 답변에 남긴다.

## Forbidden

- 기준일 없는 최근 매크로 판단
- 데이터 없이 금리/환율 방향 단정
