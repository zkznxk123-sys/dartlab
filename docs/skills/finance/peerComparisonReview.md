---
title: 동종 기업 비교 분석
skillId: peerComparisonReview
category: finance
---

# 동종 기업 비교 분석

둘 이상의 기업을 같은 metric, 같은 기간, 같은 기준으로 비교해 상대 우위와 한계를 판단한다.

## Metadata

- id: `peerComparisonReview`
- category: `finance`
- kind: `curated`
- status: `unverified`
- Pyodide: `limited`

## When To Use

- 삼성전자와 SK하이닉스 비교
- 두 기업 경쟁력 비교

## Capability Refs

- `Company.analysis`
- `Company.show`
- `Company.quant`
- `scan`

## Required Evidence

- target
- period
- metric
- table

## Expected Outputs

- 동일축 비교표
- 우위/열위 판단
- 데이터 누락 한계

## Runtime Compatibility

| runtime | status | notes |
|---|---:|---|
| `server` | `supported` |  |
| `localPython` | `supported` |  |
| `mcp` | `supported` |  |
| `webAi` | `limited` |  |
| `pyodide` | `limited` | 여러 종목 parquet를 브라우저 메모리에 올리므로 대상 수를 작게 유지한다.; live market/macro 보강은 서버 환경에서만 한다. |

## Guide

## 절차

- 각 대상의 식별 결과를 확인한다.
- 같은 metric과 기간을 가진 evidence를 대상별로 만든다.
- 한쪽만 있는 수치로 강한 비교 결론을 내지 않는다.
- 비교 표가 있으면 visual을 만든다.

## Forbidden

- 한쪽 수치만으로 우열 단정
