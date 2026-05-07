---
id: operation.extendSkills
title: Skill 확장과 공식 승격 규칙
kind: curated
scope: builtin
status: unverified
category: operation
purpose: 새 분석법, 운영 규칙, 외부 LLM 사용법을 Skills 체계에 추가하고 official 수준으로 승격하는 기준을 정한다.
whenToUse:
  - 새 skill을 추가할 때
  - 운영 규칙을 operation skill로 흡수할 때
  - user skill을 curated skill로 승격할 때
  - 반복 audit 결과를 docstring 또는 SkillSpec에 반영할 때
inputs:
  - 새 절차
  - sourceRef
  - audit result
  - 사용자 확인
outputs:
  - user skill
  - curated skill
  - docstring improvement
  - official promotion decision
sourceRefs:
  - dartlab://skills/operation.opsAsSkills
  - dartlab://skills/operation.code
  - dartlab://skills/operation.coreloop
requiredEvidence:
  - sourceRef
  - auditResult
  - userConfirmed
expectedOutputs:
  - 확장 위치 결정
  - 승격 가능 여부
  - 검증 체크리스트
runtimeCompatibility:
  server:
    status: supported
  localPython:
    status: supported
  mcp:
    status: supported
  webAi:
    status: supported
  pyodide:
    status: supported
failureModes:
  - 한 번 쓴 질문별 runner를 skill로 고정
  - 검증 없이 official 상태 부여
  - docstring에 있어야 할 API 능력을 SkillSpec에 중복
  - sourceRef 없는 운영 규칙 추가
forbidden:
  - final answer template 저장
  - API schema 복사
  - 사용자 확인 없는 official 승격
examples:
  - 새 운영 규칙을 operation skill로 추가하기
  - 반복 분석 절차를 curated skill로 승격하기
source:
  type: curated_markdown
  owner: dartlab
lastUpdated: "2026-05-07"
---

## 절차

- 새 내용이 엔진 API 능력이면 docstring/capability로 보강한다.
- 새 내용이 여러 엔진을 조합하는 분석 절차면 curated skill 후보로 둔다.
- 새 내용이 테스트, 릴리즈, 문서, UI, 데이터 같은 운영 규칙이면 operation skill로 둔다.
- 프로젝트별 실험은 `.dartlab/skills/**/*.md` user skill로 시작한다.
- official 승격은 구조 lint, 서버 audit P, 사용자 확인이 모두 있을 때만 허용한다.
- 승격 후에도 SkillSpec은 schema를 복사하지 않고 capabilityRefs와 sourceRefs로 원천을 연결한다.

## Trigger phrase 작성 규칙

`purpose:` 마지막 문장은 **trigger phrase** — 사용자가 자연어로 어떻게 부를지 1~3 가지 명시.

형식 (em dash `—` 사용 — colon 사용하면 YAML mid-value mapping 으로 해석돼 ScannerError):
```
purpose: ...절차 설명. 트리거 — '오늘 아침', '야간 공시 정리', 'morning note'.
```

원칙:
- 자연어 phrase (한국어 위주, 영문 보조 OK), 사용자가 채팅에 칠 만한 표현.
- 기존 `whenToUse:` array 와 *중복 OK* — `whenToUse` 는 검색 인덱스, `purpose` 끝 문장은 LLM 이 skill 카탈로그를 펼침 시 매칭하는 자연어.
- 1~3 개 — 너무 많으면 LLM 이 false positive 매칭. 가장 자주 칠 표현부터.
- 동의어 그룹 (예: "재무제표 비교 / 회사 비교 / 두 종목 차이") 은 같은 trigger 안에 묶어서.

이유:
- LLM 이 `read_skill` 검색 결과를 펼쳐볼 때 `purpose` 본문이 가장 먼저 보이고, 자연어 phrase 매칭이 단어 array (`whenToUse`) 보다 우선 hit.
- whenToUse 는 grep-style 인덱스이고, purpose trigger 는 LLM 의 의도 매칭에 직접 들어간다.

SCHEMA 변경 없음 — `purpose:` 본문 끝에 한 문장 추가만. `lastUpdated` 는 갱신.

신규 cadence recipe (dailyMorningNote · catalystCalendar · thesisTracker) 도 같은 규칙으로 작성.

기존 skill 일괄 audit 은 `scripts/dev/audit_trigger_phrases.py` (idempotent, dry-run 지원).

