---
title: Company.story capability view
skillId: capability:Company.story
category: capability
---

# Company.story capability view

공개 capability `Company.story`를 찾고 실행에 연결하기 위한 generated skill view.

## Metadata

- id: `capability:Company.story`
- category: `capability`
- kind: `generated`
- status: `observed`
- Pyodide: `unknown`

## When To Use

- 재무제표 구조화 보고서 — 기업이야기꾼의 대본 (내부 구현).
- When: 구조화된 보고서가 필요할 때. 사용자가 "보고서" 명시 시에만. How: 무인자 = 전체 보고서. section 으로 개별 섹션. type 으로 보고서 타입. "재무 검토서 만들어줘" -> c.story() "수익구조 분석" -> c.story("수익구조") "감사용 리뷰" -> c.story(preset="audit") "이 회사 스토리는?" -> c.story(template="auto") "요약만 보여줘" -> c.story(detail=False) "AI 가 해석한 보고서" -> dartlab.ask("005930 보고서 작성해줘") (AI 가 story tool 호출) Verified: credit 타입 → 신용 종합 보고서 (observed via credit ai-ask, 2026-04-25 — 정식 Phase P 판정 아님) audit 타입 → 분식회계 가능성 판정 보고서 (observed via ai-ask, 2026-04-25 — 정식 Phase P 판정

## Capability Refs

- `Company.story`

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
