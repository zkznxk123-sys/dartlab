# PRD — DartLab 부채 정직화 (Debt-Honesty)
## 가드망의 조용한 구멍 봉합 · 유령 자산 제거 · god 분해 트랙 박제

> 상태: 설계(PRD) · plan-deep 자기충족 표준 · 범위 = src/dartlab + tests + .github + ui + 문서 전수조사 갭 · 실행 = phased(P0 즉시정정 → P3 점진분해)
> SSOT 거처: `mainPlan/debt-honesty/` (본 PRD = `00-prd.md`, 토론·점수 = `00-eval-ledger.md`, 포인터 = `README.md`)
> 정직 가드: **공개 호출표면(Company facade·MCP advertised tools·HF artifact 경로·UI consume seam) 절대 불변.** 모든 제거는 운영자 제품결정 동반. 자동 docstring sweep 금지·scripts/ 신설 금지·master only·자동생성 도구 금지 전부 준수. churn 최소.
> 근거: 7차원 심층 전수조사(아키텍처·데이터·덕지덕지·테스트·문서·UI·AI, 245 tool 호출·683K 토큰) + 운영자 직접 ground-truth 검증 7/7 확정.

---

## 1. 한 줄 결론 + 비전

**DartLab 전수조사가 드러낸 진짜 부채는 "코드가 더럽다"가 아니라 "보호받고 있다는 믿음과 현실의 간극"이다 — 가드가 죽은 경로(`scripts/`·`ops/`)를 가리키고, 강행 가드 다수가 CI에 배선조차 안 됐고, 노이즈로 못 켜고, 광고(MCP "6 종"·"canonical 7")와 실제(advertised 23 도구)가 다르고, 유령 자산(edinet 3,868줄·ui/web 155파일·ui/shared 20파일)이 parity 게이트나 stale 메모리로 박제되어 있다. 본 PRD는 큰 리팩토링이 아니라 *방어망 자체의 정직화*를 1순위로 삼는다 — 가드망이 정직해지면, 다른 PRD들이 이미 계획한 분해 작업이 비로소 안전해진다.**

### 비전
- **가드는 거짓말하지 않는다.** CLAUDE.md가 "기계 강제"라 선언한 모든 가드는 실제로 (a) 살아있는 경로를 가리키고 (b) CI(`tests/run.py`)에 배선되어 (c) 노이즈 0으로 켜질 수 있어야 한다. *배선 못 할 가드는 명시 폐기한다 — 좀비 가드 금지.*
- **유령은 격리되거나 사라진다.** 빌드·import·skill이 0인 자산(edinet·ui/web·ui/shared·죽은 MCP 도구·중복 JSON)은 운영자 제품결정 후 격리(라벨링) 또는 제거한다. 미래 복구 옵션 보존이 필요하면 *명시적 동결 라벨*로, 아니면 삭제로.
- **광고는 진실과 같다.** 외부 LLM·기여자가 받는 모든 표면(MCP instructions·AGENTS.md·catalog count·README_EN·메모리 SSOT 포인터)은 실제 코드와 일치한다.
- **분해는 무리하지 않는다.** providers 82배 격차·Company god-class·builders.py 6,111줄 같은 구조 분해는 *순서와 추적 가드를 박제*하되 실행은 점진(기존 frontend-refactor-loop·company-analysis-report·data-build-workbench-ssot 루프에 트랙으로 위임)한다. 본 PRD가 한 번에 다 쪼개지 않는다(스코프 절제).
- **불변 3종.** 공개 호출표면(Company facade frozen manifest·MCP advertised 22 tools·각 엔진 verb) · HF artifact shape/경로 · UI consume seam은 본 PRD 전 과정에서 byte 동등으로 보존한다.

### 왜 지금, 왜 이 순서인가
CLAUDE.md의 최상위 회귀 방어 철학은 **"⛔ 회귀 가드 — Guard Index 우선 (AST census > pytest 전수)"**다. 그런데 전수조사 결과 그 Guard Index의 구멍이 7개 차원에서 *독립적으로* 발견됐다. 즉 프로젝트가 의존하는 안전망 자체가 부분적으로 거짓이다. 다른 부채(god 분해·dead code 제거)를 먼저 건드리면 그 작업의 회귀를 잡아줄 가드가 거짓이라 위험하다. **따라서 P0=가드 정직화가 모든 후속 부채감소의 전제 조건이다.**

---

## 2. 현상 진단 — 7차원 전수조사 실측 (ground-truth 검증)

> 모든 수치는 census 에이전트의 직접 grep/wc 측정 + 운영자 spot-check 7/7 확정. 추측 0. seed 과측은 §2.6에서 정정.

### 2.1 메타-테마 ① 가드 환상 (Guard Illusion) — **최고 하중·최고 ROI**

CLAUDE.md·memory가 "기계 강제"라 단언하는 가드들이 실제로는 죽어있거나 배선 안 됨. 운영자 직접 검증 완료:

| ID | 가드 | 현실 (검증된 file:line) | 증상 |
|---|---|---|---|
| G-1 | `test_no_raw_cross_scan.py` | `:22` `_BASELINE = _REPO/"scripts"/"audit"/.../rawCrossScan.json` — `scripts/` 부재(실제는 `tests/audit/_baselines/`). `_loadBaseline()`이 부재 시 `{"violations":[]}` silent fallback | baseline ledger 끊김. 위반 0이라 우연히 green. `scripts/` 금지 규칙(CLAUDE.md)을 코드가 위반 |
| G-2 | `skills/measureProgress.py` | `:68` `_BASELINE_DIR = _REPO/"scripts"/"audit"/"_baselines"`, `:69` `_PROGRESS_DIR` 동일 죽은 경로. `:111` glob이 빈 디렉터리 순회 | docstring/부채 progress 시계열(measureHistory.jsonl)이 전부 0/거짓. docstring* baseline 7개가 "읽힌다" 적혀있으나 실제 미소비 |
| G-3 | `checkAgentBoundary.py` (no-graph-regression) | `tests/run.py` 참조 **0건**(운영자 검증). substring 매처가 '회귀 가드'·'GATE 차단' 정당 주석 16파일 false-positive | CLAUDE.md "자동 lint가 PR 검출" 주장과 불일치. --strict 시 항상 red라 *켤 수 없는 가드* |
| G-4 | `staleImports.py` | `tests/run.py` 참조 **0건** | stale facade import 회귀 미감지(진단만 존재) |
| G-5 | `deprecationAudit.py` (**유령 가드**) | **파일 자체가 부재**(`find -name deprecationAudit*`=0). 그런데 `DEPRECATION.md:44,82`이 "`tests/audit/deprecationAudit.py`(T8-1)가 PR 차단", `:54` "PR마다 자동 동기화"라 단언 — *존재하지 않는 가드가 강제한다고 문서가 약속*(가장 순수한 가드 환상). 실태: raw `warnings.warn(…DeprecationWarning…)` **11건**(멀티라인 호출 — single-line grep 으로 7로 오측됐던 것을 운영자 직접 재검증): `providers/dart/accessor/profileAccessor.py:399`, `reportAccessor.py:435/454/473/492/511`(5), `credit/__init__.py:391`, `quant/__init__.py:269,280`(2), `story/registry.py:1558,1565`(2). `@deprecated` 데코 production 사용 0 vs `DEPRECATION.md` "Currently Deprecated 0" | 거버넌스 약속("언제 무엇이 사라지는지 미리 알림")이 강제 0으로 침묵. 배선이 아니라 **신규 저작**이 필요 |
| G-6 | `untrustedWrapAudit.py` | `tests/run.py` 참조 **0건**. wrap이 하드코드 8-key(`formatting.py:13-22`) 의존 → summary/html/description 키 외부본문은 unwrapped | CLAUDE.md ⛔ "external 본문 untrusted" 기계보증이 키 운(luck) 의존. prompt injection 방어선 잠재 구멍 |
| G-7 | docstring 9-섹션 게이트 | `gatherGate.py:45` `_TARGET='src/dartlab/gather'` — **6엔진 중 gather 1개만 배선**. `_baselines/`에 `gatherDocstring9Section.json` 단 1개 | seed의 "story 23.8%/ai 26.7%"는 ratcheting 게이트가 아닌 ad-hoc 1회 측정. story/ai/analysis 회귀 무방비 |
| G-8 | `stale_references.py` | `:51-60` `_SCAN_ROOTS`에 `'ops'`,`'scripts'` 포함 — 둘 다 부재(ops는 commit `69d6e667`로 폐기, scripts는 금지) | 자기 자신이 stale 경로를 광고하는 가드. 기능은 무해(빈 결과)하나 기여자 오인 |
| G-9 | `sourceDriftBaseline.py` | `:31` baseline `tests/audit/_baselines/sourceDriftBaseline.json` 부재. docstring: 부재 시 `--check`가 stderr 경고 + **exit 0** | gov↔krx 가격 fallback drift 회귀 무검증(gov-price-migration 이후). nightly·네트워크 의존이라 즉시위험은 낮음 |

**공통 근인**: 게이트를 T-트랙별로 점진 추가하다 (a) `tests/audit/` ↔ `scripts/audit/` 폴더 이전(noScriptsDir 도입) 시 일부 경로 상수 갱신 누락, (b) false-positive를 못 비워 배선 보류, (c) baseline 박제 누락. **개별로는 사소하나 합치면 "Guard Index 우선" 철학의 실행 실패다.**

### 2.2 메타-테마 ② 유령 자산 (Phantom Assets)

빌드·import·skill이 0인데 parity 게이트나 stale 참조로 박제되어 유지비만 발생:

| ID | 유령 | 규모·증거 | 왜 살아있나 |
|---|---|---|---|
| PH-1 | **edinet provider** | 14파일/3,868줄 + 테스트 15파일/531줄 + docstring stub **194건**(전체 stub의 78%, 예 `edinet/openapi/client.py:50`). 빌드경로 0·gather 0·skill 0·공개진입점 0(`dartlab.__init__`·`api.py`에 OpenEdinet 0). `dataConfig.py:182-188`에 phantom DATA_RELEASES 슬롯 | 초기 3-provider 대칭(한·미·일) 설계 → `providerSymmetry`/`folderMirror`/`folderSize`/`testCoverage` 게이트가 3자 parity 강제. EDINET API 통신불가 판명 후 스캐폴드+게이트만 잔존. `providers/__init__.py:29 __all__=["dart","edgar","edinet"]`이 "활성 일본 지원" 거짓 시그널 |
| PH-2 | **ui/web** | git-tracked **155파일**(그중 src 137파일/16,976줄, lock 8,719줄 별도) + 디스크 9.6M + node_modules 별도 8.7M. 워크스페이스 밖(`package.json` workspaces=landing·ui/packages·ui/apps만)·wheel 밖·CI 밖. 현재 앱 import **0**(`DARTLAB_UI_LEGACY=1` escape로만 서빙, `_ui_path.py:50`). `package-lock.json` 8,719줄이 dependabot(directory=/만) 밖 → 보안취약점 미스캔 rot | 단계-10 SvelteKit 전환 시 viz bento(/api/viz)가 svelte 미이관이라 "가역 escape"로 보존. viz_router는 기본서버 마운트 유지(데이터 API 살아있음)·죽은 건 소비 UI뿐. frontend-refactor-loop가 "ui/web=DEPRECATED 스코프제외"로 명시 회피 → **영구 미정리** |
| PH-3 | **ui/shared** | git-tracked 20파일(chart 15·api 3·md 2). 실 import **0**(landing `$chart` 별칭 정의됐으나 `grep '$chart' landing/src`=0). PriceChart(511줄)·SparklineChart 등 surfaces live 버전의 dead twin | vscode 확장 폐기(2026-05-26)·차트 경로 변경 시 소비처 소멸. **그런데 `financial-statement-lab/03-architecture-and-reuse.md:63`이 ui/shared/chart/ChartRenderer를 'SSOT'로 명시 참조 + memory `reference_financial_graph_ssot`가 가리킴** → 후속 작업이 죽은 코드를 SSOT로 인용 |
| PH-4 | **ai.persistence 죽은 import** | 모듈 부재(`ls src/dartlab/ai/persistence`=No such file). 그런데 `analysis/financial/storyValidation.py:108` `from dartlab.ai.persistence.knowledge_db import KnowledgeDB`, `story/publisher.py:84` `...blog_insights import upsert_ai_frontmatter_to_insights` — 둘 다 try/except로 삼킴 → 항상 except | operation.philosophy §6 "양방향 human↔AI 루프(사람→AI 경로)"가 코드상 **silent no-op**. 운영자가 작동한다고 착각. (성공했다면 L2→L4 역방향 위반이었을 코드) |
| PH-5 | **죽은 MCP 도구 6종** | `registry.py _SPECS`(**32개**, AST 키 카운트 — seed 64는 2x 오측 정정)에서 `_DEFAULT_TOOL_NAMES`(22)∪`CANONICAL_V2`(22) 양 표면 모두에 부재한 6종: **InspectDataset·ListEngineGaps·LookAheadGuard·ProposeRecipe·RequestUserInput·ValidateRecipe**(AST set-difference 검증). import+spec+구현 모듈(각 ~150-185줄) 살아있음. 단 LookAheadGuard·RequestUserInput은 deprecated `ask_kernel_status`(SD-2) 12-tuple로 *leak* → "노출 0"이 아니라 "정식 표면 0 + 좀비 resource 경유 leak" | 마스터플랜 트랙1/recipe 실험 잔재. import+spec+구현 3세트 유령 동기화. SD-2(P2-6)와 동일 변경단위 |
| PH-6 | **agent.json ≡ catalog.json** | md5 `f1d1b8e5…` byte 동일, 각 1,658,772 B(운영자 검증) | generateSkills가 동일 페이로드를 두 파일명 출력(레거시 agent.json + 신 catalog.json). 별칭화/삭제 미완. 1.66MB 데드 중복 = git diff·wheel·리뷰 2배 |
| PH-7 | **orphan baseline JSON 13개** | 어떤 audit 도구도 파일명 참조 0(stem grep): aiKpiV1·docstring{AIContext,Capabilities,Guide,Requires,SeeAlso,Specifications}·importLinterExceptions·pipAuditAllowlist·sections{Loss,Memory,Precision}Baseline·skillGraphOrphans. 그중 aiKpiV1·importLinterExceptions는 git 전체 0(완전 orphan) | 게이트 은퇴(per-section→통합 docstring9Section, import-linter 인라인화) 시 baseline 미삭제. 42 baseline 중 31%가 소비처 불명 → "부채원장 SSOT" 신뢰 저하 |
| PH-8 | **flakyAudit 화석** | `flakyAudit.py:6` "현재는 없음 — placeholder". 읽는 `flakyGates.json` 부재. `qualityHistory.jsonl` 2엔트리·최종 2026-04-09(2+개월 stale). 실효 flaky 처리는 `conftest.py:116` network마커→reruns=2가 별도로 잘 작동 | flaky 자동 quarantine 야심이 데이터소스 부재로 placeholder 정지. "품질 추적 중" 착시 |

### 2.3 메타-테마 ③ 표면 드리프트 (Surface Drift) — 광고 ≠ 현실

외부 LLM·기여자가 받는 표면이 실제와 불일치:

| ID | 표면 | 드리프트 (검증) | 영향 |
|---|---|---|---|
| SD-1 | MCP_INSTRUCTIONS | `protocol.py:26` "SSOT v2 **6 종** 도구", `:30` "**canonical 7** 데이터 도구" vs 실제 advertised **23**(`mcpAdvertisedToolNames()`=('ask',)+CANONICAL_V2 **22**, `registry.py:769-791` 직접 카운트). `protocol.py:91` docstring "= 22 종"도 stale. `server.py:270`이 instructions로 주입 | MCP로 붙는 모든 외부 LLM이 시스템 메시지에서 도구 6~7개로 학습 → PeerCompareN·DCFValuation·SensitivityAnalysis 등 신규 강력 도구 미호출 |
| SD-2 | `dartlab://ask-workbench` 리소스 | `protocol.py:183-191` `ask_kernel_status`가 deprecated 12-tuple(`MCP_WORKSPACE_AGENT_TOOL_NAMES`, LookAheadGuard 포함) + `:184` `GRAPH_NODES`로 `'passes':['brief',…,'harvest']` 반환 | 외부 AI가 옛 12종 + 5-pass 노드명을 진실로 수신. graph-회귀 금지 룰의 5-pass 고정노드를 MCP가 'passes'로 공식 노출 = chat-native 정체성 모순 |
| SD-3 | AGENTS.md | `:8` `C:\Users\MSI\.claude\projects\…\MEMORY.md` 운영자 사설 절대경로(username 'MSI' 노출). memory/는 gitignore → 외부 기여자 접근 불가 죽은 경로 | username 식별정보 누출(주체-중립 룰 위반) + 온보딩 첫 단계 실패 |
| SD-4 | catalog.json meta | `count` recipes **161** vs 실제 `specs/recipes/*.md` **243파일**(`find` 실측). 어느 status 필터로도 161 미일치(status 분포는 frontmatter 형식 혼재라 generateSkills 필터 규칙 직접 확인 선결) | 외부 LLM·기여자가 가용 recipe 수 오인. generateSkills 필터 규칙 불투명 |
| SD-5 | README_EN | `## ` 섹션 README 21 vs README_EN 16(5개 누락). EN 마지막 갱신 2026-06-13 vs README 2026-06-18(5일 stale) | 영어권 사용자 구버전 안내(터미널·데이터 신규 섹션 미반영) |

### 2.4 메타-테마 ④ god 무게 (구조 부채 — 분해는 점진/위임)

| ID | god | 규모(검증) | 분해 위험·소유 |
|---|---|---|---|
| GD-1 | providers 레이어 | 76,703줄(raw) / 61,853줄(moduleSize 유효) = **frame 대비 82배**(목표 ≤10배). dart 하위만 49,951줄. 내부 14 sub-namespace로 자연 분기. seed의 T9-1 분해 트랙은 `operation/architecture.md`(262줄)에 **흔적 0** | XL·장기. providers가 panel/finance/search 데이터 owner라 이관 시 HF 경로·consume seam 위험. **우선 문서화(S)→추적가드(M)→점진 이관(XL)** |
| GD-2 | Company god-class 3쌍 | dart 104 / edgar 84 메서드, 공유이름 **63**, 공유 base/mixin **0**(전부 object 상속). dart/company.py 5,596줄·edgar 4,713줄. 신규 provider = 60+ 메서드 복제 | XL. 추출 seam 이미 실재: `core/protocols.py:251 class CompanyProtocol`(구조적 타입 계약) + `tests/audit/guard/rules.py:296 checkProviderCompanyFrozenSurface`(공개표면 frozen manifest 가드, `dartlabGuard.py:84` 집계). `CompanyFacadeMixin` 점진 이관(메서드군별)이 CompanyProtocol 구현 보존하는 한 안전 |
| GD-3 | story/builders.py 외 god 파일 | builders.py 6,111줄/181 def, viz/display/adapters.py 2,920줄/58 def, core/ratios.py 2,132줄/63 def, story/registry.py 1,786줄. **(noteTaxonomyData.py 2,948줄은 def·class 0 = 순수 데이터 → god 아님, seed 정정)** | L. 순수 함수 무더기라 레이어 위험 낮음. 가장 다루기 쉬운 god. frontend-refactor-loop는 ui만·스코프 밖 |
| GD-4 | surfaces god 컴포넌트 | PriceChart.svelte 1,498줄·CompanyCard 1,402·MacroLensDialog 1,175·ViewerStudio 1,053·AskDrawer 1,041·HoldingsDialog 932·RightStack 918(평균 345의 2.7~4.3배). PriceChart는 활성 PRD 다수가 동시 편집하는 hot 파일 | L. frontend-refactor-loop가 'dedup'은 다루나 단일파일 god-split는 백로그 부재 |
| GD-5 | 17 lazy upper-import | **메서드 본문 내부**(col-0 아님) L1→L2/L3 역방향 lazy import 17건 — `providers/dart/company.py` 12건(라인 2359·3092·3164·3288·3289·3892·4189·4969·4970·4981·5050·5316) + `providers/edgar/company.py` 5건(라인 476·1244·1306·2103·3076). `dartlabGuard.json protectedCompanyFacadeDebt.architecture.lazyUpperImport`=17 동결(운영자 직접 검증). `test_no_cycles`는 strict-toplevel이라 이 inversion 못 봄 | L. GD-2 mixin+DI와 묶어야 근본 해소. 단독은 원장 정당성 문서화(S) |
| GD-6 | providers/__init__.py(ai) | 682줄/28 def·class. createProvider 팩토리+cache prefix+라우팅 혼재. (agent.py는 1,111줄이나 단일책임 분해됨 → god 아님, seed 정정) | M. 순수 추출(factory.py·cachePrefix.py). checkAgentBoundary가 providers skip이라 안전 |

### 2.5 메타-테마 ⑤ 테스트 비율 불균형

| 엔진 | prod/test LOC 비율(검증) | 목표 |
|---|---|---|
| viz | **6%** (14,255/857) | testLocRatio 게이트 목표 80%, 현실적 ≥30% |
| macro | **6%** (14,376/921) | ≥30% |
| story | 15% (13,836/2,053) | ≥30% |
| analysis·quant·scan | 각 17% | ≥30% |
| (대조) ai·pipeline·mcp | 59%·68%·63% | — |

`testLocRatio.py`는 전체 64.8%→80%만 측정·**엔진별 strict 게이트 부재**. viz/macro/story 회귀가 단위테스트로 안 잡히고 느린 realData/snapshot(OOM·flaky)에만 의존. god-file 분해가 진행될수록 비율 악화.

### 2.6 seed 과측 정정 (census ground-truth가 바로잡음)

미래 감사가 같은 오측을 반복하지 않도록 측정 정의를 박제:

| seed 주장 | 실측 정정 | 정의 |
|---|---|---|
| stale import 73건/56파일 | module-level(col-0) **18건** + 함수-local lazy 다수(의도된 cycle-break) | 73/56은 옛 baseline. 진짜 정리대상은 비-exempt ~12건 |
| TODO 265건 | 코드주석 `# TODO` **3건**(정상 박제) + docstring stub `<TODO:` **248건**(78%=194 edinet) | "TODO 마커"를 code-TODO vs docstring-stub로 분리 측정 필수 |
| noteTaxonomyData god 파일 | def·class **0** = 순수 NOTE_TAXONOMY dict → god 아님(데이터) | "god"=def 밀도지 줄 수 아님 |
| agent.py 49KB god | 1,111줄/22 def, toolStorage.py 등 단일책임 분해됨 → god 아님 | 49KB는 바이트(주석 한글 2바이트). LOC 기준 |
| _attempts 오염 | 이미 `.gitignore` 전체 ignore. disk 2.7GB(로컬 scratch)·tracked 8파일 | repo 위생 양호. 디스크는 git 무관 |
| .gitignore 비대 | 156줄/87 유효패턴 = 정상 | 비대 아님 |
| CHANGELOG 171KB 부채 | Keep-a-Changelog 단일파일 표준·파싱결합 0 → **분해 안 하는 게 정공법** | cosmetic, 저ROI |
| (R1 정정) DeprecationWarning 7건 | **11건**(멀티라인 `warnings.warn(`…`DeprecationWarning,`) | single-line grep 함정 — 호출 여는 줄과 인자 줄이 분리되면 누락. multiline·`-A3` grep 필수 |
| (R1 정정) MCP advertised 22 | **23**(ask+CANONICAL_V2 22) | tuple 길이는 직접 카운트. 코드 docstring(`= 22 종`)도 stale라 그대로 상속 금지 |
| (R1 정정) recipe 237 | **243파일** | status frontmatter 형식 혼재 → 파일 count 와 status 분포 분리 측정 |
| (R2 정정) _SPECS 64 | **32**(AST 키) | dict 본문 정규식이 over-match → AST 키 카운트 |
| (R2 정정) 죽은 MCP 4종 | **6종**(InspectDataset·RequestUserInput 추가) | `_SPECS − (_DEFAULT ∪ CANONICAL_V2)` set-diff, 한쪽 표면만 보면 누락 |
| (R2 정정) preflight 27/29 게이트 | GATES **30**(fast17/full6/nightly7) | CLAUDE.md "CI 27"도 stale → count 직접 AST 파싱 |
| (R2 정정) deprecationAudit.py 미배선 | **파일 부재**(문서만 강제 약속) | "미배선"과 "미존재"는 다른 처방(배선 vs 신규저작) |
| (R2 정정) edinet parity = providerSymmetry/folderMirror baseline | 실제 = `__all__`+providerSymmetry.py 본문+folderSize/testCoverage.json | parity 강제 위치를 baseline grep 으로 실측(가정 금지) |

### 2.7 기존 PRD 교차참조 — 재계획 금지 목록

본 PRD는 *어떤 기존 PRD도 안 다루는 갭*만 다룬다. 아래는 이미 계획된 부채(참조만, 재계획 금지):

| 부채 | 소유 PRD | 본 PRD 관계 |
|---|---|---|
| 파이프라인 빌드 흡수(macro/krx/news/dart subprocess→in-library), yml 단일진입 | `data-build-workbench-ssot` | 참조. 본 PRD는 빌드측 가드(rawCrossScan 경로)만 |
| 검색 sidecar 정리·npz폐기·단일 choke | `search-os`(코드 끝·배포만 잔여) | 무관 |
| ui/packages·landing cross-file dedup/추출 | `frontend-refactor-loop`(자율) | god-split·죽은패키지는 그 루프 스코프 밖 → 본 PRD 갭 |
| UI consume 데이터배선 SSOT | `data-workbench-ssot`(_done) | 완료(checkUiDataWiring 0). 무관 |
| Polars OOM 근본(메모리 백엔드) | `polars-gpu-backend` | pytest 전수금지 근본은 그 PRD. 본 PRD는 fixture/testLocRatio만 |
| 외부 AI용 좁은 8-tool connector + envelope | `ai-workbench-connector` | outward 신설. 본 PRD는 내부 MCP 22-tool registry 정리 |
| 터미널 god 다이얼로그 *기능* 재설계 | macro-lens-redesign·periodic-report-dossier 등 | 기능 IA지 파일 크기 분해는 별개 → 본 PRD가 god-split 백로그화 |

---

## 3. 설계 원칙

1. **정직화 우선 (Honesty-first).** 가드가 거짓이면 부채를 못 줄인다. P0/P1(가드 정직화)이 P2/P3(제거·분해)의 전제. 순서 역전 금지.
2. **좀비 가드 금지.** 모든 죽은/노이즈 가드는 *둘 중 하나*: ① 살려서 CI 배선(false-positive 0 전제) ② 명시 폐기(코드·docstring·CLAUDE.md 주장 동시 정정). "있는 척"으로 두지 않는다.
3. **스코프 절제.** god 분해(GD-1~6)는 *순서+추적가드를 박제*하되 일괄 분해 금지. 기존 루프(frontend-refactor-loop·company-analysis-report)에 트랙으로 위임. 본 PRD가 직접 쪼개는 건 P3의 *문서화·가드·첫 증명 1건*까지.
4. **정공법·롤백 단위.** 우회·fallback·임시 shim 금지. 각 변경은 단일 논리단위 commit + 즉시 git revert 가능. 제거는 운영자 제품결정 게이트 통과 후.
5. **규칙 정합 (전부 준수).** 자동 docstring sweep 금지(사람 묶음 review만·baseline은 동결원장) · scripts/ 신설 금지(오히려 죽은 scripts/ 참조 *제거*) · master only · 자동생성 도구 신설 금지(중복 *제거*는 허용) · UI 변경은 운영자 push 승인 · 공개표면 불변.
6. **측정 정의 박제.** §2.6 정정을 operation.testing/code에 반영해 미래 감사 오측 차단.

---

## 4. Phase 설계

> 분류 기준: P0=즉시·1줄급·저위험·고ROI / P1=가드 배선 결정 / P2=유령 제거(운영자 제품결정) / P3=구조 분해 트랙 박제(실행 점진). 각 항목에 census ID·effort·위험·롤백 명시.

### Phase 0 — 가드 경로·표면 드리프트 즉시 정정 (저위험·고ROI, 대부분 1줄)

**P0 게이트: 동작 변화 0(위반 0 상태에서 경로만 재연결) 또는 표면 텍스트만. 전부 단일 commit, 즉시 revert 가능.**

| 항목 | census | 변경 | 검증 |
|---|---|---|---|
| P0-1 | G-1 | `test_no_raw_cross_scan.py:22` `scripts/audit/_baselines` → `tests/audit/_baselines`. `_loadBaseline()` 부재 시 silent fallback → `raise FileNotFoundError`(경로 drift 즉시 fail) | 가드 재실행 위반 0 유지·baseline 재연결 확인 |
| P0-2 | G-2 | `measureProgress.py:68-69` `scripts/audit/_baselines`·`_progress` → 실제 위치(`tests/audit/_baselines`·신규 `tests/audit/_progress`). glob 부재 시 raise | progress 값 재캡처 후 baseline 재박제 |
| P0-3 | G-8 | `stale_references.py:51-60` `_SCAN_ROOTS`에서 `'ops'`,`'scripts'` 제거(둘 다 폐기). specs/는 src/ 하위라 이미 커버 확인 | 가드 재실행 클린 유지 |
| P0-4 | SD-1 | `protocol.py:26,30` "6 종"/"canonical 7" → 도구 *카테고리* 설명(메타/실행/외부/저장) + 개수 단언은 `len(mcpAdvertisedToolNames())`(=23) 참조 또는 제거. `protocol.py:91` docstring "= 22 종"도 23으로 동시 정정. 신규 도구(PeerCompareN·DCFValuation 등) 1줄씩 추가 | MCP instructions 재생성·운영자 톤 검수 |
| P0-5 | SD-3 | `AGENTS.md:8` 운영자 사설경로 → "operator-private memory(gitignored, 외부 기여자 해당 없음)" 중립 기술 또는 단계 제거 | username 0·외부 온보딩 경로 CLAUDE.md+start.dartlabSkillOs로 충분 확인 |
| P0-6 | PH-6 | agent.json/catalog.json 참조처 grep(MCP·ReadSkill 로더가 어느 이름 읽는지) → canonical 1개 확정, 다른 쪽 삭제 또는 빌드시 복사 단일화 | md5 동일 확인됨. 참조 일원화 후 wheel 크기 −1.66MB |
| P0-7 | SD-4 | catalog.json `count` 필터 규칙을 generateSkills에서 확인 → 실제 243파일 기준 정합 재생성(어느 status 를 count 에 넣는지 명문화) + deprecated 2 spec(`recipes/sentiment/*`) 제거 | count 재측정 일치 |
| P0-8 | G-9(표면화) | `sourceDriftBaseline.py` 부재를 silent-pass→명시 warn-and-track(dataAudit nightly 잡에 표면화). *박제는 운영자 1회 네트워크 실행 필요라 P2로* | nightly 로그에 "baseline 부재" 가시화 |

### Phase 1 — 가드 CI 배선 정직화 (배선 or 명시 폐기)

**P1 게이트: 각 가드는 ① false-positive 0 만든 뒤 `tests/run.py` 적정 게이트에 --strict 배선 ② 또는 살릴 가치 없으면 명시 폐기(코드+CLAUDE.md+memory 주장 동시 정정). 좀비 금지.**

| 항목 | census | 결정 + 작업 | 비고 |
|---|---|---|---|
| P1-1 | G-3, GD 노이즈 | `checkAgentBoundary` keyword 매처를 주석/docstring strip 후 *식별자 컨텍스트*만 매치(AST, `_FIVE_PASS_NODE_NAMES` 방식)로 정밀화 → false-positive 0 → `tests/run.py` preflight 배선. **이게 "기계 강제" 주장을 현실로 만듦** | no-graph-regression은 memory상 8번 회귀한 민감영역 → 탐지력 유지 신중 검증. 실제 5-pass 노드 회귀는 계속 잡아야 |
| P1-2 | G-4 | `staleImports.py`를 baseline 원장(현재 module-level 18건 동결)으로 `tests/run.py` 배선 → 신규 증가=회귀. 비-exempt ~12건은 codemod 후 baseline 축소 | server/api·skills/add* exempt 패턴 검토. 각 건 import 그래프 확인(cycle 회피 목적이면 직접 import가 새 cycle 유발) |
| P1-3 | G-5 | **11개** raw `warnings.warn(…DeprecationWarning…)`(accessor 6·credit 1·quant 2·story 2)을 `@deprecated(version, alternative)` 데코로 교체 → `DEPRECATION.md` Currently Deprecated 동기화 → **`deprecationAudit.py` 신규 저작**(가드 부재 — DEPRECATION.md 약속 충족: @deprecated 데코↔문서 항목 대조 + raw warnings.warn 잔존 검출, FP=0) → `tests/run.py` 배선. *기존 가드 배선이 아니라 작성+배선이라 effort L* | report.dividend·quant/credit/story axis-first swap 등 외부 의존 가능 → 즉시 제거 아닌 3-minor notice 준수 |
| P1-4 | G-6 | `untrustedWrapAudit.py` `tests/run.py` 배선 + wrap을 8-key 허용목록 → external ref 전체 str 필드 순회(키 무관) 또는 흔한 키(summary·html·description) 우선 추가 | 마커 idempotent라 과잉wrap 안전. 출력 가독성만 주의 |
| P1-5 | G-7 | docstring 9-섹션 게이트를 story/ai/analysis로 확산하되 **분모를 공개 API 표면(`__all__`+엔진 verb spec capabilityRefs 교집합)으로 정밀화**(`docstring9Section.py:166` public 판정 수정). baseline=현재위반 동결(자동생성 아닌 사람 묶음 review 대상은 좁혀진 표면만) | 자동 sweep 금지 준수. "story 23.8%"는 LLM 미노출 내부헬퍼 280개 포함된 형식주의 함정 → 실제 부채는 수십 verb 규모 |
| P1-6 | ARCH-4 | import-linter advisory(100+ 위반 비가시) 결정: **dartlabGuard AST census 단일 SSOT로 통합 권고**(cycleScan도 advisory인 현실과 정합) 또는 100+ ignore 원장화 후 blocking. import-linter의 transitive 분석을 dartlabGuard가 대체하는지 검증 선결 | 이중 가드 체계 중복 해소. 결정이 선결 |

### Phase 2 — 유령 제거 (운영자 제품결정 동반)

**P2 게이트: 빌드·import 0 확정(grep 전수) 후 ① 미래복구 옵션 필요시 명시 동결 라벨 ② 아니면 삭제. UI 자산 제거는 운영자 push 승인 필수.**

| 항목 | census | 작업 | 운영자 결정 |
|---|---|---|---|
| P2-1 | PH-1 | edinet **동결 격리** (parity 강제 위치 실측 정정 — providerSymmetry.json·folderMirror.json은 edinet 참조 0, 강제는 코드+다른 baseline): ① **주역** `providers/__init__.py:29 __all__`에서 제외(게이트 provider 루프 구동) ② `providerSymmetry.py` 본문 edinet 상수 2건에 동결-skip 분기 ③ `folderSize.json`(edinet 2건)·`testCoverage.json`(edinet 1건)에서 엔트리 제거 또는 frozen 표시 ④ skill/README "API 미가용 동결" 라벨 ⑤ `dataConfig.py:182-188` phantom 슬롯 "unbuilt" 주석. **코드 삭제 X(미래 API 복구 옵션 보존)** | 동결 격리 vs 완전삭제 |
| P2-2 | PH-2 | ui/web 운명: (A) viz bento(/api/viz) + dashboard를 surfaces 이관 후 ui/web 삭제 / (B) viz bento 폐기(viz_router unmount + ui/web 전체 + _ui_path legacy 분기 삭제). 어느쪽이든 17K줄·9.6M·미스캔 lock 제거. terminalSvelte/는 import 0이라 즉시삭제 | **viz bento 폐기 vs 이관(제품결정)**. UI라 push 승인 |
| P2-3 | PH-3 | ui/shared 삭제(import 0 확정) + landing vite/svelte.config `$chart`·sharedChartDir 별칭 제거 + **`reference_financial_graph_ssot` 메모리·`financial-statement-lab` PRD를 실제 dispatcher(landing charts.ts·surfaces MiniFinChart)로 정정**. SSOT 정정이 삭제보다 중요 | prerender/notebook 동적사용 가능성 1회 확인. UI라 push 승인 |
| P2-4 | PH-4 | ai.persistence 추적: KnowledgeDB·blog_insights 실제 위치 grep → 이동됐으면 import 정정(단 L2→L4 역방향이라 호출 구조 재설계), 폐기됐으면 try/except 블록+죽은 호출 제거 + operation.philosophy §6 양방향루프 사상을 현실 동기화 | **기능 부활 vs 박제(사상 결정)** |
| P2-5 | PH-5 | 죽은 MCP **6종**(InspectDataset·ListEngineGaps·LookAheadGuard·ProposeRecipe·RequestUserInput·ValidateRecipe) 의도 판정 → 능력이면 CANONICAL_V2/_DEFAULT 배선(노출), 잔재면 import+_SPECS+구현 동시 제거. InspectDataset은 work.py:32 실사용이라 별도 분류, recipe 계열은 ai/recipes/ 교차확인. **P2-6과 동일 변경단위**(leak 경로 동시 차단) | 능력 vs 잔재(도구별) |
| P2-6 | SD-2 | (P2-5와 묶음) `ask_kernel_status`(`protocol.py:183-191`)를 `mcpAdvertisedToolNames()` SSOT 전환 + 'passes' 필드 제거(또는 workbench=opt-in 명시) + `MCP_WORKSPACE_AGENT_TOOL_NAMES` 12-tuple 상수 삭제(= LookAheadGuard·RequestUserInput leak 경로 제거) | — |
| P2-7 | PH-7 | orphan baseline 정리: aiKpiV1·importLinterExceptions(완전 orphan) 삭제, docstring* 7개는 P0-2(measureProgress 정정) 후 재판정. baseline↔소비도구 1:1 인덱스 게이트 신설(자동 orphan 검출) | — |
| P2-8 | PH-8 | flakyAudit 화석 처리: conftest network→rerun이 유일 SSOT임을 operation.testing 문서화 → placeholder flakyAudit·stale qualityHistory 삭제(over-eng 회피). 또는 nightly GH workflow_runs 수집 배선(살릴 경우) | 폐기(권고) vs 부활 |
| P2-9 | SD-5, TEST-8 | README↔README_EN 섹션 parity 라이트 audit(헤더 비교) + EN 5섹션 동기화(사람번역). tests/eval↔_evals 이름충돌 README SSOT 명시 + _drafts(1)·calibration(1) 적정폴더 흡수 | — |

### Phase 3 — god 분해 트랙 박제 + 테스트 비율 가드 (실행 점진/위임)

**P3 게이트: 본 PRD는 *순서·추적가드·첫 증명 1건*만. 일괄 분해 금지. 나머지는 기존 루프 백로그로 위임.**

| 항목 | census | 작업 |
|---|---|---|
| P3-1 | GD-1 | providers 82배 격차 분해 트랙을 `operation.architecture.md`에 박제: 측정치(76.7K/82배)+목표(≤10배)+분해 순서(search 7K→panel→finance pivot을 frame/synth 또는 빌드레이어로, 재구현 아닌 위치이동). `moduleSizeAudit.py`를 baseline 원장으로 배선(신규 격차증가=회귀) |
| P3-2 | TEST-1 | `testLocRatio.py`에 *엔진별* 임계(viz/macro/story ≥30%) + baseline 부채원장화. 신규 분해 commit마다 해당 엔진 test 동행 강제. viz/macro는 snapshot(syrupy) 우선(무의미 단위테스트 양산 회피) |
| P3-3 | GD-3 | **첫 증명 1건**: story/builders.py(6,111줄/순수함수)를 도메인별(`builders/{revenue,capital,cashflow,quality}.py`)로 분해, registry dispatch 보존(narrate.py 분해 선례). 나머지 god는 백로그 |
| P3-4 | GD-2, GD-5 | Company `CompanyFacadeMixin` *설계 문서*(dual-access 래퍼+lifecycle+_buildFinanceSeries SSOT 추출 seam)를 본 PRD 부록에 + company-analysis-report 백로그에 트랙 추가. 17 lazy upper-import 동결원장 정당성을 operation.architecture 명문화. 실행은 점진(메서드군별) |
| P3-5 | GD-4, GD-6 | surfaces god-split(PriceChart 등 7종)를 frontend-refactor-loop 백로그에 'dedup+god-split' 트랙으로 명시. ai providers/__init__ 682줄 factory.py·cachePrefix.py 추출은 P2-5 인접 작업으로 |
| P3-6 | TEST-6, G 카탈로그 | audit 도구 65종↔관심사 매핑 카탈로그를 operation.testing에 1표(통합 아닌 *문서화* — 통합은 master red 위험). baseline↔도구 인덱스(P2-7)와 합류 |

---

## 5. 영향 파일·함수 (전 항목 file:line)

> P0/P1은 정확한 위치 확정(self-sufficient). P2/P3는 진입점+결정게이트.

**P0 (즉시):**
- `tests/architecture/test_no_raw_cross_scan.py:22,35-36` (경로+fallback)
- `src/dartlab/skills/measureProgress.py:68-69,111` (경로+glob raise)
- `tests/audit/stale_references.py:51-60` (_SCAN_ROOTS)
- `src/dartlab/mcp/protocol.py:26,30,91,99` (instructions+advertised count)
- `AGENTS.md:8` (사설경로)
- `src/dartlab/skills/{agent,catalog}.json` + generateSkills 출력부 + MCP/ReadSkill 로더 참조처
- `src/dartlab/skills/catalog.json` count + `specs/recipes/sentiment/*`(deprecated 2)
- `tests/audit/sourceDriftBaseline.py:31` + dataAudit nightly 잡

**P1 (배선):**
- `tests/audit/checkAgentBoundary.py:53-71,158-172` + `tests/run.py`(preflight 게이트)
- `tests/audit/staleImports.py` + `tests/run.py` + baseline 신규
- raw DeprecationWarning 11곳: `providers/dart/accessor/profileAccessor.py:399`, `providers/dart/accessor/reportAccessor.py:435,454,473,492,511`, `credit/__init__.py:391`, `quant/__init__.py:269,280`, `story/registry.py:1558,1565` + `DEPRECATION.md` + `deprecationAudit.py` 배선
- `src/dartlab/ai/tools/formatting.py:13-22`(_EXTERNAL_TEXT_KEYS 8키)·`:83-92`(_wrapDictTextFields)·`:309`(wrapExternalInResult) + `untrustedWrapAudit.py` + `tests/run.py`
- `tests/audit/docstring9Section.py:166-170` + `gatherGate.py:45` 패턴 복제(story/ai/analysis) + baseline 신규
- `pyproject.toml:419-420,467+` (import-linter contracts) + `tests/run.py:140-141` + 결정(통합 vs blocking)

**P2 (유령):**
- `src/dartlab/providers/__init__.py:29`(__all__) + `tests/audit/providerSymmetry.py`(본문 edinet 상수 2) + `_baselines/folderSize.json`(edinet 2)·`testCoverage.json`(edinet 1) + `core/dataConfig.py:182-188` + edinet skill/README *(providerSymmetry.json·folderMirror.json은 edinet 0 — 대상 아님)*
- `ui/web/**`(tracked 155파일=src 137+lock 등) + `package.json` workspaces + `server/__init__.py:36`(viz_router) + `src/dartlab/server/_ui_path.py:50` + `pyproject.toml:123`
- `ui/shared/**`(20파일) + `landing/vite.config.ts:281`·`svelte.config.js:218`($chart) + memory `reference_financial_graph_ssot` + `mainPlan/financial-statement-lab/03-architecture-and-reuse.md:63`
- `analysis/financial/storyValidation.py:108` + `story/publisher.py:84` + KnowledgeDB/blog_insights 추적 + operation.philosophy §6
- `src/dartlab/ai/tools/registry.py:_SPECS`(32개 중 dead 6: InspectDataset·ListEngineGaps·LookAheadGuard·ProposeRecipe·RequestUserInput·ValidateRecipe) + 구현 모듈 + `mcp/protocol.py:183-191`(ask_kernel_status)+`:9`(MCP_WORKSPACE_AGENT_TOOL_NAMES 12-tuple)
- `tests/audit/_baselines/{aiKpiV1,importLinterExceptions}.json`(삭제) + 신규 baseline 인덱스 게이트
- `tests/audit/flakyAudit.py` + `qualityHistory.jsonl` + `conftest.py:116`(SSOT 문서화)
- `README.md`↔`README_EN.md` + `tests/{eval,_evals,_drafts,calibration}/`

**P3 (분해 트랙):**
- `src/dartlab/skills/specs/operation/architecture.md`(providers 분해 순서+17 lazy 정당성) + `moduleSizeAudit.py`(baseline 배선)
- `tests/audit/testLocRatio.py`(엔진별 임계) + baseline
- `src/dartlab/story/builders.py`→`builders/{도메인}.py`(첫 증명) + `story/registry.py` dispatch
- company-analysis-report 백로그(CompanyFacadeMixin) + frontend-refactor-loop 백로그(god-split) + operation.testing(audit 카탈로그)

---

## 6. 테스트·가드 동행 (Refactor Checklist 6단계 준수)

operation.refactorChecklist = src 변경 → tests 변경 → Skills/docs 변경 동행 + 자동 게이트.

- **P0**: 각 경로 수정 후 해당 가드 직접 재실행(위반 0 유지 확인). MCP instructions 변경은 `mcp/` 테스트 + 운영자 톤 검수. JSON dedup은 ReadSkill/MCP 로더 테스트.
- **P1**: 가드 배선마다 (a) false-positive 0 증명(현 코드 전수 통과) (b) 의도 위반 1건 주입→fail 확인(가드가 진짜 무는지) (c) baseline 원장 동결. `tests/run.py preflight` 추가 게이트가 깨지지 않음 확인.
- **P2**: 제거 전 `git grep`/import 그래프로 소비 0 재확인. 제거 후 `bash tests/test-lock.sh tests/<관련> -m "<marker>"` + architecture 가드(`test_import_direction`·`test_no_cycles`·`folderMirror`·`providerSymmetry`) 통과. UI는 svelte-check 0 + 운영자 눈검수.
- **P3**: builders.py 분해는 `lint-imports`+guard index+story 테스트 동행. testLocRatio 엔진별 임계 추가 후 baseline green.
- **전역**: `uv run python -X utf8 tests/run.py preflight` 신규 failure 0. GATES dict **30개**(fast 17·full 6·nightly 7, AST 파싱 실측 — seed "27/29"·CLAUDE.md "CI 27 게이트"는 stale → P0 표면드리프트로 흡수). preflight = fast-tier blocking 부분집합. OOM 가드(병렬 agent ≤2·dartlab import 순차) 준수.

신규 가드(본 PRD 산물): rawCrossScan/measureProgress raise-on-missing · baseline↔도구 인덱스 게이트 · 엔진별 testLocRatio · moduleSize baseline · (옵션) forward-window+reconcile stage 가드.

---

## 7. 롤백 전략

- **단위**: 모든 변경은 Phase·항목별 단일 commit(`git commit -o <명시 paths>`). 즉시 `git revert <sha>`.
- **P0**: 경로/텍스트 정정이라 revert = 원상복구(동작 변화 0이었으므로 무손실).
- **P1**: 가드 배선이 예상외 master red 유발 시 해당 게이트 등록만 revert(가드 코드는 유지, 배선만 후퇴). baseline 동결은 별 commit.
- **P2**: 제거는 단일 commit이라 revert = 파일 복원. edinet/ui/web은 동결 라벨이 1차(삭제 아님)라 가역. ui/shared 삭제 전 운영자 동적사용 확인 게이트.
- **P3**: builders.py 분해는 파일 분할이라 revert로 합본 복원. import 경로 변경 다수면 분해 자체를 후속 PR로 분리.
- **금지**: force push·master 외 작업·`git add -A`. 자동생성물은 별도 "정리: 동기화" commit.

---

## 8. 이중 평가 (전문 개발자 + PM)

**전문 개발자 관점**:
- ✅ 강점: 모든 핵심 주장 ground-truth 검증(7/7), 정공법(우회 0), 스코프 절제(god-split 위임), 규칙 정합. P0이 1줄급 저위험이라 즉시 가치.
- ⚠ 위험: P1-1(checkAgentBoundary)는 false-positive 0 만들기가 어렵고 no-graph-regression 민감영역. P2-2(ui/web)·P2-4(ai.persistence)는 제품/사상 결정 선결이라 코딩 전 막힘. P2-1(edinet)은 baseline 재조정이 4 게이트에 걸침.
- 완화: P1-1은 "탐지력 유지+노이즈 제거" 균형을 의도 위반 주입 테스트로 증명. 결정 선결 항목은 PRD가 선택지를 명시(운영자 1회 답).

**PM 관점**:
- ✅ 강점: "가드망 정직화 우선"이 비-자명하고 측정가능한 thesis. 부채 28건을 4 phase로 우선순위화. 기존 23 PRD와 중복 0(갭만). 착수=운영자 go로 다른 PRD와 동일 운영.
- ⚠ 위험: 범위가 repo 전체라 "한 번에 하나" 철학과 긴장. P2/P3가 제품결정·다른 루프 위임 의존이라 PRD 단독 완결 불가.
- 완화: P0/P1을 *독립 완결 가능 단위*로 설계(가드 정직화만으로도 출시가치). P2/P3는 "결정게이트+위임"으로 명시해 PRD 경계를 정직하게 그음. MUST(P0+P1) / SHOULD(P2) / 위임(P3) 웨이브.

---

## 9. 성공·실패 기준

**성공 (MUST — P0+P1)**:
1. 죽은 경로 가드 3종(G-1·G-2·G-8) 살아있는 경로 + raise-on-missing. `scripts/`·`ops/` 참조 0.
2. 강행 가드 4종(checkAgentBoundary·staleImports·deprecationAudit·untrustedWrapAudit)이 `tests/run.py`에 배선 *또는* 명시 폐기. CLAUDE.md "기계 강제" 주장이 현실과 일치(좀비 0).
3. MCP instructions·AGENTS.md·catalog count가 실제와 일치(표면 드리프트 0). agent.json/catalog.json 단일화(wheel −1.66MB).
4. 9-섹션 게이트 분모가 공개표면으로 정밀화 + story/ai/analysis 배선. import-linter 통합/blocking 결정.
5. preflight 신규 failure 0(GATES 30=fast17/full6/nightly7 실측). 공개표면 불변.

**성공 (SHOULD — P2)**:
6. 유령 자산 8종이 격리(라벨) 또는 제거. ui/shared SSOT 메모리 정정. ai.persistence silent no-op 해소.
7. orphan baseline 정리 + 인덱스 게이트. flakyAudit SSOT 확정.

**위임 (P3)**: providers 분해 순서·17 lazy 정당성 operation.architecture 박제 + testLocRatio 엔진별 임계 + builders.py 첫 증명 1건. 나머지 god-split는 기존 루프 백로그 트랙으로 *명시*(실행은 점진).

**실패 (회귀)**:
- 공개표면(Company facade·MCP advertised·HF 경로·UI consume) 1건이라도 깨짐.
- 가드를 "배선"한다며 false-positive로 master red 방치(좀비를 다른 좀비로 교체).
- god을 일괄 분해해 import 회귀·OOM 사고.
- 자동 docstring sweep/생성 도구 신설.

---

## 10. 부록 — census 28 finding → PRD 트랙 매핑

| census ID | 메타테마 | PRD 항목 | severity | effort |
|---|---|---|---|---|
| ARCH-3 / DATA-2 | 가드환상 | P0-1 | P2 | S |
| TEST-2 | 가드환상 | P0-2 | P1 | S |
| DOC-5 | 가드환상 | P0-3 | P3 | S |
| MCP-1 / SD-1 | 표면드리프트 | P0-4 | P1 | S |
| DOC-3 / SD-3 | 표면드리프트 | P0-5 | P2 | S |
| SKILL-1 / PH-6 | 유령 | P0-6 | P2 | S |
| SKILL-2 / SD-4 | 표면드리프트 | P0-7 | P3 | S |
| DATA-3 / G-9 | 가드환상 | P0-8→P2-8 | P3 | S |
| AICORE-2 / G-3 | 가드환상 | P1-1 | P2 | M |
| CRUFT-2 / G-4 | 가드환상 | P1-2 | P2 | S |
| CRUFT-3 / G-5 | 가드환상 | P1-3 | P2 | L (가드 신규저작) |
| AICORE-3 / G-6 | 가드환상 | P1-4 | P2 | M |
| DOC-1 / DOC-2 / G-7 | 가드환상 | P1-5 | P2 | M |
| ARCH-4 | 가드환상 | P1-6 | P2 | M |
| DATA-1 / CRUFT-1 / PH-1 | 유령 | P2-1 | P1/P2 | M |
| FE-1 / PH-2 | 유령 | P2-2 | P1 | L |
| FE-2 / PH-3 | 유령 | P2-3 | P1 | M |
| AICORE-1 / PH-4 | 유령 | P2-4 | P1 | M |
| MCP-3 / PH-5 | 유령 | P2-5 | P2 | M |
| MCP-2 / SD-2 | 표면드리프트 | P2-6 | P2 | S |
| TEST-3 / PH-7 | 유령 | P2-7 | P2 | S |
| TEST-4 / PH-8 | 유령 | P2-8 | P2 | M |
| DOC-4 / SD-5 / TEST-8 | 표면드리프트 | P2-9 | P3 | M |
| ARCH-2 / GD-1 | god무게 | P3-1 | P1 | XL |
| TEST-1 | 테스트비율 | P3-2 | P1 | L |
| ARCH-5 / CRUFT-4 / GD-3 | god무게 | P3-3 | P2 | L |
| ARCH-1 / ARCH-6 / GD-2 / GD-5 | god무게 | P3-4 | P1 | XL |
| FE-3 / AISTRUCT-1 / GD-4 / GD-6 | god무게 | P3-5 | P2 | L |
| TEST-6 | 메타부채 | P3-6 | P3 | M |
| DATA-5 | 데이터무결성 | P3(옵션) | P3 | M |

**총 28 census finding → 4 phase. P0(8)·P1(6)·P2(9)·P3(6+옵션). MUST=P0+P1(가드 정직화, 독립 완결). SHOULD=P2(유령 제거). 위임=P3(god 분해 트랙).**
