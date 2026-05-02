---
title: credit 신용 분석 엔진
skillId: basic.credit
category: basic
---

# credit 신용 분석 엔진

DartLab `credit` 엔진의 역할과 capability 묶음을 찾기 위한 generated basic engine skill.

## Metadata

- id: `basic.credit`
- category: `basic`
- kind: `generated`
- status: `observed`
- Pyodide: `unknown`

## When To Use

- AI는 credit을 상환능력·재무건전성 판단 엔진으로 보고 부채, 현금흐름, 이자보상, 만기 근거를 요구한다.
- 신용등급 산출 단일 진입점. / AI 역할: AI는 credit을 상환능력·재무건전성 판단 엔진으로 보고 부채, 현금흐름, 이자보상, 만기 근거를 요구한다. When: 종목의 부도 위험·재무 건전성을 독립 평가할 때. How: credit 단독으로 종합 등급 확인 → analysis(안정성, 현금흐름) 와 함께 심층 진단. story credit 타입이 credit + analysis(안정성) + analysis(현금흐름)
- 독립 신용평가 — dCR 20단계 등급 (내부 구현). / When: 부도 위험·신용등급·채무상환능력 판단이 필요할 때. How: 무인자 호출로 종합 등급, axis 로 개별 축, detail=True 로 시계열. Verified: credit 단독 → dCR 등급 + 7축 위험점수 분해 + PD 추정 (observed via ai-ask, 2026-04-25 — 정식 Phase P 판정 아님) credit + analysis(안정성,현금흐름) →

## Capability Refs

- `credit`
- `Company.credit`

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

- AI 역할: AI는 credit을 상환능력·재무건전성 판단 엔진으로 보고 부채, 현금흐름, 이자보상, 만기 근거를 요구한다.
- 이 skill은 엔진 능력 지도다. API 상세는 capabilityRefs의 docstring/generated capability에서 확인한다.
- 필요 입력, 반환 형태, 단위, 실제 반환 키를 이 skill에 중복하지 않는다.
- 분석 중 생성한 숫자·날짜·표·한계는 ref로 남겨 최종 답변 검산에 연결한다.

## Forbidden

- API parameters/returns/unit/actual return keys를 SkillSpec에 중복하지 않는다.
- workbench tool 사용법을 basic engine skill에 넣지 않는다.
