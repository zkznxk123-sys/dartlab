---
title: analysis 엔진 재무 인과 사용 지도
skillId: engines.analysisUsage
category: engines
---

# analysis 엔진 재무 인과 사용 지도

단일 기업의 재무 원인, 가치, 전망, 리스크를 analysis 축 조합으로 해석하는 절차를 설명한다.

## Metadata

- id: `engines.analysisUsage`
- category: `engines`
- kind: `curated`
- status: `unverified`
- Pyodide: `limited`

## When To Use

- 수익성, 성장성, 안정성, 현금흐름, 가치평가를 원인까지 분석할 때
- 기업 재무제표의 변화 원인을 축별로 분해할 때
- story나 credit의 근거를 재무 축으로 보강할 때

## Capability Refs

- `analysis`
- `Company.analysis`
- `Company.show`
- `Company.trace`
- `scan`

## Dataset Refs

- dart.finance

## Required Evidence

- target
- axis
- metric
- period
- value
- table

## Expected Outputs

- axis-level financial evidence
- causal interpretation
- limits and missing data notes

## Runtime Compatibility

| runtime | status | notes |
|---|---:|---|
| `server` | `supported` |  |
| `localPython` | `supported` |  |
| `mcp` | `supported` |  |
| `webAi` | `limited` | Web AI는 finance-lite snapshot에서 가능한 축 위주로 실행한다. |
| `pyodide` | `limited` | 전체 서버 finance 축과 동일한 coverage를 보장하지 않는다. |

## Guide

## 가능한 분석

- analysis는 “무슨 숫자인가”보다 “왜 그렇게 변했는가”에 쓰는 엔진이다.
- 수익성, 현금흐름, 안정성, 자본배분, 가치평가를 조합하면 엔진에 단일 축으로 정의되지 않은 투자 논제도 만들 수 있다.

## 절차

- `basic.analysis`, `analysis`, `Company.analysis` capability를 먼저 확인한다.
- 질문을 재무 축으로 분해한다: 수익성/성장성/안정성/현금흐름/자본배분/가치평가/전망.
- target과 period를 고정하고 실제 축 결과를 실행해 표 evidence를 남긴다.
- 축 하나가 부족하면 보완 축을 추가한다. 예: 수익성은 비용구조, 현금흐름은 자본배분, 안정성은 credit.
- 최종 답변은 숫자, 기간, 단위, 인과 가정, 데이터 한계를 함께 남긴다.

## Forbidden

- API parameters/returns를 SkillSpec에 중복하지 않는다.
- 근거 축 없이 재무 원인 서사를 생성하지 않는다.
