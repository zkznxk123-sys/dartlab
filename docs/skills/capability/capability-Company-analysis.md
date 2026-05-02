---
title: Company.analysis capability view
skillId: capability:Company.analysis
category: capability
---

# Company.analysis capability view

공개 capability `Company.analysis`를 찾고 실행에 연결하기 위한 generated skill view.

## Metadata

- id: `capability:Company.analysis`
- category: `capability`
- kind: `generated`
- status: `observed`
- Pyodide: `unknown`

## When To Use

- 재무제표 완전 분석 — 14축, 단일 종목 심층 (내부 구현).
- AI 역할: AI는 analysis를 단일 기업 재무·가치·리스크 해석 엔진으로 보고 axis/subaxis와 필요한 재무 evidence를 선택한다. When: 특정 종목의 재무 심층 분석이 필요할 때. How: axis 로 분석 영역, sub 로 세부 축 지정. "14축 분석 뭐가 있어?" → c.analysis() (가이드 반환) "수익구조 분석해줘" → c.analysis("financial", "수익구조") "안정성 분석" → c.analysis("financial", "안정성") "가치평가 해줘" → c.analysis("valuation", "가치평가") "매출전망" → c.analysis("forecast", "매출전망") Verified: 수익성 단독 → 마진 시계열 + 전환점 + 반도체 사이클 인과 (observed via ai-ask, 2026-04-25 — 정식 Phase P 판정 아님) 이익품질 + 재무정합성 → 분식회계 가능성 판정 (observed via

## Capability Refs

- `Company.analysis`

## Required Evidence

- sourceRef

## Expected Outputs

- capability-backed execution or limitation

## Runtime Compatibility

| runtime | status | notes |
|---|---:|---|
| `server` | `supported` |  |
| `localPython` | `supported` |  |
| `mcp` | `supported` |  |
| `webAi` | `limited` | 웹 AI는 Pyodide/HF snapshot 가능 범위에 따른다. |
| `pyodide` | `unknown` | Generated capability view는 API 사용법만 나타낸다.; Pyodide 가능 여부는 curated/user SkillSpec 또는 ops/pyodide.md를 확인한다. |

## Procedure

- capability ref의 공개 docstring/generated capability를 확인한다.
- 필요 입력과 반환 형태는 SkillSpec이 아니라 capability ref에서 읽는다.
- 실제 계산이나 조회 결과는 작업대 실행 결과 ref로 남긴다.

## Forbidden

- API parameters/returns를 SkillSpec에 중복하지 않는다.
