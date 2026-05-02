---
title: 기업 분석 시작 라우터
skillId: companyResearchStarter
category: finance
---

# 기업 분석 시작 라우터

종목 또는 기업 질문을 받았을 때 어떤 분석 skill과 capability로 시작할지 결정한다.

## Metadata

- id: `companyResearchStarter`
- category: `finance`
- kind: `curated`
- status: `unverified`
- Pyodide: `limited`

## When To Use

- 종목 분석 어떻게 시작
- 기업 분석 시작
- 삼성전자 분석 첫 단계
- ticker 분석 첫 단계

## Capability Refs

- `Company.analysis`
- `Company.show`
- `Company.credit`
- `Company.quant`
- `Company.story`
- `macro`
- `scan`
- `industry`

## Required Evidence

- target
- skillRef
- period

## Expected Outputs

- 분석 skill 선택
- 필요한 capabilityRefs
- 근거 체크리스트

## Runtime Compatibility

| runtime | status | notes |
|---|---:|---|
| `server` | `supported` |  |
| `localPython` | `supported` |  |
| `mcp` | `supported` |  |
| `webAi` | `limited` |  |
| `pyodide` | `limited` | live filings, macro 보강, 신규 수집은 서버 또는 로컬 Python 경로에서 수행한다. |

## Guide

## 절차

- 기업명, 종목코드, ticker 중 무엇이 입력됐는지 먼저 식별한다.
- 질문 목적이 수익성, 현금흐름, 신용, 공시, 비교, 밸류에이션, 배당, 지배구조 중 어디에 가까운지 skill 검색으로 고른다.
- 목적이 불명확하면 companyCausalReview를 기본 후보로 두되, macro와 scan 맥락도 함께 확인한다.
- 선택한 skill의 requiredEvidence를 실행 전 체크리스트로 둔다.
- 첫 답변은 강한 결론보다 데이터 가능 범위와 다음 실행 계획을 먼저 확정한다.

## Forbidden

- 근거 없는 투자판단
- Company 편의성 원칙을 dartlab 전체 사상으로 오해
