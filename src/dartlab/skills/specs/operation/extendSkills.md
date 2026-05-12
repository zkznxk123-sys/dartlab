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
- 신규 분석 skill 을 자율 발굴·검증으로 만드는 6 단계 사이클과 audit 회환은 [operation.skillDevelopmentLoop](/skills/operation.skillDevelopmentLoop) 가 SSOT (gapSpot → dataSanityCheck → protoSkill → selfRun → redTeam → graduate → auditFeedback). 본 skill 은 graduate 단계의 *승격 규칙* 만 정의한다.
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
- LLM 이 `ReadSkill` 검색 결과를 펼쳐볼 때 `purpose` 본문이 가장 먼저 보이고, 자연어 phrase 매칭이 단어 array (`whenToUse`) 보다 우선 hit.
- whenToUse 는 grep-style 인덱스이고, purpose trigger 는 LLM 의 의도 매칭에 직접 들어간다.

SCHEMA 변경 없음 — `purpose:` 본문 끝에 한 문장 추가만. `lastUpdated` 는 갱신.

신규 cadence recipe (dailyMorningNote · catalystCalendar · thesisTracker) 도 같은 규칙으로 작성.

기존 skill 일괄 audit 은 `scripts/dev/audit_trigger_phrases.py` (idempotent, dry-run 지원).

## 자동화 CLI — 1 명령 cascading

신규 엔진·axis·recipe 추가는 수동 5 단계 대신 1 명령 cascading CLI 우선:

```bash
# 새 엔진 (engines.{name})
uv run python -X utf8 scripts/dev/addEngine.py myEngine \
    --title "My Engine" \
    --purpose "myEngine 엔진은 ..."

# 새 axis · recipe 는 동일 패턴 (확장 예정)
```

`addEngine.py` 가 자동 산출:

- `src/dartlab/{name}/__init__.py` 스켈레톤 + `__all__`
- `src/dartlab/skills/specs/engines/{name}/SKILL.md` frontmatter 5 필수 + 3 강제 섹션 placeholder
- `validateSkills.py` + `generateSkills.py` 자동 호출

운영자 수동 잔여 (CLI 가 안내 출력):

1. `src/dartlab/__init__.py` re-export
2. `pyproject.toml [tool.importlinter]` contract 추가
3. `operation.architecture` L2 계층 표 1 줄
4. SKILL.md 3 강제 섹션 본문 채우기

`--dry-run` 으로 미리보기. axis / recipe / operation / start / runtime sub-spec 은 수동 4 단계 절차 ([skill-os-add](file://./.claude/skills/skill-os-add/SKILL.md)) 따름.

## 신규 frontmatter 필드 8 종 (Skill Graph 모델)

`SkillSpec` 에 다음 필드 추가됨 (모두 default 값, backward-compatible):

| 필드 | 타입 | 의미 |
|---|---|---|
| `predecessors` | `list[str]` | 본 skill 호출 전 거쳐야 할 skill id (역방향 successors) |
| `successors` | `list[str]` | 본 skill 후 자연 호출 후속 skill id (linkedSkills 의 의미 분리) |
| `audiences` | `dict[str, str]` | `{"llm": "...", "agent": "...", "human": "..."}` 주체별 한 줄 도입 |
| `isLeafNode` | `bool` | true 면 의도적 leaf — orphan lint 면제 |
| `entryHint` | `bool` | true 면 외부 LLM 첫 진입 후보 — MCP `start.*` 외 보강 |
| `graphTier` | `str` | L0~L4 계층 hint — 그래프 클러스터링 색상 |
| `cluster` | `str` | 자동 도출 외 수동 그룹핑 (e.g. `gather.history`) |
| `humanIntro` | `str` | 사람용 본문 도입 1~2 문단 (랜딩 페이지 상단 별도 영역) |

작성 가이드:

- `successors[]` · `predecessors[]` 는 *recipe* 의 linkedSkills 와 다르다 — recipe step 흐름이 아닌 일반 skill 간 후속 관계.
- `audiences[]` 3 키는 본문 directive (`:::for-llm` · `:::for-agent` · `:::for-human` · `:::end`) 와 함께 3 인덱스 분기 (mcp.json · agent.json · web.json) 에 사용.
- `isLeafNode: true` 는 자연스러운 종점 (e.g. `engines.gather.collect` 단순 호출) 만 — orphan 분류와 구분.

## 3 주체 인덱스 산출물

`scripts/build/generateSkills.py` 가 6 산출:

| 산출물 | 대상 | 크기 (skill 당) |
|---|---|---|
| `index.json` | 호환 alias (= agent.json) | ~500 토큰 |
| `agent.json` | 내부 AI 엔진 (dartlab.ask) | ~500 토큰 |
| `mcp.json` | 외부 LLM (MCP first hop) | < 300 토큰 |
| `web.json` | 사람 (랜딩) | ~1500 토큰 + humanIntro |
| `pyodide.json` | 브라우저 Pyodide | ~400 토큰 |
| `graph.json` | 그래프 시각화 (`/skills/graph`) | nodes + edges + cycles + orphans |

직접 편집 금지 — `scripts/build/generateSkills.py` 가 SSOT. 별도 commit "정리: 동기화" ([commit-self-change](file://./.claude/skills/commit-self-change/SKILL.md)).

