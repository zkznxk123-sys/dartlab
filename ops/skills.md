# Skills — capability 는 docstring, 분석 skill 은 SkillSpec

> 상위 사상: [philosophy.md](philosophy.md) · 코드 계약: [code.md](code.md)

**주체**: DartLab 공용 분석 절차 계층 (`src/dartlab/skills`).
**현재**: API 사용법은 docstring/generated capabilities 가 SSOT 이고, 사용법·분석 절차·조합법은 SkillSpec 으로 공유한다.
**방향**: AI, MCP, story, UI, audit, GitHub Pages, 외부 LLM 이 같은 skill resolver 를 사용한다.

---

## 1. 두 가지를 분리한다

### Capability

Capability 는 공개 API 가 무엇을 받고 무엇을 반환하는지 설명한다.

- SSOT: 공개 API docstring.
- 생성물: `CAPABILITIES.md`, generated capabilities, llms/reference 산출물.
- 포함: signature, parameters, returns, units, examples, requires.
- 직접 수정 금지: 생성물은 `scripts/build/generateSpec.py` 로만 갱신한다.

### Skill

Skill 은 분석 목적별 절차 명세다.

- SSOT: `src/dartlab/skills` 의 generated SkillSpec 과 Markdown SkillSpec.
- 포함: 목적, 언제 쓰는지, 필요한 capability/tool/knowledge, 절차, required evidence, runtime compatibility, forbidden, audit 상태.
- 포함 가능: `runtimeCompatibility` — server/MCP/Pyodide/browser 에서 실행 가능한지, 필요한 HF parquet/prefetch, 한계.
- 금지: API parameters/returns/schema 중복, final answer template, 질문별 runner, 대형 코드 블록.
- 사용처: AI workbench, MCP, story, UI, audit, notebook, GitHub Pages.

이 분리는 SSOT 위반이 아니다. Capability 는 API 능력이고, Skill 은 여러 capability 를 조합하는 분석 절차다.
공개 API 능력의 SSOT 는 docstring/generated capability 다. 다만 docstring 은 엔진·함수별로 흩어져 있어 AI 가 목적 기반으로 찾기 어렵기 때문에, SkillSpec 은 흩어진 capability 를 검색·조합·검증 절차로 공개하는 discovery/procedure index 다. SkillSpec 은 API schema 를 중복하지 않고 capability id 만 참조한다.

---

## 2. SkillSpec 구조

SkillSpec 은 실행 코드가 아니라 절차 객체다.

필드:

- `id`
- `title`
- `kind` (`generated`, `curated`, `user`)
- `scope` (`builtin`, `project`, `user`)
- `status` (`unverified`, `observed`, `auditP`, `official`, `deprecated`)
- `category` (`start`, `runtime`, `engines`, `screens`, `finance`, `visuals`, `basic`, `user`, `capability`)
- `inputs`
- `outputs`
- `purpose`
- `whenToUse`
- `requiredInputs`
- `capabilityRefs`
- `datasetRefs`
- `toolRefs`
- `knowledgeRefs`
- `visualRefs`
- `procedure`
- `requiredEvidence`
- `expectedOutputs`
- `visualGuidance`
- `failureModes`
- `forbidden`
- `examples`
- `source`
- `verifiedBy`
- `lastUpdated`
- `runtimeCompatibility`
- `pyodide`
- `docs`
- `quality`

`capabilityRefs` 는 generated capabilities 의 id 만 참조한다. API 반환 구조는 SkillSpec 에 다시 쓰지 않는다.

`runtimeCompatibility` 는 API 사용법이 아니라 실행 환경 계약이다. 예를 들어 Pyodide 에서는 HuggingFace parquet 와 `await dartlab.prefetch(code)` 경로는 가능하지만, live KRX/DART API 와 OAuth profile 은 CORS/인증 제약 때문에 제한된다. 이 정보는 웹 AI 가 실행 가능한 skill 만 고르는 데 사용한다.

---

## 3. Skill 종류

수기 builtin spec 파일은 Markdown + frontmatter 로 둔다. 이것이 사람 문서이면서 AI/MCP skill source 다.

```text
src/dartlab/skills/specs/start/    # 설치, 첫 실행, 환경 점검
src/dartlab/skills/specs/runtime/  # local Python, Pyodide, Web AI, MCP, VSCode
src/dartlab/skills/specs/engines/  # 엔진별 사용 지도
src/dartlab/skills/specs/screens/  # scan/gather 기반 후보 찾기
src/dartlab/skills/specs/finance/  # 재무·공시·밸류에이션·비교 분석
src/dartlab/skills/specs/visuals/  # 표·차트·다이어그램 설명
```

런타임 API는 `dartlab.skills.list/search/get` 한 곳이고, skill id가 SSOT다.

### basic generated

베이직스킬은 수기 YAML 이 아니라 공개 docstring/capabilities 에서 자동 생성되는 엔진 능력 지도다.

- `basic.company`
- `basic.gather`
- `basic.scan`
- `basic.analysis`
- `basic.quant`
- `basic.macro`
- `basic.story`
- `basic.credit`
- `basic.industry`
- `basic.viz`

베이직스킬은 API 설명을 중복하지 않는다. 담는 것은 엔진 역할, 언제 쓰는지, 관련 `capabilityRefs`, 대표 guide/examples 요약, required evidence 후보, failure mode 후보뿐이다. 담지 않는 것은 parameters, returns, unit, 실제 반환 키다.

작업대 도구 사용법은 skill 이 아니다. `search_reference`, `inspect_dataset`, `run_python`, `compile_visual`, `finalize_answer` 는 tool schema/docstring 에서 노출한다.

### capability generated

공개 docstring/capabilities 에서 자동 파생되는 API 단위 capability view. capability view 는 API 상세의 진입점일 뿐이며, API schema 는 docstring/generated capability 가 SSOT다.

### curated

DartLab 이 공식 제공하는 수기 분석 절차. 예: 기업 6막 인과 분석, KRX 지수 강세 분석, 공시 이벤트 중요도 검토.

### user

사용자 또는 프로젝트가 추가하는 skill. 기본 위치:

```text
.dartlab/skills/*.yaml
```

user skill 은 `scope=user`, `status=unverified` 로 시작한다. 기본 위치는 `.dartlab/skills/**/*.md` 이고 capability ref 유효성 검사를 통과해야 한다.

### docs/web 산출물

`docs/skills/**` 와 `landing/static/skills/*.json` 은 skill source 에서 생성한다. 직접 수정하지 않는다.

```text
skill markdown + generated basic/capability
  -> package skill index
  -> docs/skills GitHub Pages markdown
  -> landing static search index
  -> Pyodide compatibility manifest
```

GitHub Pages는 사용자가 보는 skill catalog 이며, AI/MCP/Web AI가 보는 검색 index와 같은 원천을 사용한다.

---

## 4. 실행과 승격

Skill 은 직접 실행하지 않는다. AI, MCP 클라이언트, 사람, story 가 skill 을 읽고 DartLab API 와 workbench tools 로 실행한다.

AI 또는 외부 코딩 에이전트가 DartLab 코드 전체를 읽지 않고 `dartlab.skills` 만 먼저 본 경우에도 다음 순서로 충분히 출발할 수 있어야 한다.

1. 목적 질문으로 skill 을 검색한다.
2. 선택한 skill 의 `capabilityRefs` 로 공개 API docstring/generated capability 를 찾는다.
3. `requiredEvidence` 와 `runtimeCompatibility` 로 실행 가능 범위와 필요한 근거를 확정한다.
4. 실행 결과는 table/value/date/visual 같은 ref 로 남기고 최종 답변 전에 검산한다.

이 흐름 자체도 start/runtime SkillSpec 으로 공개한다. 단, tool parameter schema 나 API return schema 는 여전히 tool docstring/generated capability 가 SSOT 이며 SkillSpec 에 중복하지 않는다.

### Skill 개발 루프

엔진에 직접 정의되지 않은 분석도 곧바로 새 API 로 만들지 않는다. 먼저 skill 개발 루프로 검증한다.

1. 질문을 목적, 대상, 필요한 근거, runtime 제약으로 나눈다.
2. curated skill 이 있으면 그 절차를 쓰고, 없으면 `basic.company`, `basic.scan`, `basic.macro`, `basic.quant`, `basic.viz` 같은 generated basic skill 을 조합한다.
3. 조합이 단일 capability 의 Guide/AIContract 부족 때문에 실패하면 docstring 보강 후보로 기록한다.
4. 여러 capability 를 묶는 반복 절차가 필요하면 curated SkillSpec 후보로 만든다.
5. `/api/ask` 서버 audit 에서 같은 skill 이 반복 P 를 받고 사람이 확인하면 `auditP` 또는 `official` 승격을 검토한다.

이 루프는 `runtime.skillDevelopmentLoop` SkillSpec 으로도 공개한다. 새 skill 은 질문별 runner 나 답변 템플릿이 아니라 capabilityRefs, requiredEvidence, failureModes, runtimeCompatibility 를 통해 엔진 조합 방법을 남긴다.

Kernel/verifier 에 새 분석 분기를 넣는 것은 금지한다. 공통 workbench 규칙은 kernel/verifier 에 남기되, 엔진 선택·절차·응용법은 docstring/generated capability 와 SkillSpec 으로 공개한다.

엔진별 docstring 의 `Guide` 에는 AI 역할을 포함한다. 이 역할은 generated capability 를 거쳐 `basic.company`, `basic.scan`, `basic.macro` 같은 generated basic skill 에 반영되어, AI 가 스킬만 보고도 엔진의 책임과 필요한 evidence 를 먼저 이해하게 한다.

반복 검증된 skill 은 두 경로 중 하나로 간다.

1. 절차 skill 로 유지한다.
2. 공식 엔진 기능으로 승격한다.

승격 대상:

- `analysis` axis
- `scan` axis
- `quant` metric
- `story` report type
- `gather` helper

승격 시 공개 API docstring과 capabilities를 갱신하고, 기존 skill 은 새 capability 를 참조하도록 축소한다.

반복 audit P 를 받은 절차는 docstring Guide/AIContract 또는 공식 엔진 axis 로 승격한다. `auditP` 는 서버 경유 `/api/ask` audit 에서 같은 skill 이 2 회 이상 P 판정을 받은 후보 상태이고, `official` 은 구조 lint, 서버 audit P, 사용자 확인이 모두 있을 때만 허용한다. 자동 metric 만으로 승격하지 않는다.

---

## 5. 검증 게이트

Skill lint 는 다음을 실패로 본다.

- 존재하지 않는 capability ref.
- API parameters/returns/signature/schema 중복.
- final answer template.
- 대형 코드 블록.
- `verified` 근거 없는 official 상태.
- MCP 전용 의미론.
- 잘못된 runtime status (`supported`, `limited`, `unsupported`, `unknown` 외).
- curated skill 의 `runtimeCompatibility.pyodide` 누락.

품질 판정은 직접 audit 로 한다. 자동 검사는 구조 위반만 잡는다.

---

## 6. MCP 관계

MCP 는 skill 을 새로 정의하지 않는다. `dartlab.skills` resolver 를 그대로 노출한다.

기본 표면:

- `listDartlabSkills`
- `searchDartlabSkills`
- `explainDartlabSkill`
- `checkDartlabSkillEvidence`

MCP, `/api/ask`, CLI, UI 는 같은 SkillSpec 을 본다.

---

## 요약

1. API capability SSOT 는 docstring 이다.
2. 분석 skill SSOT 는 `src/dartlab/skills` SkillSpec 이다. SkillSpec 은 흩어진 docstring/generated capability 를 AI/MCP/Web/UI 가 찾기 위한 공개 discovery/procedure index 다.
3. SkillSpec 은 API detail 을 중복하지 않고 capability id 를 참조한다.
4. 수기 skill 은 허용한다. 단 실행 코드·답변 템플릿·질문별 runner 는 금지한다.
5. user skill 은 `.dartlab/skills/*.yaml` 로 확장 가능하다.
6. MCP/story/UI/audit 는 같은 skill resolver 를 사용한다.
