---
title: 저평가·수익성 종목 후보 찾기
skillId: screens.findUndervaluedQualityStocks
category: screens
---

# 저평가·수익성 종목 후보 찾기

scan과 재무 prebuild를 이용해 밸류에이션이 낮고 수익성 근거가 있는 후보 종목을 횡단면으로 찾는다.

## Metadata

- id: `screens.findUndervaluedQualityStocks`
- category: `screens`
- kind: `curated`
- status: `unverified`
- Pyodide: `limited`

## When To Use

- 스캔엔진으로 저평가 종목 찾기
- 저평가이면서 수익성 좋은 종목
- value quality screen

## Capability Refs

- `scan`
- `Company.analysis`

## Dataset Refs

- dart.scan.financeLite

## Required Evidence

- universe
- metric
- table
- basis

## Expected Outputs

- 저평가 후보 표
- 수익성 보조 지표
- 한계

## Runtime Compatibility

| runtime | status | notes |
|---|---:|---|
| `server` | `supported` |  |
| `localPython` | `supported` |  |
| `mcp` | `supported` |  |
| `webAi` | `limited` |  |
| `pyodide` | `limited` | full scan 축 전체가 아니라 prebuild에 포함된 지표 기준 후보만 만든다. |

## Guide

## 절차

- `engines.scanUsage`와 `basic.scan`으로 가능한 횡단면 축을 확인한다.
- valuation metric과 profitability metric이 같은 universe와 기준일에서 있는지 확인한다.
- `run_python`으로 후보 표를 만들고 value metric만 아니라 profitability 보조 지표를 같이 둔다.
- 낮은 valuation은 후보 조건이지 최종 투자 판단이 아니라고 한계를 남긴다.

## Forbidden

- 후보 종목을 매수 추천으로 단정
- universe와 기준일 없는 ranking
