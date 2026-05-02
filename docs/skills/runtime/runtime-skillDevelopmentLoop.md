---
title: Skill 개발과 엔진 조합 루프
skillId: runtime.skillDevelopmentLoop
category: runtime
---

# Skill 개발과 엔진 조합 루프

기본 엔진 capability를 조합해 엔진에 직접 정의되지 않은 분석 절차를 만들고 audit 결과를 docstring 또는 SkillSpec 개선으로 되돌리는 체계다.

## Metadata

- id: `runtime.skillDevelopmentLoop`
- category: `runtime`
- kind: `curated`
- status: `unverified`
- Pyodide: `limited`

## When To Use

- 스킬 개발 체계
- 엔진 조합으로 새 분석 만들기
- 엔진에 없는 분석을 응용
- audit 결과를 skills에 반영
- 독스트링 보강 후보 찾기

## Capability Refs

- `Company`
- `Company.analysis`
- `Company.show`
- `Company.credit`
- `Company.quant`
- `gather`
- `scan`
- `macro`
- `quant`
- `ChartResult`

## Required Evidence

- skillRef
- capabilityRef
- auditResult
- failureMode

## Expected Outputs

- 반복 가능한 절차
- 필요한 capabilityRefs
- 승격 여부 판단

## Runtime Compatibility

| runtime | status | notes |
|---|---:|---|
| `server` | `supported` |  |
| `localPython` | `supported` |  |
| `mcp` | `supported` |  |
| `webAi` | `supported` |  |
| `pyodide` | `limited` | Pyodide에서는 live API가 필요한 조합을 서버 audit 없이 official로 승격하지 않는다. |

## Guide

## 절차

- 실패 또는 신규 질문을 목적어, 대상, 필요한 근거, runtime 제약으로 나눈다.
- 먼저 `search_reference`로 curated skill을 찾고, 없으면 `basic.company`, `basic.scan`, `basic.macro`, `basic.quant`, `basic.viz` 중 필요한 엔진 조합을 선택한다.
- 조합이 capability의 Guide/AIContract만으로 충분히 설명되면 docstring 보강 후보로 둔다. 여러 capability를 묶는 분석 절차가 필요하면 curated SkillSpec 후보로 둔다.
- 서버 경유 `/api/ask` audit에서 같은 skill이 반복 P를 받으면 `auditP` 후보가 된다. `official`은 구조 lint, 서버 audit P, 사용자 확인을 모두 만족할 때만 허용한다.
- public API 자체가 새 축을 요구할 정도로 반복되면 docstring Guide/AIContract 또는 공식 엔진 axis로 승격하고, 기존 SkillSpec은 새 capability id를 참조하도록 축소한다.

## Forbidden

- 질문별 실행 코드 저장
- 답변 템플릿 저장
- capability schema 중복
- 사용자 확인 없는 official 승격
