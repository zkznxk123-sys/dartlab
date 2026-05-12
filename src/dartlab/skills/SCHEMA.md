# Skill SSOT 작성 규약

> 본 문서는 `src/dartlab/skills/specs/**/*.md` 에 새 skill 을 추가하거나 기존 skill 의 frontmatter 를 갱신할 때 참고하는 운영자 가이드. **수동 SSOT 정책** 위에서 동작 — capability/docstring 으로부터 자동 생성하지 않는다.
>
> **자동 산출물 6 종** (빌드 시점 `scripts/build/generateSkills.py` 가 갱신):
> - `index.json` — 기존 다운스트림 호환 (agent.json alias).
> - `agent.json` — 내부 AI 엔진 용 (frontmatter + bodyPreview).
> - `mcp.json` — 외부 LLM (MCP) 용 경량 (5 핵심 필드 + nextSkills max 5).
> - `web.json` — 사람 (랜딩) 용 풍부 (humanIntro · visualRefs · bodyHuman).
> - `pyodide.json` — Pyodide 런타임 manifest.
> - `graph.json` — 257 노드 + 1337 엣지 + cycle/orphan/unreachable 메타.
>
> `llms.txt` · `sitemap.xml` 은 별도 `scripts/build/generateSpec.py` 책임.

## 1. 4 카테고리 + 디렉토리

| 카테고리 | 위치 | 의미 |
|---|---|---|
| `start` | `specs/start/{name}.md` | 첫 진입 (DartLab Skill OS, install, catalog 사용) |
| `runtime` | `specs/runtime/{name}.md` | 실행 환경 (Pyodide, MCP, Web AI, Local Python, VSCode) |
| `operation` | `specs/operation/{name}.md` | 운영 규칙 (philosophy, code, apiContract, architecture, testing) |
| `engines` | `specs/engines/{group}/SKILL.md` (기본) + `specs/engines/{group}/{axis}.md` (응용) | 엔진별 기본 사용법 + 응용 실행 스킬 |

엔진 응용 스킬의 `id` 는 `engines.{group}.{axis}` 형식 (예: `engines.analysis.cashflow`). 기본 스킬은 `engines.{group}` (예: `engines.company`).

## 2. frontmatter 필드

### 필수 (검증 게이트)

| 필드 | 타입 | 설명 |
|---|---|---|
| `id` | `string` | 점-분리 (`category.name` 또는 `engines.group.axis`). 다른 곳에서 참조하는 표준 식별자. |
| `title` | `string` | 사람이 읽는 짧은 제목. 카드·헤더에 노출. |
| `category` | `start` \| `runtime` \| `operation` \| `engines` | 카테고리 태그. |
| `purpose` | `string` | 1~2 문장. 이 skill 이 무엇을 하는지. 카드 미리보기·메타 디스크립션·llms.txt 에 직접 노출. |
| `whenToUse` | `string[]` | 어떤 질문/작업에 매칭되는 키워드. 검색·필터의 핵심. 비어있지 않게. |

### lint 강제 (게이트 통과 필수) — `src/dartlab/skills/registry.py::lintSkill`

| 필드 | 강제 조건 | 차단 |
|---|---|---|
| `runtimeCompatibility.pyodide` | `kind="curated"` skill 은 반드시 선언 | `_validateRuntimeCompatibility` 가 ValueError |
| `capabilityRefs[]` | 등록된 capability id 만 | `_validateCapabilityRefs:577-583` 가 ValueError |
| `id` 점 분리 | `category.name` 또는 `engines.group.axis` | `validateSkills.py` |
| `purpose` · `title` | 비어있지 않음 | `lintSkill:202-203` |
| (engines 카테고리) 본문 강제 섹션 3 종 | `## 공개 호출 방식` · `## 호출 동작` · `## 대표 반환 형태` | `_validateExecutionSkillContract` |

### Graph lint (phase 1 warn-only, phase 2-3 차단 예정) — `src/dartlab/skills/graphLint.py`

| 필드 | 검증 | 정책 |
|---|---|---|
| `knowledgeRefs[]` · `sourceRefs[]` · `toolRefs[]` · `datasetRefs[]` | id 가 listSkills 셋에 존재 | phase 1 warn / phase 2 신규 차단 |
| `successors[]` · `predecessors[]` | 양방향 일관성 | phase 2 부터 |
| `linkedSkills[]` cycle | 3+ 노드 SCC | phase 2 부터 |
| in-degree 0 + entry 아님 | `isLeafNode: true` 명시 권장 | warn-only |

### 권장 (`/skills/[id]` 페이지가 명시 섹션으로 렌더)

| 필드 | 타입 | 페이지 렌더 위치 |
|---|---|---|
| `procedure` | `string[]` | 우측 상단 `<ProcedureStepper>` numbered card stepper. **빈 배열이면 섹션 자체가 안 뜬다 — 채우면 절차감이 강해진다.** |
| `examples` | `string[]` | `<UsageExamples>` — 어떤 질문일 때 이 skill 을 쓰는지. |
| `expectedOutputs` | `string[]` | `<EvidenceChecklist title="기대 결과" kicker="출력">`. |
| `requiredEvidence` | `string[]` | 좌측 메타 카드의 chip 배열. 답변에 묶어야 할 evidence 종류. |
| `failureModes` | `string[]` | `<DoNotDo>` 의 "흔한 실패" 블록. |
| `forbidden` | `string[]` | `<DoNotDo>` 의 "절대 금지" 블록. |
| `runtimeCompatibility` | `Record<env, {status, notes?, limitations?}>` | `<RuntimeMatrix>` 5 환경 표. |
| `inputs` / `outputs` | `string[]` | 구조화된 입출력. 좌측 메타 카드. |
| `capabilityRefs` / `apiRefs` / `toolRefs` | `string[]` | 코드 원천. |
| `knowledgeRefs` | `string[]` | 다른 skill id (예: `engines.company`) — **참조용** (읽으면 도움). 클릭 가능한 chip 으로 링크. |
| `linkedSkills` | `string[]` | 다른 skill id — **실행 절차의 일부** (recipe 가 순서대로 거치는 step). `knowledgeRefs` 와 의미 분리. `kind: recipe` 에서 핵심. |
| `predecessors` / `successors` | `string[]` | 작업 흐름 path — 이전/다음 단계. graph 빌드 시 양방향 자동 도출. recipe 외 sub-spec 의 진입 path 명시. |
| `audiences` | `dict[str, str]` | 본문 주체별 분기 — `llm` / `agent` / `human` 키 → 짧은 한글 설명. mcp.json/web.json 빌드 시 매핑. |
| `isLeafNode` | `bool` | True 면 *의도적 leaf* — orphan warn 면제. |
| `entryHint` | `bool` | True 면 진입 노드 — graph 시각화에서 강조. |
| `graphTier` · `cluster` | `string` | graph 시각화 그룹화 키 (선택). 기본 cluster = engines.{group} 또는 category. |
| `humanIntro` | `string` | 사람용 도입 1~2 문단 — web.json 의 `bodyHuman` 또는 별도 필드로 노출. |
| `sourceRefs` | `string[]` | `dartlab://skills/{id}` 형식의 표준 출처. |
| `status` | `observed` \| `unverified` \| `archived` | 검증 상태. 카드 배지. |
| `lastUpdated` | `YYYY-MM-DD` | 본문 변경 날짜. 운영자 수동 갱신. |

### 옵셔널 (사람용 슬롯)

| 필드 | 타입 | 의미 |
|---|---|---|
| `image` | `string` | 헤더 커버 이미지. `landing/static/skills/{id}/cover.{png,webp,svg}` 패턴. 없으면 카테고리별 placeholder. |
| `humanIntro` | `string` | 도입 1~2 문단 (사람용 톤). 페이지에서만 노출, AI 인덱싱 우선순위 낮음. |

## 3. 본문 구조

frontmatter 아래 본문은 mdsvex 가 렌더한다. Shiki 코드 하이라이트 + 카테고리 색상 (start blue · runtime purple · operation green · engines orange) 적용됨. `./assets/foo.png` 상대경로는 `/skills/assets/foo.png` 으로 자동 변환.

### 3.1. engine skill — 강제 섹션 (lint 게이트)

`category: engines` 인 skill 은 `dartlab.skills.registry` 의 `_validate_execution_skill_contract` 가 다음 3 개 섹션 제목을 본문에서 강제한다. 빠지면 `generateSkills.py` 가 `ValueError: engine skill {id} missing execution sections` 로 실패.

- `## 공개 호출 방식` — Python 코드블록. 사용자가 그대로 복사해 실행할 수 있는 호출 예.
- `## 호출 동작` — 입력 / 출력 / 에러 동작 산문. 어떤 인자를 받고 어떤 결과를 어떻게 반환하는지.
- `## 대표 반환 형태` — 표 또는 구조 텍스트로 반환 DataFrame / dict 구조 명시.

추가로 권장 (강제 아님):
- `## 엔진 역할` — 본문 도입 1~2 문단.
- `## evidence 기준` — `requiredEvidence[]` 의 각 항목 의미.
- `## 기본 실행 순서` — 사용 절차 numbered list.
- `## 기본 검증` — 검증 게이트.

### 3.2. recipe skill — 본문 5 단 분석 구조 (권장)

`category: recipes` 인 skill 은 *여러 engine 을 조합하는 깊은 분석 절차* 다. 단순 출력 형태 (mermaid 한 개, 표 한 개) 만 명세하지 말고, 답변 본문이 그대로 5 단 구조로 작성되도록 다음 섹션을 채운다. 시스템 프롬프트의 분석 답변 5 단 (결론/근거/메커니즘/반례·한계/후속 모니터링) 과 1:1 매핑.

강제 (registry 검증): `## 연계 절차` 1 개 — 다른 skill 연결 단계.

권장 (본문 깊이 표준):

- `## 공개 호출 방식` — Python 코드블록. 사용자가 복사 실행 가능한 호출 예. *5 단 답안 산출* 가능한 구조여야 한다.
- `## 호출 동작` — 5 단 분석 구조로 다음 sub-heading 강제:
    - `### 1. 결론 도출` — 어떤 정량 한 문장 결론을 산출하는지 (예: "회사 X 의 신용 충격 민감도 = β 1.8 ± 0.3").
    - `### 2. 핵심 근거 수집` — 어떤 ref (skillRef/sourceRef/executionRef) 3 개 이상을 모으는지. 출처 + 수치 + 시점 명시.
    - `### 3. 메커니즘 분석` — 인과 경로 (mermaid graph LR 또는 단계별 bullet). 노드에 *수치 임계* 부착 권장.
    - `### 4. 반례·한계` — 결론이 깨지는 조건 / 데이터 noise / 측정 보수성.
    - `### 5. 후속 모니터링` — 다음 turn 에 추적할 지표 + 임계값 2~3 개.
- `## 대표 반환 형태` — 표 또는 구조 텍스트로 반환 dict / DataFrame 구조 명시.
- `## 연계 절차` — 다른 skill 로 이어지는 단계 (linkedSkills 와 정합).
- `## 기본 검증` — 검증 게이트.

### 3.3. 그 외 카테고리 (start · runtime · operation) — 권장 섹션

강제 섹션 없음. 자유로운 본문 구조. 권장:
- `## 절차` 또는 `## 무엇을 하나` — 본문 도입.
- `## 공개 호출 방식` (있으면) — 코드블록.
- `## 다음 단계` — 관련 skill 링크 (반드시 절대 path `/skills/{id}` 형식).

### 3.3. 내부 링크는 절대 path

skill 사이 링크는 항상 `[title](/skills/{id})` 절대 path 로 박는다. relative path (`(SKILL)`, `(../start/quickStart)`) 는 prerender 시 `/skills/SKILL` 같은 잘못된 URL 로 해석되어 빌드 실패.

본문 헤더 (`h1`/`h2`/`h3`) 는 `/skills/[id]` 페이지의 좌측 TOC 자동 추출 대상.

## 4. 새 skill 추가 절차

1. 카테고리 결정 (4 개 중 하나).
2. `src/dartlab/skills/specs/{category}/{name}.md` 생성. 엔진 응용은 `specs/engines/{group}/{axis}.md`.
3. 위 §2 의 필수 필드 5 개 + 권장 필드 채우기. `procedure[]` · `examples[]` 비워두기보다 1~2 개라도 채우기 (페이지 풍부도).
4. 본문 산문 작성 (§3 권장 구조).
5. 인덱스 빌드: `uv run python -X utf8 scripts/build/generateSkills.py`. `index.json` · `pyodide.json` 갱신.
6. 검증: `uv run python -X utf8 scripts/build/validateSkills.py src/dartlab/skills/specs/{category}/{name}.md`.
7. 랜딩 빌드 확인: `cd landing; npm run build`.

## 5. 이미지 자산

- 위치: `landing/static/skills/{id}/cover.{ext}` — 랜딩 정적 자산 (PyPI 패키지와 분리). frontmatter `image:` 가 이 경로를 가리킨다 (예: `/skills/engines.company/cover.png`).
- 본문 안 이미지: 마크다운 `![alt](./assets/foo.png)` → 빌드 시 `/skills/assets/foo.png` 으로 변환 ([landing/svelte.config.js](landing/svelte.config.js) `rehypeBaseUrl`).
- 본문에서 사용하는 자산은 `landing/static/skills/assets/` 평면 폴더에 평면 파일명으로 (`syncSkillAssets.js` 가 향후 추가될 수 있음 — 그 전까진 운영자 직접 복사).

## 6. 검증 게이트

`scripts/build/validateSkills.py` 가 신규/수정된 .md 만 검사 (CI 에서 `git diff --name-only` 로 변경 파일 추출 후 인자 전달). 174 개 기존 파일에 일괄 강제하지 않는다.

검증 항목:
- frontmatter 존재.
- 필수 필드 5 개 (id·title·category·purpose·whenToUse) 비어있지 않음.
- `category` 가 4 카테고리 안.
- `id` 점 포함.

## 7. 무엇을 하지 않는가

- capability/docstring 에서 본문 자동 생성 — 금지. SSOT 분리.
- 174 개 본문 일괄 변환 또는 마이그레이션 — 운영자 페이스로 점진.
- frontmatter schema 에 새 필드 즉흥 추가 — [landing/src/lib/skills/catalog.ts](landing/src/lib/skills/catalog.ts) 의 `SkillDoc` 인터페이스와 동기화 필요.
- 카테고리 추가 — 4 개 (start/runtime/operation/engines) 외에 추가하지 않는다.
