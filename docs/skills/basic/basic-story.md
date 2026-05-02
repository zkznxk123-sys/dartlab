---
title: story 보고서 조합 엔진
skillId: basic.story
category: basic
---

# story 보고서 조합 엔진

DartLab `story` 엔진의 역할과 capability 묶음을 찾기 위한 generated basic engine skill.

## Metadata

- id: `basic.story`
- category: `basic`
- kind: `generated`
- status: `observed`
- Pyodide: `unknown`

## When To Use

- AI는 story를 검증된 engine output을 보고서 섹션으로 조립하는 엔진으로 보고 원자료 없이 새 claim을 만들지 않는다.
- 보고서 조합기 — 6 엔진 블록을 조합하여 6막 구조화 보고서 생성. / AI 역할: AI는 story를 검증된 engine output을 보고서 섹션으로 조립하는 엔진으로 보고 원자료 없이 새 claim을 만들지 않는다. When: 종목의 종합 분석 보고서가 필요할 때. How: 11 타입 중 선택 — full(전체), executive(경영진 요약), credit(신용), valuation(가치평가), growth(성장), crisis(위기), audit(감사
- 재무제표 구조화 보고서 — 기업이야기꾼의 대본 (내부 구현). / When: 구조화된 보고서가 필요할 때. 사용자가 "보고서" 명시 시에만. How: 무인자 = 전체 보고서. section 으로 개별 섹션. type 으로 보고서 타입. "재무 검토서 만들어줘" -> c.story() "수익구조 분석" -> c.story("수익구조") "감사용 리뷰" -> c.story(preset="audit") "이 회사 스토리는?" -> c.story(template=
- Damodaran 3P — possible(낙관)/plausible(중도)/probable(보수) 3 DCF + 민감도. / "3 시나리오 가치" → c.storyTree() "서사 민감도" → c.storyTree()['summary']['spreadPct']

## Capability Refs

- `Story`
- `Company.story`
- `Company.storyTree`

## Expected Outputs

- engine AI role
- engine capability map
- capability-backed evidence refs

## Runtime Compatibility

| runtime | status | notes |
|---|---:|---|
| `server` | `supported` |  |
| `localPython` | `supported` |  |
| `mcp` | `supported` |  |
| `webAi` | `limited` | 실제 실행 가능 여부는 연결된 capability와 dataset skill을 함께 확인한다. |
| `pyodide` | `unknown` | 엔진 지도 자체는 조회 가능하다. 실행 가능 여부는 조합되는 skill과 capability별 runtimeCompatibility를 따른다. |

## Procedure

- AI 역할: AI는 story를 검증된 engine output을 보고서 섹션으로 조립하는 엔진으로 보고 원자료 없이 새 claim을 만들지 않는다.
- 이 skill은 엔진 능력 지도다. API 상세는 capabilityRefs의 docstring/generated capability에서 확인한다.
- 필요 입력, 반환 형태, 단위, 실제 반환 키를 이 skill에 중복하지 않는다.
- 분석 중 생성한 숫자·날짜·표·한계는 ref로 남겨 최종 답변 검산에 연결한다.

## Forbidden

- API parameters/returns/unit/actual return keys를 SkillSpec에 중복하지 않는다.
- workbench tool 사용법을 basic engine skill에 넣지 않는다.
