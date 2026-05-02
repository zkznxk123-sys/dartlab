---
title: industry 엔진 산업맥락 사용 지도
skillId: engines.industryUsage
category: engines
---

# industry 엔진 산업맥락 사용 지도

기업 지표를 산업 공정, 밸류체인, peer 맥락과 연결하는 절차를 설명한다.

## Metadata

- id: `engines.industryUsage`
- category: `engines`
- kind: `curated`
- status: `unverified`
- Pyodide: `limited`

## When To Use

- 기업을 산업 밸류체인 안에서 해석해야 할 때
- 같은 업종 peer나 공정별 위치가 필요한 때
- macro나 scan 결과를 산업 driver와 연결해야 할 때

## Capability Refs

- `industry`
- `Company.industry`
- `scan`
- `analysis`
- `macro`

## Dataset Refs

- industry.taxonomy
- dart.finance

## Required Evidence

- industry
- stage
- peer
- target
- table

## Expected Outputs

- value-chain context
- peer/stage table
- company-to-industry bridge

## Runtime Compatibility

| runtime | status | notes |
|---|---:|---|
| `server` | `supported` |  |
| `localPython` | `supported` |  |
| `mcp` | `supported` |  |
| `webAi` | `limited` | taxonomy 조회는 가능하나 summary/timeline은 finance coverage에 좌우된다. |
| `pyodide` | `limited` | 공정별 재무 summary는 finance snapshot coverage를 따른다. |

## Guide

## 가능한 분석

- industry를 쓰면 개별 기업 숫자를 업종, 공정, 밸류체인 위치와 연결할 수 있다.
- scan이 “시장 전체 분포”라면 industry는 “왜 이 기업을 이 peer와 비교하는가”를 설명한다.

## 절차

- `basic.industry`와 `industry` capability에서 가능한 산업/공정 범위를 확인한다.
- target 기업의 산업과 stage를 확인한다.
- peer/stage table을 evidence로 남긴 뒤 scan/analysis 지표와 연결한다.
- macro 환경을 다룰 때는 산업 driver를 거쳐 기업 영향으로 내려온다.
- 최종 답변에는 산업 맥락과 기업 고유 지표를 분리한다.

## Forbidden

- API parameters/returns를 SkillSpec에 중복하지 않는다.
- 산업명만으로 기업 실적 원인을 단정하지 않는다.
