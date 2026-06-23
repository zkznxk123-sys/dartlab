# 00. 전수조사 · 전문가 토론 · 적대 평가 원장

> 운영자 goal: "dartlab을 전수조사한다(데이터·아키텍처·덕지덕지·부채) → 약점 개선 플랜을 mainPlan에 상세 PRD로 → 여러 전문가와 토론해 기획 완전성 95점 달성까지 루프." + 추가: "전문가들 점수 **개별 95점 이상**씩, 강제 아닌 **냉정한 평가**, 95 이하면 피드백 받아 개선 반복."
> 본 원장은 그 과정·점수 이력·ground-truth 교정을 기록한다. 게이트 = **6 전문가 전원 min≥95**.

---

## 1. 과정

1. **운영자 직접 정찰** — 레포 지형·부채 원장(`tests/audit/_baselines/` 44 JSON)·Guard Index(`tests/audit/guard/`)·god 파일(moduleSizeAudit·overSplitInventory 실행)·stray(전부 gitignored 확인)·기존 PRD 포맷(data-build-workbench-ssot·macro-superstrengthen)·refactorChecklist 6단계·DEPRECATION 정책을 직접 측정. → 정량 지형 확보 후 다차원 감사 설계.
2. **7차원 심층 전수조사 워크플로**(`wf_119e02d0-b1d`, 7 finder·245 tool 호출·683K 토큰, effort high, READ-ONLY·dartlab import 금지[OOM 가드]) — 아키텍처/데이터/덕지덕지/테스트/문서/UI/AI 각자 실제 코드를 grep/wc로 측정, 기존 23 mainPlan PRD 교차참조해 *미계획 갭만* 식별. 산출 = 28 finding + 정량 지표 + alreadyPlanned 분리.
3. **운영자 ground-truth 직접 검증 7/7** — 척추 주장(죽은 경로·CI 미배선·MCP 드리프트·JSON 중복·ai.persistence·AGENTS.md·edinet)을 직접 grep으로 확인. census 환각 0.
4. **PRD 작성**(`00-prd.md`) — 5 메타테마(가드환상·유령·표면드리프트·god무게·테스트비율)로 28 finding 집약, P0~P3 phase, plan-deep 자기충족.
5. **6 전문가 적대 평가 루프**(`debate-honesty-debate`) — 아키텍트·데이터·QA/테스트·문서/DX·AI엔진·PM이 각자 *실제 코드로 PRD 주장 검증* + 6축 100점 채점. min<95면 차단 이슈를 운영자가 직접 ground-truth 재검증 후 교정→재평가. 1차 PRD **R1~R3**에 전원 ≥95(min 97) 달성.
6. **2차 census(coverage 갭 메움)** — 운영자 "모든 엔진·랜딩·프론트 다 봤나(web/blog 빼고)" 질문에 1차의 차원-중심 커버리지 갭을 인정, 5 finder로 미감사 13엔진(analysis/quant/credit/industry/synth/reference/frame/simulate/channel/cli/server/skills)+landing/src+ui-packages 전수(222 tool·565K 토큰). 38 신규 finding을 §2.8로 통합 → **R4~R5** 재평가(R4 아키텍트 importlib 차단 1건 교정)로 다시 전원 ≥95(min 97) 달성.

채점 6축: 진단정확성/20 · 우선순위ROI/20 · 스코프절제/15 · 정공법롤백/15 · 규칙정합/15 · 자기충족성/15. 게이트 = min≥95.

---

## 2. 점수 이력

| 라운드 | 아키텍트 | 데이터 | QA/테스트 | 문서/DX | AI엔진 | PM | **min** | gate |
|---|---|---|---|---|---|---|---|---|
| R1 (1차 PRD) | 91 | 95 | 95 | 93 | 95 | 95 | **91** | REVISE |
| R2 | 98 | 95 | 94 | 99 | 94 | 98 | **94** | REVISE |
| **R3** | 97 | 97 | 97 | 97 | 98 | 97 | **97 ✅** | **PASS** |
| R4 (2차 census §2.8 확장) | 91 | 97 | 98 | 97 | 99 | 98 | **91** | REVISE |
| **R5** | 99 | 98 | 97 | 100 | 99 | 99 | **97 ✅** | **PASS** |

> **2회의 정체(R1·R4)는 둘 다 *설계 약함이 아니라 정밀/정공법 정확성*이었고, 둘 다 운영자 직접 ground-truth로 교정해 통과.** R1~R3 = 1차 PRD의 file:line/카운트 정밀 오류 11건(전부 *내 PRD*가 부정확, 에이전트 환각 아님). R4 = 운영자 "모든 엔진·랜딩·프론트 다 봤나(web/blog 빼고)" 질문에 2차 census(38 신규 finding)를 §2.8로 확장하자 *아키텍트만* P1-7(importlib 가드)이 sanctioned cycle-break까지 깨뜨릴 설계임을 적발(나머지 5명은 §2.8을 ≥97로 검증). 모든 축이 전 라운드 만점이었던 곳: 스코프절제(15)·규칙정합(대부분 15). 깎인 축은 진단정확성·정공법롤백·자기충족성뿐. 정공법 = 에이전트 재라운드(환각 반복)가 아니라 **운영자가 architecture.md §172/§181을 직접 검증해 importlib 우회를 sanctioned 5 vs 진짜위반 4로 재분류**.

---

## 3. ground-truth 교정 11항 (운영자 소스 직접 검증)

### R1 차단 6건 (전부 검증 후 교정)

| # | PRD 오류 | 소스 ground-truth | 검증 |
|---|---|---|---|
| 1 | GD-2 frozen-surface 가드 `rules.py:296` | `providers/dart/rules.py` 부재, 실제는 `tests/audit/guard/rules.py:296 checkProviderCompanyFrozenSurface` + `core/protocols.py:251 CompanyProtocol`(실재) | `ls`+grep |
| 2 | GD-5 lazy import `providers/company.py:29`(col-0) | 그 파일 부재. 실제 = 메서드 본문 내부 `providers/dart/company.py` 12 + `edgar/company.py` 5 = 17(`dartlabGuard.json` baseline 라인까지) | col-0 grep=0, baseline 17 |
| 3 | SD-4 recipe **237** | `find specs/recipes -name *.md` = **243** | find |
| 4 | SD-1 advertised **22**(CANONICAL_V2 21) | CANONICAL_V2 **22** → ask+22 = **23**. `protocol.py:91` docstring "22 종"도 stale | AST tuple len |
| 5 | PH-2 ui/web **137파일** | git-tracked **155**(src 137/16,976줄, lock 8,719 별도) | git ls-files |
| 6 | G-5 DeprecationWarning **7건** | **11건**(멀티라인 `warnings.warn(`…`DeprecationWarning,`) — single-line grep 함정): accessor 6·credit 1·quant 2·story 2 | grep -A3 |

### R2 차단 5건 (전부 검증 후 교정)

| # | PRD 오류 | 소스 ground-truth | 검증 |
|---|---|---|---|
| 7 | P2-1 edinet parity = `providerSymmetry/folderMirror` baseline 등록 | 두 baseline은 edinet **0**. 실제 레버 = `__all__`(주역) + `providerSymmetry.py` 본문 상수 2 + `folderSize.json`(2)·`testCoverage.json`(1) | grep -c edinet |
| 8 | G-5 deprecationAudit.py "미배선 가드" | **파일 자체 부재**. `DEPRECATION.md:44,54,82`이 "PR 차단"한다 단언 = *가장 순수한 가드 환상*. P1-3은 배선이 아니라 **신규 저작**(effort L) | find=0 |
| 9 | 게이트 "27/29" | GATES dict **30**(fast 17·full 6·nightly 7). CLAUDE.md "CI 27"도 stale | AST 파싱 |
| 10 | PH-5 `_SPECS` **64개** | **32**(AST 키 카운트, 2x 오측) | ast.parse |
| 11 | PH-5 죽은 MCP **4종** | **6종**(InspectDataset·ListEngineGaps·LookAheadGuard·ProposeRecipe·RequestUserInput·ValidateRecipe = `_SPECS − (CANONICAL_V2 ∪ _DEFAULT_TOOL_NAMES)`). 일부는 deprecated `ask_kernel_status`로 leak | AST set-diff |

### R3 nit 1건 (비차단, 정확성 차원 교정)

| # | PRD 오류 | ground-truth |
|---|---|---|
| 12 | §5 `formatting.py:316` | `wrapExternalInResult`는 **:309**(키 :13-22·체크 :83-92) |

**교훈 박제(§2.6 PRD 측정정의 표)**: single-line grep으로 멀티라인 호출 누락(7→11) · tuple 길이는 직접 카운트(22→23) · dict 정규식 over-match→AST 키(64→32) · 한쪽 표면만 보면 dead 누락(4→6) · 가드 count 직접 AST 파싱(27→30) · "미배선"≠"미존재"(처방이 다름) · parity 강제 위치는 baseline grep 실측(가정 금지).

### 2차 census 확장 정정 (운영자 coverage 질문 → §2.8 + R4 교정)

운영자 "모든 엔진·랜딩·프론트 다 봤나(web/blog 빼고)" 질문에 1차 커버리지 갭(차원 중심이라 analysis/quant/credit/industry/synth/reference/frame/simulate/channel/cli/server/skills + landing + ui-packages 미감사)을 인정하고 2차 census(5 finder·38 finding)로 메움. 핵심 5건 운영자 직접 검증 + R4 아키텍트 차단 1건 교정:

| # | PRD 오류/갭 | 소스 ground-truth | 검증 |
|---|---|---|---|
| 13 | P2-3 live dispatcher = landing `charts.ts` | charts.ts **importer 0=죽음**. 유일 live = `surfaces/.../MiniFinChart.svelte` | grep importer 0 |
| 14 | (R4 아키텍트) P1-7 importlib "2 실위반" + 무조건 `ast.Call` 탐지 | importlib peer-cross 전수 = **sanctioned 5**(analysis→macro `architecture.md:172` 허용방향 + credit→macro/analysis 4 `:181` pattern-4 cycle-break) **vs 진짜 위반 4**(synth→frame/scan L1.5, pattern-4는 L2 전용). 무조건 탐지는 sanctioned 깸 → §172 allowlist + pattern-4 baseline 동반 필수 | architecture.md §172/§181 + importlib 전수 grep |
| - | (측정) analysis 42K·quant 21K | 실측 54K·27K (seed LOC도 과소) | find\|wc |
| - | (측정) "god=큰 파일" | forecastRevenue 548줄/86분기 god *함수*(파일 588줄 평범) | 함수-분기 밀도 |

**신규 메타발견 2종**: ① importlib 문자열 import가 AST 레이어가드를 우회(sanctioned/unsanctioned 구분 불가) = 가드 환상의 4번째 형태 ② "빌드-후-미배선" 유령 ~6-8K LOC(analysis/graph 1,147·quant transforms 719·server/api 죽은라우터 1,840·ui-pkg throw-stub 7포트 등 전부 importer 0).

---

## 4. 최종 판정

**2회 통과(R3·R5) 전부 6 전문가 전원 ≥95.** 1차 PRD R3 min 97(아키텍트 97·데이터 97·QA 97·문서 97·AI 98·PM 97). 2차 확장 PRD **R5 min 97**(아키텍트 99·데이터 98·QA 97·문서 **100**·AI 99·PM 99), blocking 0. 모든 인용 경로·줄번호·카운트를 6명이 소스와 직접 대조해 정합 확인("환각 0"). 채점은 강제가 아닌 냉정한 적대평가 — R1·R2·R4에서 합 12+ 정밀/정공법 오류를 잡아내 REVISE시키고, PRD가 byte-정확해진 R3·R5에서만 PASS.

평가가 가장 높이 산 강점: **thesis("보호받고 있다는 믿음과 현실의 간극")가 비-자명·측정가능**하고, P0=가드 배선 정정이 후속 부채감소의 전제라는 순서논리가 CLAUDE.md "Guard Index 우선" 철학과 정합. importlib 우회 봉합을 "금지"가 아니라 "sanctioned 원장화 + 미허가만 발화"로 정공법 설계(R4 교정). god-split를 일괄 안 하고 첫 증명 1건(builders.py)만 본 PRD가 지고 나머지는 기존 루프 백로그로 위임한 스코프 절제. 빌드-후-미배선 유령 ~6-8K LOC를 *배선 or 회수* 2지선다로 명시 처리.

**커버리지 = 전 엔진 + landing + ui-packages 전수(ui/web·blog만 운영자 제외).** 착수 = 운영자 go. P2 UI 제거는 운영자 push 승인 필수.

---

## 5. 구현 (as-built) — 운영자 "정공법으로 끝까지 완성" 지시 실행

> **MUST(P0+P1) 실질 완료 = 14 commit(미push).** 구현 중에도 thesis가 반복 실증됨 — *가드를 실제로 연결/사용하면 숨어있던 breakage가 드러난다*. 아래는 PRD 설계와 다른 **as-built 정정**(구현이 ground-truth를 또 도려냄) + 결정 + 보류.

### 5.1 완료 (commit)

| 항목 | commit | 핵심 |
|---|---|---|
| P0-1/2/3 죽은경로 | `60f617e07` | rawCrossScan·measureProgress·stale_references `scripts/·ops/`→실경로 + silent fallback→raise |
| P0-4 MCP 드리프트 | `890905486` | instructions 거짓 카운트(6종/canonical7/22) 제거·tools/list 정본·advertised 23 |
| P0-6 문서부 | `07bfe25ff` | 유령 index.json 제거·catalog.json 정본·agent.json=byte동일 alias 라벨 (4 spec) |
| P0-7 catalog count | `9b006a739` | count 161 정확 명문화 (SD-4 "드리프트"는 오독) |
| P0-8 sourceDrift | `710267e3e` | `[DRIFT-UNVERIFIED]` 명시 + 거짓 'nightly 게이트' 정정 |
| P0-9 recipe import | `8fe6a1fe9` | quant.{blackLitterman,meanCVaR}→quant.portfolio.* |
| P1-3 deprecationAudit | `0eee85474` | **유령 가드 신규저작** + lint 배선 (raw DeprecationWarning ratchet 9 baseline) |
| P1-7 importlib AST | `3ee193f2c`·`943b99bc9` | L2/L1.5 cross 가드에 import_module 탐지 + baseline ratchet (사각 봉합) |
| P1-2 staleImports | `b63c474df` | module-level baseline+--check 배선 + **정규식 잠재버그 수정** |
| P1-4 untrustedWrap | `84ff58af6` | --strict 배선 + wrap 키 보강(html·htmlContent·headline·excerpt) |
| P1-6 import-linter | `ea685279b` | advisory 결정 확정 + stale ignore 5 제거 + config 정직화 |
| P1-1 checkAgentBoundary | `35158d818` | **stale allowlist 정정** + 구조검사 strict 배선(FP-0)·keyword advisory 분리 |
| P1-8B testCoverageGate | `c59436d2a` | carve-out 통째 면제 → [PERMANENT]/[REVIEW] 명시 원장 |

신규 가드 wiring: lint(fast) 게이트에 `deprecationAudit · staleImports --check · untrustedWrapAudit --strict · checkAgentBoundary --strict` 4종 추가. preflight GATES 30 무결성 유지(audit-self OK). 각 가드 inject-test로 *실제로 무는지* 검증.

### 5.2 as-built 정정 — 구현이 또 도려낸 ground-truth (PRD/census가 틀렸던 것)

| # | PRD 가정 | 구현 ground-truth | 처리 |
|---|---|---|---|
| 15 | SD-3 AGENTS.md username 누출 = **공개 표면** | `.gitignore:26-27` — **AGENTS.md·CLAUDE.md 둘 다 gitignored(L-local)** = 추적 안 됨 = 외부 노출 0. SD-3 과대평가 | 로컬 정리(커밋 불가). 공개 drift는 4 Skill OS spec에만 있었고 그것만 정정 |
| 16 | SD-4 catalog 161 vs 243 = **드리프트** | `_builtinSpecPaths()` 발견 recipe **161 = catalog count, lint-drop 0**. 243 = `.archive/`(76)+README/non-spec(6) 포함 raw. **count 정확** | 드리프트 아님 → count 의미 명문화(P0-7) |
| 17 | P0-6 wheel −1.66MB 즉시 제거 | agent.json은 wheel에 실린 **공개 artifact** → 물리 삭제는 PRD 자체 게이트("공개표면 불변·제거=운영자 결정") 대상 | 문서 honesty만 실행, 물리 dedup 운영자 결정 보류 |
| 18 | P1-3 raw DeprecationWarning **11** | 11 warn문 = **9 unique 함수**(reportAccessor 5속성·quant `__call__` 2warn→1·credit·profile·story) | baseline 키=relpath::qualname 9 |
| 19 | P1-7 synth 위반 **4건** | 4 warn = **3 unique 키**(bottomUpBeta:104·277 둘 다 synth→frame.sector 동일) | L1.5 baseline 3 |
| 20 | P1-6 import-linter "100+ 위반 가시화" | 4 contract BROKEN의 **대부분이 `module→dartlab→…` PEP562 lazy facade transitive noise**(config가 "도구검사 외"라 이미 인정). 진짜 직접위반은 L2→gather raw access 잔존. **layers contract는 facade를 구조적으로 모델 불가 → blocking 불가능** | advisory가 정답(결정 강화) |

### 5.3 구현이 표면화한 **잠재 버그·숨은 위반** (thesis 실증 — 연결하니 드러남)

1. **measureProgress BOM** — 죽은 경로(scripts/)를 실경로(tests/audit/_baselines)로 재연결하자 `testCoverage.json`의 UTF-8 BOM에 `json.loads`(plain utf-8)가 깨짐. 가드가 죽어있던 동안 한 번도 안 읽혀 묻혀 있던 것 → `utf-8-sig` 내성으로 수정. 부채 total 0(거짓)→**656**(정직) 복원.
2. **staleImports 정규식 `^\s*` 버그** — `\s`가 `\n`도 매칭해 빈 줄 위의 indented import를 cross-line으로 잡아 line 번호·col-0 판정 오염(module-level 15→40 거짓). moduleLevel 추가가 표면화 → `^[ \t]*`(줄-로컬)로 수정.
3. **import-linter stale ignore 5 + 숨은 L2→L1 위반** — `predictionSignals→scan` 등 5 ignore가 dead. 제거하니 `_signalsCorporate→scan`(L2→L1.5 facade) 등 `|| pass`가 가려온 실위반 드러남 → facade 예외 문서화.
4. **checkAgentBoundary stale allowlist** — `agent_gateway.py`(snake)가 `agentGateway.py`(camel)로 rename됐는데 allowlist stale → legit WorkbenchLoop 호출 2건 FP. + runWorkbench(sanctioned 러너) 누락. allowlist 정정으로 FP-0.

→ **모두 "가드 환상" thesis의 추가 증거**: 가드가 죽어있거나 미배선이면 그 안의 버그·stale·숨은 위반이 영영 안 드러난다. 연결/배선이 곧 발견.

### 5.4 결정 (좀비 가드 금지 원칙 적용) — 부정확 배선 **거부**가 정공법

- **P1-5 (docstring 9섹션 story/ai/analysis 배선) = 명시 거부.** 측정: 비-underscore 함수 story **286**·ai **293**·analysis **360** vs 실제 공개표면(`__init__ __all__`) **29·5·0**. non-underscore 분모로 배선하면 ~900 내부헬퍼를 baseline = PRD가 명시 경고한 *형식주의 함정*. 설계원칙 2("좀비 가드 금지: 살려서 배선 **or** 명시 폐기")에 따라 부정확 분모 배선을 거부. 정밀 분모(capabilityRefs ∩ __all__)는 L-effort 별도작업으로 명세. **노이즈 가드를 켜는 것보다 안 켜는 것이 정직.**
- **P1-8A (landing checkUiDataWiring 편입) = 보류.** 동시 세션이 landing/src를 격렬히 churn 중 + landing은 UI라 push 운영자 승인 필요. 충돌·승인 위험으로 트리 안정 후 별도 진행.

### 5.5 push 보류 (확정)

origin/master 대비 15 commit ahead인데 **동시 세션의 UI 커밋이 interleave**(`a4caa1205` /cards 캐러셀·`6dd7e261a`). git push는 브랜치 전체를 보내므로 내 non-UI 커밋만 분리 불가 → 동시 세션 UI를 운영자 승인 없이 push하게 됨(UI push 규칙 위반). **따라서 push 보류** — 운영자 UI 승인 시 내 커밋이 함께 올라감. 내 작업은 master에 커밋되어 안전(reflog 선형).

### 5.6 잔여 (운영자 결정/위임)

- **P2 유령 제거 전부 = 운영자 제품결정 게이트**: edinet 동결격리 · ui/web 운명(폐기 vs 이관) · ai.persistence(부활 vs 박제) · 죽은 MCP 6종 · agent.json 물리 dedup · orphan baseline · flakyAudit 폐기 · README_EN 동기화 · 빌드후미배선 ~6-8K LOC 배선/회수. *모두 공개표면 또는 사상 결정 동반이라 단독 실행 부적합.*
- **P3 god 분해 = 트랙 박제(이미 PRD/architecture.md에 순서·추적가드 명문)·실행은 기존 루프 위임.** P3-3 builders.py 첫 증명 1건만 본 PRD "do" 대상 — 별도 안전 구간에서 진행.
- **P1-8A·P1-5 정밀분모**: 위 5.4 사유로 보류/별도.
