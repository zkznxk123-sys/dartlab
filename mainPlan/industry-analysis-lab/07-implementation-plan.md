# 07. 구현 플랜 — gap-closure (재조사 없이 착수 가능)

상태: 구현 플랜 v1 (2026-06-17, 5구멍 조사 → 4렌즈 토론 → 적대 critic → 수렴). 00~06 비전 PRD를 *착수 가능* 수준으로 끌어올린다.
목적: 06-14 비전 PRD의 5개 미완 구멍(로컬 데이터흐름·Skill OS 동기화·테스트/롤백·측정 AC·미해결 선결)을 file:line touchpoint + 테스트 매핑 + 롤백 + 측정 AC로 닫는다.
방법: 11에이전트 워크플로(조사 5·토론 4·적대검증 1·수렴 1). critic verdict=gaps-remain의 mustFix 5건 전부 반영, 토론 KILL 전부 미채택.

> ★이 문서는 코드실측으로 **00~06과 06-17 1차 정정의 사실오류 3건을 추가로 정정**한다 — (a) marketShare는 "producer 전무 inert dead"가 아니라 *실생산 + 로컬 날조*, (b) 로컬 격자/hop walk는 "EXTEND 배선"이 아니라 *신규 데이터 채널*, (c) edges 642·7.9x·2%→43%는 *재빌드 전 미검증 추정*. 충돌 시 본 문서가 SSOT.

---

## 0. 단일 최대 정정 — 데이터 의존 게이트

비전 PRD는 Phase A(profit-pool)·B(공급망)를 "신규 데이터 0 / 추출 보강"으로 독립 제시했으나, 실측상 **로컬 hop walk와 공급망 evidence는 edges 빈곤에 데이터 의존**으로 묶인다:

- `landing/static/map/industries/{id}.json`의 `edges[]`는 **옛 markdown 세대 라벨**(docs/docs_table/network, panel_text/panel_table 아님)을 그대로 갖고, semiconductor 실측 `amount 3/80·ratio 1/80`으로 거의 비어 있다.
- 따라서 **profit-pool 버블**(stages[].nodes per-node `revenue×opMargin`, edges 무관)만 Phase A 선행 가능. **RightStack hop walk·공급망 ratio/amount**는 구멍3 `Industry().build()` 재빌드 진단 *이후*로 게이트(빈 edge로 BFS 짓는 헛수고 차단).
- 34산업 전부 같은 세대인지는 semiconductor 1건만 실측 — 재빌드가 일괄 갱신한다.

---

## 1. 구멍별 gap-closure

### 구멍 1 — 로컬·퍼블릭 터미널의 산업 데이터 채널 부재 (신규 채널, EXTEND 아님)

**실측 메커니즘**: 데이터 흐름은 셸별 두 갈래.
- 퍼블릭 터미널: `landing/src/lib/terminal-shell/routeLoad.ts:37-50`이 8개 JSON(finance·macro·meta·quarters·prices-snapshot·search-index·ecosystem·industryStats)을 `loadJson`(static base→HF 폴백) 병렬 로드해 RawData 조립. `eco=map/ecosystem.json`(전종목), `industryStats=map/industryStats.json`(p10~p90). **`map/industries/{id}.json`은 터미널이 전혀 fetch 안 함**(/industry/[id] 라우트 전용).
- 로컬 터미널(`env.kind==='local'`, :8400): `ui/web/src/features/terminalSvelte/localTerminalData.ts:318-385 buildRaw()`가 단일사 응답에서 RawData 합성 — `eco.nodes`=1개(line 379), `industryStats=null`(382), index 1행. **산업 모집단이 구조적으로 없음.**
- `RawData`(types.ts:179-189)에 `edges`·`industryFlows` 필드 부재. `EcosystemFile.industryFlows`는 `unknown[]` 선언만, `RawData.eco`는 nodes만 소비.
- 진짜 소스 = `map/industries/{id}.json` 단일 파일이 `stages[].nodes[]`(revenue·opMargin·stage·stream)와 최상위 `edges[]`(from/to/type/amount/ratio/confidence)를 **둘 다** 담음. `loadJson`이 이 경로를 `hasHfLandingJson`으로 인지(`dartlabData.ts:28-46`)→base static + HF 폴백 기존, **로컬도 백엔드 0으로 브라우저 fetch 가능**.

**판정**: EXTEND 아닌 **신규 lazy 데이터 채널**. 근거 — RawData에 edges 필드 부재, routeLoad가 industries/{id}.json 미로드, runtime `map` 포트는 양 셸 throw 게이트(`createPublicRuntime.ts:178`·`createLocalRuntime.ts:70`). 단 fetch 인프라(loadJson HF 폴백)·정적 데이터·소비 컴포넌트 골격은 REUSE.

**정공법 결정**:
- `RawData` 타입 **불변**(edges/industryFlows 추가 금지 — 단일사 계약 보존). 회사 전환 시 현재 종목 industry **1개분만** lazy `loadJson('map/industries/'+id+'.json')`(34개 prefetch 금지).
- 신규 `ui/packages/surfaces/src/terminal/lib/industryPool.ts` — `engine.ts`(raw 클로저) **밖**에 격리. Phase A 책임은 **파싱 + stage 롤업으로만** 좁힘.
- hop2 BFS를 브라우저에 **재구현 금지**(over-eng KILL) — 엔진 `computeHop2` 산출을 표시층으로만(03 §4 dual-source SSOT 일관). `IndustryEdge`/hop 타입은 Phase B 지연(YAGNI). Phase A 신규 타입은 `IndustryStageRollup` 1개만.
- 로컬 profit-pool 버블은 "현재 종목 산업 그래프 내부"에서만 동작(`eco.nodes=1` 독립)을 단일사 제약으로 명문화.

**touchpoints**:
| 파일 | 변경 |
|---|---|
| `ui/packages/surfaces/src/terminal/lib/industryPool.ts` (신설) | industries/{id}.json → IndustryPool 파싱·롤업. Phase A=stage별 Σ(node.revenue×node.opMargin/100)/Σ(node.revenue) + coverageRatio(opMargin 보유노드/전체노드). edges 정규화·hop은 Phase B. |
| `terminal/lib/types.ts:111-189` | RawData 불변. Phase A에 `IndustryStageRollup` 1개만 추가. IndustryEdge 필드 Phase B 지연. |
| `landing/src/lib/terminal-shell/routeLoad.ts:37-50` | 8개 병렬 로드에 넣지 말고 **회사 전환 핸들러**에서 lazy `loadJson('map/industries/'+id+'.json')`. |
| `ui/web/src/features/terminalSvelte/localTerminalData.ts:318-385,799-810` | buildRaw() 불변. `seed.meta.sector→industryKey`(line 799)로 도출한 id로 lazy fetch, `LocalTerminalRuntime.industryPool` 채널 보관. industryKey 8산업 외 misc 폴백 시 격자 미표시. |
| `terminal/panels/CenterStack.svelte` | Phase A profit-pool 인터랙티브 버블(기존 stage 섹션 축 확장, 새 패널 금지). |
| `terminal/panels/RightStack.svelte:485-507` | **Phase B(재빌드 진단 후)**: ego relations→엔진 산출 hop walk 표시. 브라우저 BFS 금지. |

**테스트**: `tests/industry/test_financials_sanity.py::TestProfitPoolDerived`(엔진 캐논, 합성 fixture) · `tests/industry/profitPoolParity.mts`(신설, 구멍4) · svelte-check + build.
**롤백**: Phase A = industryPool.ts 신설 + 양셸 lazy 배선 + CenterStack 버블 각각 격리 변경단위. RawData 미변경이라 회귀 표면 최소, git revert로 단일사 터미널 무손상. Phase B hop walk는 재빌드 진단 후 별도 단위.
**측정 AC**: (1) 회사 전환 시 industries/{id}.json **1회** fetch(34개 prefetch 0, 네트워크 탭 1요청), (2) types.ts diff에 edges/industryFlows 추가 **0건**, (3) industryPool.ts가 stage Σ(rev×OM/100)/Σrev + coverageRatio 반환, (4) 로컬 단일사에서 버블이 자기-산업 그래프로 렌더, (5) hop walk는 재빌드 후 source 라벨 panel_* 전환·amount non-null 실측 *이후*에만 착수.

---

### 구멍 2 — 공개 SSOT 동기화가 EXTEND touchpoint에서 누락

**실측**: PRD 03 §2 EXTEND 표가 `edges()`·`buildIndustrySummary` 컬럼/인자 추가만 적고, 공개 SSOT 3종(SKILL.md 반환/호출 섹션·catalog/agent.json bodyPreview 드리프트·apiContract forbidden)을 누락. SKILL.md 자체가 반환 컬럼을 문서화하므로 컬럼 추가 시 자기위반.

**정공법 결정** (★critic mustFix — 토론 시니어 렌즈의 "600 vs 1500 컷길이별 부분 재생성" 정밀화는 **실측 반증으로 채택 거부**):
- `artifactSync.py:99`에서 agent.json은 catalog와 **동일** `_searchDoc`(body[:1500])을 씀("catalog 와 동일 직렬화, 소비자만 다름"). `:210`의 body[:600]은 agent.json이 아니라 별 직렬화(graph/mcp 계열) 소속. 따라서 **catalog.json·agent.json은 SKILL.md 본문 편집 시 함께 드리프트**하고 graph/mcp/web/pyodide는 직렬화 방식 상이.
- 결론: **SKILL.md 1자라도 본문 편집 시 `syncArtifacts(write=True)` 전수 재생성이 안전** — 컷길이별 부분 재생성 가정 자체를 버린다. 어느 JSON이 실제 드리프트하는지는 write 후 diff로 확정(openRisk).
- 동기화는 운영자 수동 `syncArtifacts(write=True)`→별도 "정리: skills 카탈로그 동기화" commit(자동 호출 금지, `test_no_auto_callers`).
- 선행 위생(financials.py docstring `공정` 오기·SKILL.md 표기 불일치)은 컬럼 추가와 **같은 commit**(별도 위생 commit은 과분할 KILL).
- apiContract 본문 변경 불요(인자 확장은 새 진입점 아님)이나 `apiContract.md` forbidden 준수의 전제로 SKILL.md 갱신이 묶임.

**touchpoints**:
| 파일 | 변경 |
|---|---|
| `src/dartlab/skills/specs/engines/industry/SKILL.md` | summary 반환 실명 정정(공정→stage·매출합계→매출(조)) + 영업이익률(%)/coverageRatio 추가 + edges() 반환 블록(amount/ratio) 신설 + EngineCall args에 hop/insights 행. |
| `src/dartlab/industry/__init__.py:295-333` | edges() docstring Parameters에 hop/insights kwargs(camelCase), Returns에 거래액/의존도(%). |
| `src/dartlab/industry/build/financials.py:243,320` | buildIndustrySummary docstring Returns를 실제 select 컬럼으로 정정 + 영업이익률(%)/coverageRatio 명세. |
| `src/dartlab/skills/catalog.json·agent.json (+mcp/web/pyodide/graph)` | SKILL.md 편집 후 `syncArtifacts(write=True)` 6 JSON 전수 결정론 재생성. 별도 "정리: 동기화" commit. **컷길이별 부분 재생성 금지.** |
| `03-architecture-and-reuse.md:44,46,97` | EXTEND 표 두 행에 SSOT 동기화 touchpoint 추가 + §6.1 `generateSkills`→`syncArtifacts(write=True)` 정정. |

**테스트**: `tests/skills/test_artifact_sync.py`(write_then_check_clean·check_detects_drift·no_auto_callers) · `tests/audit/docstring4Section.py` + `lint_camelcase_ast.py`(hop/insights camelCase).
**롤백**: SKILL.md/docstring 편집 1 commit + 6 JSON 재생성 별도 commit, 각각 git revert 독립. 미재생성 시 test_artifact_sync fail로 push 차단(드리프트 조용한 통과 0).
**측정 AC**: SKILL.md 본문 편집 후 syncArtifacts(write=True) 시 test_artifact_sync 전체 green, 미실행 시 check_detects_drift fail로 가드 입증.

---

### 구멍 3 — edges.json 642 vs 132 미진단 + 레버 A/C 졸업상태 + 재빌드 롤백

**실측**: `edges.py:424-425` docstring "642 precise"는 **1곳·검증 테스트 0건**, 디스크 132는 옛 markdown 세대값. 레버 A는 `_attempts ②까지만`, 레버 C(매출처 표)는 데모 0·customer 엣지 7건 전원 amount/ratio=None.

**정공법 결정** (★critic mustFix — 642·7.9x·2%→43%는 **재빌드 전 미검증 추정**):
- 재빌드 **2단계 강제**: 운영자가 `Industry().build()`(`__init__.py:286→pipeline.buildIndustryMap`, skipDocs=False)를 메모리 가드(병렬 agent≤2·회사 순차) 하 1회 실행 → 산출물 **먼저 검증**(source 라벨 panel_text/panel_table 전환·amount non-null 카운트 642 vs 132 확정·nodes.json 동반 회귀 diff) → **그 후에만** commit. 깨진 부분산출물의 mapBuild/HF landing 전파 차단.
- **nodes.json 동반 덮어쓰기 명시**: `_saveNodes`가 nodes.json(2026-05-10 신선본)도 갱신 → 롤백 = git revert **2파일**.
- 레버 A 본진 이관은 ③~⑧ 졸업 완주 후: `edges.py:506-507` exact lookup(`r.get('매입액')/r.get('비중')`)→데모(`leafSupplierCoverageDemo.py:122-128`)처럼 퍼지 + 합쳐진 셀 `parsePercent`, `512-513` 상장-only 드롭→**buyer-centric leaf supply fact**(비상장 매입처 amount/ratio 보존, 그래프 노드 승격 아님), 회귀테스트 동행, edges.json 재빌드를 같은 변경단위.
- **leaf fact 배선 경계 명문**(정직 렌즈): leaf supply fact는 그래프 엣지 아님 → `buildIndustryMap.py` atlas/ecosystem flow amount 집계에 미진입.
- **레버 C = Phase B 범위에서 KILL**(데모 0·customer 전원 None), 별도 `_attempts ①카테고리`부터.
- `edges.py:425` docstring 642는 재빌드 실측값으로 정정, 회귀 테스트(현 0건) 동행. 04 §1 내부 충돌(0.7% vs amount 가중 4.1%)·7.9x·2%→43% 전부 "재빌드 전 추정·미검증" 딱지 — 실측 후에만 사실 톤.

**touchpoints**:
| 파일 | 변경 |
|---|---|
| `edges.py:506-507` | exact 컬럼 lookup → 퍼지(데모 122-128 이식) + 합쳐진 셀. ratio 복구. 레버 A 졸업 후. |
| `edges.py:512-513` | 상장-only 드롭 → buyer-centric leaf supply fact. atlas flow 집계 미진입 경계. |
| `edges.py:424-425` | docstring 642 → 재빌드 실측값 정정. 회귀 테스트 동행. |
| `src/dartlab/industry/edges.json + nodes.json` | 운영자 수동 build 재빌드 후 검증→commit. 2파일 git-tracked, 롤백=git revert 2파일. |
| `pipeline.py:192-201` | buildAllEdges→_saveEdges/_saveNodes 재실행 경로(Industry().build() 통해서만). 비용 운영자 실행 전 미측정. |
| `04-data-readiness-kill-list.md:16-17` | amount 132·ratio 19·642·7.9x·2%→43%에 "재빌드 전 추정·미검증" 딱지 + 재빌드 후 실측 SSOT. |
| `tests/_attempts/industryAnalysisLab/` | 레버 A: 데모→edges.py 이식 + 본진 회귀테스트(③~⑧). 레버 C: Phase B 제외, ①부터. |

**테스트**: `tests/industry/test_edges.py`(신설) — 재빌드+레버 A 후 Industry.edges() 거래액·의존도(%) 컬럼 + hop=2/insights, `loadEdges` monkeypatch(`test_overrides_exclude.py:28` 패턴) 합성 edge. amount 행 lift를 **production 함수로 재현**(데모 재구현 아님). 재빌드 진단 자체는 운영자 1회 수기.
**롤백**: edges.json/nodes.json 단독 "정리: edges 재빌드" commit→git revert(2파일). 단 mapBuild dispatch 1사이클로 HF landing 재발행(롤백 시에도 재발행). 레버 A 코드 이관 별도 단위.
**측정 AC**: 재빌드 후 (1) source 라벨 panel_* 전환, (2) amount/ratio non-null 카운트 PRD 실측값 기재(옛 132/19 삭제), (3) nodes.json 회귀 diff 후 commit, (4) 레버 A 이관 시 test_edges.py가 production extractRawMaterialEdges로 amount 행 증가 재현, (5) 레버 C는 Phase B AC 제외.

---

### 구멍 4 — Phase별 테스트 매핑·dual-source 패리티 러너·롤백 부재

**실측**: surfaces vitest 0·첫파티 .test.ts 0. dual-source 패리티 받을 프론트 러너 없음.

**정공법 결정**:
- Phase A 캐논 = `tests/industry/test_financials_sanity.py::TestProfitPoolDerived`(합성 nodes/finance fixture, parquet 무의존: 영업이익률(%)·coverageRatio 동결 + revenue-weighted Σopinc/Σrev≠per-node평균 케이스 + coverageRatio 분모=finance-join노드/전체노드 단언).
- 브라우저 dual-source 게이트 = 신설 `profitPoolParity.mts`(`tests/parse/browserXlsxParity.mts` 패턴 복제). ★critic mustFix 2건:
  - (a) 단언 방향 = "tolerance 완전일치" **아님** → **"양 경로 coverageRatio 분모가 다르면 화면 라벨이 그 차이를 노출하는가"**. (opMargin 82.4% 노드 가중 vs finance-join Σ/Σ는 분모 모집단이 달라 같은 값 불가 — 완전일치 강제는 거짓 실패 + 커버리지 은폐.)
  - (b) profitPoolParity.mts가 import할 브라우저 롤업 로직이 `+page.svelte` 인라인뿐(추출 0) → **industryPool.ts로 ts 추출이 선결**.
- Phase B edges() = `test_edges.py` 신설(구멍3). calcs/concentration.py 승격 = `test_l2_pure_functions.py:88-160,287` + `enrichCompany.py:270` import re-point을 **같은 commit**. shim 여부는 recipes.industry deep-import grep 후 결정.
- **.mts CI 미배선 처방 충돌**(시니어=배선 시도 / over-eng=배선 동반 시에만 / PM=수동줄 필수)은 **운영자 단일 결정**으로 06 §4 고정 — 합의 아닌 운영자 결정 항목(`table-export browserXlsxParity.mts`가 이미 같은 부채).
- 합성 fixture만(메모리 가드 PYTEST_MEMORY_LIMIT_MB=1900), 실 panel 로드는 `requires_data` 마커로 preflight 분리.

**touchpoints**: `tests/industry/test_financials_sanity.py`(TestProfitPoolDerived) · `tests/industry/profitPoolParity.mts`(신설) · `tests/industry/test_edges.py`(신설) · `test_l2_pure_functions.py:88-160,287`+`enrichCompany.py:270`(승격 re-point) · `06-progress-ledger.md:67`(§4 게이트 명문화).
**테스트 편입**: 기존 industry 테스트 전부 합성 unit → `test-fast`(`run.py:185 -m 'unit and not requires_data'`) 자동 편입, GATES 수정 불요. 단일=`bash tests/test-lock.sh tests/industry/test_financials_sanity.py -m unit -v`. `.mts`는 preflight 미포함 → 06 §4 수동 실행줄 `npx tsx tests/industry/profitPoolParity.mts`(CI 배선=운영자 결정).
**롤백**: edges 재빌드 단독 commit→revert(nodes 동반). calcs 승격 import 경로 1 commit(로직 이동이라 revert 깨끗). Phase A 파생 financials.py select 1 commit. 모두 git-tracked, /tmp 백업 불요.
**측정 AC**: (1) TestProfitPoolDerived가 test-fast 자동수집 green, (2) profitPoolParity.mts가 coverageRatio 차이 라벨 노출 단언(완전일치 아님), (3) calcs 승격 후 import re-point 동행 green, (4) 신설 테스트 합성 DataFrame만(메모리 가드 위반 0), (5) .mts 처방이 06 §4 단일 결정 고정.

---

### 구멍 5 — Phase C framing 오류 + marketShare 사실오류 + compare 범주오류

**실측** (★06-17 1차 정정 + 비전 PRD 사실오류 정정):
- "백분위 3분기 분기" framing 오류 — `engine.ts:179 pctRank`는 모집단 무관 순수함수, `industryPercentile(492)`·`percentileIn(501)` 둘 다 `buildFundMetrics→pctRank` **공유**, industryStats는 band 표시용(순위 무참조). 실측상 "3갈래"가 아니라 **1개 산식 + 모집단 파라미터화**.
- **marketShare 사실오류**(06-17 1차 정정이 틀림): `buildIndustryMap.py:816 share=revenue/total*100`·`:868 marketShare 기입`으로 **실생산**, ecosystem.json에 실재(grep 1건). `localTerminalData.ts:348`이 로컬 단일사에 **marketShare:100 하드코딩**(날조). 즉 "producer 전무 inert dead·null→'—'"는 사실오류 — 실제는 *라벨 사칭(상장사 상대비중을 "점유율"로, 04 EXCLUDED·§3-8 분포≠공식지수 위반) + 로컬 100 날조*.
- `EcoNode`(types.ts:120)는 `routeLoad.ts:46`이 퍼블릭 터미널 RawData로 로드하는 **퍼블릭/로컬/landing 공통** 타입 — `landing map/+page.svelte:236`(metric 9)·`compare/+page.svelte:82`가 같은 키 소비.
- compare(05 funnel)는 `compare.py` percentile 토큰 **0건**(셀 정렬 매트릭스) — 백분위 통일 항목에 묶은 건 범주오류.

**정공법 결정**(★2026-06-17 3렌즈 토론 만장일치 — 기존 "터미널 표시 제거"를 **전 소비처 정직 재라벨**로 격상): Phase C를 "백분위 3갈래 통일"에서 **(a) 경계 문서화 (b) compare 범주오류 정정 (c) marketShare 라벨 사칭 정직 재라벨**으로 재프레임(framing kill).
- ★**marketShare = 제거 아닌 재라벨**. 값(buildIndustryMap.py:816 `share=revenue/total*100`)은 *정직한 양*(상장사 풀 내 상대 매출규모)에 *거짓 이름*("점유율"/market share)만 붙은 것 — 멀쩡한 metric(TreemapView 크기·scan industry-leader 프리셋·정렬)을 죽이면 over-eng+기능회귀+경계침범(scan/map 소유). 정공법 = **이름만 `상장사매출비중`(en `rev share(listed)`)으로 교정, 키·metric·preset·동작 전부 보존(회귀 0)**. 04 EXCLUDED("상장사 매출=시장규모 근사만")·§3-8("분포≠공식지수")와 정확 합치.
- ★**전 소비처 포함**(터미널만 아님 — 사칭은 값에 붙지 화면에 안 붙음, 외부 사용자 보는 퍼블릭 map 사칭 유지=정직정책 자기모순). 단 **라벨 문자열만** 교정이라 SSOT 경계(scan=횡단스크리닝·map=산업맵 소유) 무충돌 — metric 삭제·재구현 아님. 다른 PRD 소유 화면은 **별도 변경 단위**로 분리(아래 commit 단위).
- ★**로컬 100 = 값 제거**(재라벨 불가). localTerminalData.ts:348 `marketShare:100`은 단독 유니버스(peer 1사)라 분모=자기자신 = 동어반복 날조 → 값 미설정(undefined). `industryRank:1`·`industryPeerCount:1` 동반 제거(같은 날조). optional 필드라 소비처 자동 '—' 폴백(회귀 0).
- compare(05 funnel) = 백분위 통일에서 분리 → fin-stmt-lab/compare "셀 정밀 비교" 교차참조로만.
- `useStatsBand` 이원화(퍼블릭 industryStats prebuilt vs 로컬 quantileBand 라이브)는 **의도된 설계** → `engine.ts:404-406` 주석을 industry SKILL.md 경계 SSOT로 승격(제거 아님).

**touchpoints (소유 경계별 변경 단위)**:
| 변경 단위 | 파일 | 변경 |
|---|---|---|
| CU1 [터미널/industry-lab] | `CenterStack.svelte:194/198`·`ScreenerModal.svelte:42`·`types.ts:120` | 라벨 '점유율/M.SHARE'→'상장사매출비중/LISTED REV%'·'rev share(listed)'. 키·num accessor·필드 보존 + 주석 1줄. |
| CU2 [퍼블릭 map·/map 소유] | `map CompanyCard.svelte:498/776`·`TreemapView.svelte:180`·`landing map/+page.svelte:994`·`compare/+page.svelte:82` | '점유율'→'상장사매출비중' 라벨만. 크기/색/정렬 기능·키 불변. landing map 수동 회귀 검수. |
| CU3 [scan·scan 소유] | `scan/metrics.ts:113/117`·`presets.ts:144` | label '점유율'→'상장사매출비중' + definition 정직화. metric key/conds/sorts/cols 불변(industry-leader 프리셋 보존). |
| CU4 [로컬 날조 제거] | `localTerminalData.ts:348/353/354` | marketShare:100·industryRank:1·industryPeerCount:1 제거(undefined). 소비처 자동 '—'. |
| CU5 [데이터·build 소유] | `buildIndustryMap.py:803/816/868` | 산출 주석 '상장사매출비중(시장점유율 아님)' 정정. 키명·산식 불변. |
| `engines/industry/SKILL.md` | 백분위 SSOT 경계 박제(band 이원화=의도된 설계). 구멍2 SKILL.md 편집이면 syncArtifacts 묶임. |

**테스트**: 순수 표시층 → svelte-check + build (터미널/landing) + ui/web build (CU4). compare 범주오류·band 경계 = 문서 변경.
**롤백**: 변경 단위별 git revert. 라벨 교정이라 데이터층 무손상, 로컬 값 제거는 optional 필드라 소비처 가드로 안전.
**측정 AC**: (1) 코드에 "점유율"(marketShare 맥락) 0건(grep), (2) types.ts:120 필드 보존, (3) TreemapView 크기 옵션·scan industry-leader 프리셋·compare 행 **기능 무손상**(키 불변), (4) 로컬 단일사 카드에서 상장사매출비중/순위 '—' 표시(날조 0), (5) 라벨 길이 변화('점유율'3→'상장사매출비중'7) 시각 회귀 운영자 눈검수(특히 CenterStack stat grid·ScreenerModal 헤더·TreemapView 버튼).

---

## 2. openRisks (착수 전 인지)

1. industries/{id}.json edges 옛 세대(docs/docs_table·amount 3/80·ratio 1/80, semiconductor 실측) — hop walk edge 가중은 구멍3 재빌드 *이후*에만 의미. 34산업 전부 같은 세대인지 1건만 실측(재빌드가 일괄 갱신).
2. `Industry().build()` 전종목 재빌드 메모리·시간 비용 미측정(`pipeline.py:121` "비용 큼"만). 메모리 가드 하 완주 가능 여부 운영자 1회 실행 전 미상 — OOM 시 부분산출물 오염을 2단계 검증→커밋으로만 방어.
3. `.mts` CI 미배선 처방 3렌즈 충돌 + table-export 같은 부채 — **운영자 단일 결정 필요**. 수동줄은 사람이 빼먹으면 dual-source 회귀 조용히 통과.
4. mcp/web/pyodide/graph.json이 edges()/summary 반환 컬럼을 본문에 담는지(_mcpDoc/_webDoc 직렬화) 추가 실측 미완 — 보수적으로 SKILL.md 편집 시 syncArtifacts 전수 재생성, 실 드리프트는 write 후 diff로 확정.
5. build/insights.py→calcs/concentration.py 승격 re-export shim 필요 여부는 recipes.industry deep-import grep 후 결정 — 미grep 상태.
6. profit-pool dual-source(엔진 finance-join Σ/Σ 캐논 vs 브라우저 opMargin 82.4% per-node) 분모 모집단 상이 — coverageRatio를 양 경로 라벨에 노출 안 하면 확신오정렬. 완전일치 강제는 거짓 실패.

---

## 3. 운영자 단일 결정 항목 (합의 아님)

1. **`.mts` CI 배선 vs 수동줄**: profitPoolParity.mts를 `run.py` GATES에 배선할지, 06 §4 수동 실행줄로만 둘지. (table-export browserXlsxParity.mts 선례 = 미배선 부채.)
2. **`Industry().build()` 재빌드 실행 시점**: Phase B 첫 작업, 메모리 가드 하 운영자 직접 실행(2단계 검증→커밋). 비용 미측정이라 OOM 위험 인지 후 go.

---

## 4. 착수 순서 (선결조건 게이트 반영)

- **Phase A** (선결 0, 신규 데이터 0): 구멍2 위생(SKILL.md/docstring 정정 + syncArtifacts) → 구멍1 profit-pool 버블(industryPool.ts 신규 채널 + 양셸 lazy + CenterStack, **edges 무관**) → 구멍4 TestProfitPoolDerived + profitPoolParity.mts(ts 추출 선결) → 구멍5 marketShare 정직 재라벨(전 소비처)·로컬 날조 제거 + Phase C 재프레임 문서.
- **Phase B** (구멍3 재빌드 진단 선결): `Industry().build()` 2단계 재빌드 → 642 vs 132 확정 → 레버 A 졸업 이관 → Industry.edges() 컬럼/인자 + test_edges.py → **그 후** RightStack hop walk.
- **Phase C** (경계 문서화 선결): 백분위 SSOT 경계 SKILL.md 박제 + compare 범주오류 정정(대부분 문서 — 산식은 이미 단일).
- **Phase D** (차단): 적응형 lifecycle 임계·가동률·세그먼트·US·DOL·레버 C — `_attempts` 졸업 게이트.
