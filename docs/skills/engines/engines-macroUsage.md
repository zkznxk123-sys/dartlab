---
title: macro 엔진 거시 환경 사용 지도
skillId: engines.macroUsage
category: engines
---

# macro 엔진 거시 환경 사용 지도

금리, 환율, 경기, 유동성 환경을 macro로 해석하고 기업/섹터 분석에 연결하는 절차를 설명한다.

## Metadata

- id: `engines.macroUsage`
- category: `engines`
- kind: `curated`
- status: `unverified`
- Pyodide: `limited`

## When To Use

- 금리, 환율, 경기, 유동성, 침체확률이 분석에 필요한 때
- 기업 분석 전에 시장 환경을 먼저 고정해야 할 때
- top-down 논제를 scan, analysis, credit로 이어갈 때

## Capability Refs

- `macro`
- `gather`
- `scan`
- `analysis`
- `credit`

## Dataset Refs

- macro.raw

## Required Evidence

- asOf
- metric
- period
- value
- direction

## Expected Outputs

- macro regime evidence
- top-down implication map
- company or sector follow-up plan

## Runtime Compatibility

| runtime | status | notes |
|---|---:|---|
| `server` | `supported` |  |
| `localPython` | `supported` |  |
| `mcp` | `supported` |  |
| `webAi` | `limited` | Web AI는 snapshot과 public macro provider 접근 가능성에 따른다. |
| `pyodide` | `limited` | 실시간 FRED/ECOS 접근과 장기 시계열은 서버 경유가 필요할 수 있다. |

## Guide

## 가능한 분석

- macro를 쓰면 기업 숫자를 경기, 금리, 유동성, 환율 환경 안에 배치할 수 있다.
- macro 단독은 시장 환경 설명이고, 투자 논제는 scan/analysis/credit과 조합해야 한다.

## 절차

- `basic.macro`와 `macro` capability에서 시장, axis, asOf 기준을 확인한다.
- 질문의 거시 축을 cycle/rates/liquidity/trade/fx/sentiment 중 하나 이상으로 분해한다.
- asOf와 지표 방향성을 evidence로 남긴다.
- 기업/섹터 질문이면 macro → scan → analysis/credit 순서로 연결한다.
- 최종 답변에는 거시 환경과 기업 고유 요인을 분리해 쓴다.

## Forbidden

- API parameters/returns를 SkillSpec에 중복하지 않는다.
- 거시 방향성만으로 종목 매수/매도 결론을 내지 않는다.
