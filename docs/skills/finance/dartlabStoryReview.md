---
title: DartLab 스토리형 분석
skillId: dartlabStoryReview
category: finance
---

# DartLab 스토리형 분석

여러 엔진의 근거를 thesis, evidence, risk, limit 구조로 조립한다.

## Metadata

- id: `dartlabStoryReview`
- category: `finance`
- kind: `curated`
- status: `unverified`
- Pyodide: `supported`

## When To Use

- 기업을 이야기처럼 종합해달라는 질문
- 보고서형 분석 요청

## Capability Refs

- `Company.story`
- `Company.analysis`
- `Company.credit`
- `Company.quant`

## Required Evidence

- target
- period
- metric

## Expected Outputs

- thesis
- evidence
- risk
- limits

## Runtime Compatibility

| runtime | status | notes |
|---|---:|---|
| `server` | `supported` |  |
| `localPython` | `supported` |  |
| `mcp` | `supported` |  |
| `webAi` | `limited` |  |
| `pyodide` | `supported` | 브라우저에서는 외부 API를 추가 호출하지 않고 prefetched parquet 기준으로만 작성한다. |

## Guide

## 절차

- story capability가 제공하는 report type과 한계를 확인한다.
- 필요한 하위 엔진 근거를 실행 결과로 확보한다.
- narrative는 숫자/날짜 claim ref를 가진 상태에서만 작성한다.

## Forbidden

- 검산 없는 서사형 투자판단
