---
title: 전종목 횡단면 주가 스크리닝
skillId: crossSectionStockScreen
category: screens
---

# 전종목 횡단면 주가 스크리닝

런타임 시장 데이터에서 종목 universe와 최신 관측일을 확인한 뒤 조건에 맞는 종목 후보군을 만든다.

## Metadata

- id: `crossSectionStockScreen`
- category: `screens`
- kind: `curated`
- status: `unverified`
- Pyodide: `limited`

## When To Use

- 최근 많이 오른 종목을 찾는 질문
- 전종목에서 특정 조건을 만족하는 종목 검색

## Capability Refs

- `gather`
- `scan`

## Dataset Refs

- krx.prices

## Required Evidence

- latestAsOf
- universe
- metric
- table

## Expected Outputs

- 후보 종목 표
- 기준일/기간/metric
- 한계

## Runtime Compatibility

| runtime | status | notes |
|---|---:|---|
| `server` | `supported` |  |
| `localPython` | `supported` |  |
| `mcp` | `supported` |  |
| `webAi` | `limited` |  |
| `pyodide` | `limited` | KRX API 실시간 호출은 CORS 때문에 사용하지 않는다.; finance-lite에는 주요 계정만 있어 전체 scan과 동일하지 않다. |

## Guide

## 절차

- RuntimeDatasetCatalog에서 KRX 가격 또는 종목 데이터셋 후보를 찾는다.
- `inspect_dataset`으로 종목코드, 종목명, 날짜, 가격/거래대금/등락률 컬럼을 확인한다.
- `run_python`으로 동일 기준의 횡단면 표를 만든다.
- 표의 기준일, 기간, universe, metric을 답변에 함께 밝힌다.

## Forbidden

- 데이터 기준일 없이 최근이라고 말하기
- 단일 종목만 보고 전종목 결론 내기
