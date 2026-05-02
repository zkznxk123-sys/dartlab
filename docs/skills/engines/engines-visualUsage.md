---
title: viz 엔진 표 기반 시각화 사용 지도
skillId: engines.visualUsage
category: engines
---

# viz 엔진 표 기반 시각화 사용 지도

검증된 표 evidence를 차트나 시각 설명으로 변환하는 절차를 설명한다.

## Metadata

- id: `engines.visualUsage`
- category: `engines`
- kind: `curated`
- status: `unverified`
- Pyodide: `supported`

## When To Use

- 표 기반 차트, 시계열 그래프, 비교 차트가 필요할 때
- analysis, scan, gather 결과를 시각화해야 할 때
- AI 답변에 chart ref와 table ref를 함께 남겨야 할 때

## Capability Refs

- `ChartResult`
- `Company.select`
- `Company.show`
- `scan`
- `gather`
- `analysis`

## Dataset Refs

- table.evidence

## Required Evidence

- table
- metric
- period
- series
- chartSpec

## Expected Outputs

- table-backed chart
- visual ref
- chart limitation note

## Runtime Compatibility

| runtime | status | notes |
|---|---:|---|
| `server` | `supported` |  |
| `localPython` | `supported` |  |
| `mcp` | `supported` |  |
| `webAi` | `limited` | 렌더링 대상 UI가 chart event를 지원해야 한다. |
| `pyodide` | `supported` | chart source table이 브라우저 메모리에 있어야 한다. |

## Guide

## 가능한 분석

- viz는 분석을 새로 만드는 엔진이 아니라 이미 검증된 표를 시각 설명으로 바꾸는 엔진이다.
- chart claim은 항상 source table ref와 함께 있어야 한다.

## 절차

- `basic.viz`, `visuals.tableBackedChart`, `ChartResult` capability를 확인한다.
- 먼저 분석/수집/스캔 엔진으로 chart source table을 만든다.
- table에 기간, series, metric이 충분한지 확인한다.
- ChartResult/viz로 chart spec을 만들고 visual ref를 남긴다.
- 최종 답변에는 chart가 어떤 table을 시각화했는지와 한계를 쓴다.

## Forbidden

- API parameters/returns를 SkillSpec에 중복하지 않는다.
- 표 evidence 없는 차트를 만들지 않는다.
