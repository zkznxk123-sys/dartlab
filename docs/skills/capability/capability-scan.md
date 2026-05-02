---
title: scan capability view
skillId: capability:scan
category: capability
---

# scan capability view

공개 capability `scan`를 찾고 실행에 연결하기 위한 generated skill view.

## Metadata

- id: `capability:scan`
- category: `capability`
- kind: `generated`
- status: `observed`
- Pyodide: `unknown`

## When To Use

- 축(axis)별 전종목 횡단분석.
- AI 역할: AI는 scan을 전종목 횡단 비교와 스크리닝 엔진으로 보고 universe, metric, 기간, rank 근거를 만든다. When: 특정 종목 심층 분석 전, 업종·시장 내 상대 위치를 파악할 때. How: scan 으로 전체 분포를 보고 → analysis 로 개별 종목 심층 분석. story credit/governance/audit 타입에서 scan 데이터를 동종업계 비교로 활용. 조건형 종목 발굴은 scan("fields") → scan("screen", spec=...) → Company/analysis 순서. 단일 지표 하나만으로 후보 추천을 끝내지 말고 finance/report/docs/krx 중 최소 3관점 교차 검증. Verified: scan("재무건전성") → 업종 비교 테이블, 해석 약간 부족 (observed weak via ai-ask, 2026-04-25 — 정식 Phase 판정 아님) See Also analysis : 개별 종목 재무

## Capability Refs

- `scan`

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
