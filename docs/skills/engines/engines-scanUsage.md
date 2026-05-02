---
title: scan 엔진 사용 지도
skillId: engines.scanUsage
category: engines
---

# scan 엔진 사용 지도

전종목 횡단면 분석에서 scan 엔진으로 후보 발굴, peer 비교, 시장 분포 확인을 수행하는 절차를 설명한다.

## Metadata

- id: `engines.scanUsage`
- category: `engines`
- kind: `curated`
- status: `unverified`
- Pyodide: `limited`

## When To Use

- 스캔엔진으로 어떤 종목을 찾을 수 있나
- 횡단면 조건 검색
- 시장 전체에서 rank, percentile, peer 위치를 확인할 때

## Capability Refs

- `scan`
- `Company.analysis`
- `Company.credit`
- `Company.industry`

## Required Evidence

- universe
- metric
- table
- rank
- period

## Expected Outputs

- screened candidate table
- peer comparison evidence
- follow-up company analysis plan

## Runtime Compatibility

| runtime | status | notes |
|---|---:|---|
| `server` | `supported` |  |
| `localPython` | `supported` |  |
| `mcp` | `supported` |  |
| `webAi` | `limited` | finance-lite prebuild와 Web scan runtime 범위에서 가능하다. |
| `pyodide` | `limited` | 전체 서버 scan과 동일한 축을 보장하지 않는다. |

## Guide

## 절차

- `basic.scan`과 `scan` capability를 먼저 확인한다.
- 사용자가 찾는 후보가 가격/재무/공시/업종/신용/산업 중 어느 축인지 확인한다.
- RuntimeDatasetCatalog 또는 scan capability에서 가능한 universe와 metric을 확인한다.
- `run_python`으로 횡단면 표를 만들고 기준일, universe, metric을 함께 남긴다.
- 후보는 투자 결론이 아니라 추가 분석 대상이라고 표시한다.
- 후속 분석은 Company, analysis, credit, industry 중 질문 의도에 맞는 엔진으로 이어간다.

## Forbidden

- universe 없는 횡단면 결론
- API parameters/returns를 SkillSpec에 중복하지 않는다.
