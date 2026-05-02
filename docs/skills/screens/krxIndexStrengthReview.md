---
title: KRX 지수 강세 분석
skillId: krxIndexStrengthReview
category: screens
---

# KRX 지수 강세 분석

런타임 KRX 지수 데이터에서 최신 관측일과 비교 기간을 확인하고 여러 지수의 상대 강세를 검토한다.

## Metadata

- id: `krxIndexStrengthReview`
- category: `screens`
- kind: `curated`
- status: `unverified`
- Pyodide: `limited`

## When To Use

- 최근 주가지수 강세를 묻는 질문
- 뜨는 지수, 강한 지수, 지수 랭킹 질문

## Capability Refs

- `gather`

## Dataset Refs

- krx.indices

## Required Evidence

- latestAsOf
- universe
- metric
- table

## Expected Outputs

- 강세 지수 후보
- 기준일과 기간
- 수치 표
- 한계

## Runtime Compatibility

| runtime | status | notes |
|---|---:|---|
| `server` | `supported` |  |
| `localPython` | `supported` |  |
| `mcp` | `supported` |  |
| `webAi` | `limited` |  |
| `pyodide` | `limited` | KRX API 실시간 호출은 CORS 때문에 사용하지 않는다.; 최신성은 HF에 업로드된 parquet의 BAS_DD 기준으로만 말한다. |

## Guide

## 절차

- RuntimeDatasetCatalog에서 KRX 지수 데이터셋 후보를 찾는다.
- `inspect_dataset`으로 날짜 컬럼, 지수명 컬럼, 가격/등락률 컬럼, 최신 관측일을 확인한다.
- `run_python`으로 최신일 기준 비교 가능한 지수별 수익률 또는 등락률 표를 계산한다.
- 강세 판단은 기준일, 기간, universe, metric이 모두 있는 표를 근거로 제한한다.
- visual은 지수별 비교 표가 있을 때만 만든다.

## Forbidden

- 기준 기간 없는 강세 단정
- 계산 없이 원하면 계산하겠다는 답변
