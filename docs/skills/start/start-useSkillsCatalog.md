---
title: Skill catalog 기반 작업 시작
skillId: start.useSkillsCatalog
category: start
---

# Skill catalog 기반 작업 시작

DartLab 코드 전체를 읽기 전에 skills catalog만 보고 목적 skill, capability, 근거 요구사항을 찾는 시작 절차다.

## Metadata

- id: `start.useSkillsCatalog`
- category: `start`
- kind: `curated`
- status: `unverified`
- Pyodide: `supported`

## When To Use

- dartlab skills 어떻게 써
- dartlab 뭐 할 수 있어
- dartlab 기능과 가능한 분석
- 스킬만 보고 시작
- 외부 AI가 DartLab 기능을 찾기
- 목적 기반 capability 검색
- show 함수 사용법

## Capability Refs

- `Company`
- `Company.show`
- `Company.analysis`
- `gather`
- `scan`
- `macro`
- `quant`
- `ChartResult`
- `ask`

## Required Evidence

- skillRef

## Expected Outputs

- 목적 skill 후보
- capability ref 목록
- 실행 전 확인할 evidence 목록

## Runtime Compatibility

| runtime | status | notes |
|---|---:|---|
| `server` | `supported` |  |
| `localPython` | `supported` |  |
| `mcp` | `supported` |  |
| `webAi` | `supported` |  |
| `pyodide` | `supported` | 실제 분석 실행 가능 여부는 선택한 skill의 runtimeCompatibility를 따른다. |

## Guide

## 절차

- 사용자 질문을 그대로 skill 검색어로 사용해 curated skill을 먼저 찾는다.
- "뭐 할 수 있어", "기능", "사용법", "함수" 질문은 데이터셋보다 skill/capability ref를 먼저 근거로 삼는다.
- 사용법 답변은 코드 예시를 최소화하고, 숫자·날짜가 필요한 실행 claim처럼 보이지 않게 capability ref를 근거로 설명한다.
- 검색 결과가 generic `basic.*`뿐이면 질문의 목적어를 더 좁혀 다시 검색한다.
- 선택한 skill의 `capabilityRefs`, `requiredEvidence`, `runtimeCompatibility`를 읽는다.
- API 인자와 반환 구조는 capability view 또는 docstring에서 확인한다.
- 실행 전에는 어떤 ref를 만들어야 하는지 목록으로 고정한다.

## Forbidden

- SkillSpec에 없는 API schema를 추측
- capabilityRefs 확인 없이 실행 코드 작성
