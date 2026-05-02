---
title: 데이터 가용성 확인
skillId: runtime.dataAvailabilityCheck
category: runtime
---

# 데이터 가용성 확인

분석 전에 dataset, Company topic, snapshot 최신성, 실행 가능 runtime을 확인한다.

## Metadata

- id: `runtime.dataAvailabilityCheck`
- category: `runtime`
- kind: `curated`
- status: `unverified`
- Pyodide: `supported`

## When To Use

- 데이터가 있는지 확인
- dataset 확인
- 최신 기준일 확인
- 분석 가능한 데이터 범위 점검

## Capability Refs

- `Company.index`
- `Company.topics`
- `gather`
- `scan`

## Required Evidence

- latestAsOf
- dataset
- metric

## Expected Outputs

- 데이터 있음/없음 판단
- 기준일
- 가능한 metric 목록
- 한계

## Runtime Compatibility

| runtime | status | notes |
|---|---:|---|
| `server` | `supported` |  |
| `localPython` | `supported` |  |
| `mcp` | `supported` |  |
| `webAi` | `supported` |  |
| `pyodide` | `supported` | live API 최신성은 서버 또는 로컬 Python 경로에서 확인한다. |

## Guide

## 절차

- 선택한 skill의 runtimeCompatibility와 datasetRefs를 먼저 확인한다.
- runtime dataset 또는 Company topic 목록에서 대상 데이터가 있는지 확인한다.
- date column, latestAsOf, entity column, metric 후보를 기록한다.
- 데이터가 없으면 필요한 수집 또는 prefetch 경로를 한계로 남긴다.
- 최신성 claim은 snapshot 기준일 또는 live 조회 기준일이 있을 때만 작성한다.

## Forbidden

- 데이터 확인 없이 최신이라고 말하기
- missing 값을 0으로 대체
