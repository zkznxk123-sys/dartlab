# 01 · 현 상태 감사 — 가진 것 vs 표면화한 것 (실측)

> 본 문서의 모든 file:line 은 이번 세션 grep/read 직접 검증. 워크플로 종합 청사진이 88점에서 막힌 이유는 **근거 토대 논거를 떠받치는 4개 사실이 코드와 어긋났기 때문**이며, 그 4건을 코드로 재검증해 정정한다(§4).

## 1. story 엔진 — 가진 것 (검증됨)

| 자산 | 위치 | 실측 |
|---|---|---|
| ReportType (관점) | [`reportTypes.py:31-260`](../../src/dartlab/story/reportTypes.py#L31) | dict 12 entry. `thesis` 는 hypothesis 입력받아 sections 통째 교체([`registry.py:1574`](../../src/dartlab/story/registry.py#L1574) 근방) → 정적 투영 불가. **실효 11 관점**. 각 관점 = {sectionOrder, emphasize, focusQuestions, detail}. |
| 섹션 카탈로그 | [`catalog.py:43-78`](../../src/dartlab/story/catalog.py#L43) | 27 SectionMeta(수익구조…매크로 + improvementPlan + storyValidation + thesisReport), 6막. |
| 블록 카탈로그 | `catalog.py` `_BLOCKS` | 100+ BlockMeta(segmentComposition·marginTrend·dupont·penmanDecomposition·roicTree·breakevenEstimate·operatingLeverage·distressScore·dividendPolicy·accrualAnalysis·beneishMScore 등). |
| 6막 헤더 | `catalog.py` `ACT_HEADERS` | dict 키 "1".."6" → (title, question). [`buildStoryManifest.py:13,154`](../../.github/scripts/prebuild/buildStoryManifest.py#L154) 가 굽고 [`manifest.json:4`](../../landing/static/story/manifest.json#L4) 에 baked("제1막: 이 회사는 뭘 하는가"). |
| 기업유형 템플릿 | [`templates.py:549`](../../src/dartlab/story/templates.py#L549) `STORY_TEMPLATES` | 7종(사이클·프랜차이즈·턴어라운드·성장…), 각 {emphasize, keyQuestions, actFocus(막별 초점), industryContext, peerAxes}. 자동감지 보조. |
| 멀티포맷 렌더러 | [`formats.py`](../../src/dartlab/story/formats.py) | renderHtml(9) / renderMarkdown(311) / renderJson(419) / renderAscii(516). |
| 6축 evidence | [`sixAct.py:234`](../../src/dartlab/story/sixAct.py#L234) `sixActScore(c)` | SixActScore{6축 score + evidence(축별 evidenceIds) + notes + coverage}. `asDict()`([`sixAct.py:50`](../../src/dartlab/story/sixAct.py#L50)) → `{score, evidence, notes, coverage}`. |
| 서사 thread | `narrative.py` `detectThreads` | NarrativeThread{threadId, title, story, severity, involvedSections, evidence}. renderJson 이 이미 직렬화([`formats.py:471-482`](../../src/dartlab/story/formats.py#L471)). |
| 결정론 레이블 | `narrate.py` `_classify` | 값→임계 위치/판정 어휘(narrate.py:26/58/90 등 '양호/안전/위험/충분' 생산). |
| storyValidation | `registry.py` ~960 | `calcValuationSins`/`calcPlausibilityBand` 호출(L2 storyValidation import). Damodaran 3-test(precedents/plausibilityBand/valuationSins). |

## 2. 퍼블릭 터미널 — 표면화한 것 (검증됨)

| 표면 | 위치 |
|---|---|
| 터미널 진입 | [`landing/src/routes/terminal/+page.svelte`](../../landing/src/routes/terminal/+page.svelte) (CSR·prerender) + `ui/packages/surfaces/src/terminal/TerminalSurface.svelte`(루트 오케스트레이터). Svelte 5 runes, `--dl-*` 토큰, `.dlTerm` 스코프, lucide, Tailwind/shadcn 없음. |
| 좌측 | `LeftRail.svelte` — 통합 스크리너(스파크라인+1Y) + 워치리스트. |
| 중앙 | `CenterStack.svelte` — PriceChart(klinecharts·백테스트·매크로 오버레이) · MiniFinChart · BacktestReport. |
| 우측 | `RightStack.svelte` — Finance 탭(profitability/cashflow/debt/shareholder) · 공시팩트 패널 · 회사관계 · 스코어링/감사. |
| 다이얼로그 | MacroLensDialog(전체화면) · IndustryDialog · GradeExplainDialog · FilingSearchDialog(⌘⇧F) · GiscusPanel · SupportDialog · SourcesModal · ViewerOverlay(공시뷰어). |
| 회사 선택 | `?sym=XXXXX` → localStorage(`dlTerm.lastSym`) → featured. 헤더 topRight "토론"/"이슈" 옆 슬롯 비어 있음. |
| 데이터 진입 | `ui/packages/runtime/src/data` 단일 진입 + origins 레지스트리(hf·hfRange·newsWorker·naverWorker·localApi[예약]·duckdbHf[예약]). `loadHfJson` 으로 회사 JSON fetch. |

## 3. 갭 — 정확히 무엇이 0인가

1. **회사별 story 콘텐츠가 HF/클라에 0.** manifest 는 메타카탈로그만. → bake 필요(03문서).
2. **터미널에 narrative 렌더 표면 0.** → ReportDialog 신규(05문서).
3. **인쇄/PDF 선례 0** (@media print·window.print·jspdf 전무). → zero-dep print(05문서).
4. **NEVER-CLAIM 게이트 0** (tests/audit 에 neverClaim 게이트 없음). → claimGuard 신규(06문서).
5. **블록별 출처 라벨 0** (blocks.py 에 sourceEngine 필드 없음). → 정적 catalog 필드 신규(03문서).

## 4. ★검증된 사실 정정 4건 (심판 FATAL → 코드 재검증)

워크플로 종합 청사진이 인용한 4개 "기존 자산 재사용" 논거가 **코드와 어긋났다.** 직접 grep/read 로 재검증해 정정한다. 이 4건이 PRD 근거 토대의 핵심이므로 명시 박제한다.

### F1 — 런타임 `Section` 엔 `act` 없으나 `SectionMeta`(catalog) `act` 실재 + manifest 이미 bake → **catalog act 직접 사용**

- 실측: 런타임 [`section.py:14-26`](../../src/dartlab/story/section.py#L14) `Section` dataclass = `key/partId/title/blocks/helper/aiOpinion/aiGuide/threads/summary`, **`act` 없음**. 단 메타데이터 [`catalog.py:38`](../../src/dartlab/story/catalog.py#L38) `SectionMeta` 는 **`act: int` 필드 보유**("F1 Phase 10: 6막 매핑 명시 필드", 27 섹션 전부 act=1..6/0). [`ACT_HEADERS`](../../src/dartlab/story/catalog.py#L452) = 키 "1".."6". [`buildStoryManifest.py:102-104`](../../.github/scripts/prebuild/buildStoryManifest.py#L102) 가 per-section `partId/act/keys` 를 **manifest 에 이미 bake**(manifest.json 25 섹션).
- 정정: 6막 헤더는 partId 를 쪼개지 않고 **`getSectionMeta(section.key).act` → ACT_HEADERS[str(act)]** 로 매핑한다(act=0 메타섹션 = 헤더 없음). `partId.split("-")[0]` 는 메타섹션 partId(`IP`/`SV`/`T`)에서 깨지므로 **폐기**. 이는 **기존 catalog 필드 사용**(신규 파생 최소) — bake 가 catalog act 를 `payload.sections[].act` 로 stamp, 클라는 manifest act 와 동일값. *재정정 함의: 신규 작업이 줄었다(파생 로직 불필요, 기존 필드 읽기).*

### F2 — `sixActScore()` 는 registry 가 **호출하지 않는다** → bake 직접 호출(신규)

- 실측: `sixActScore(` grep 결과 단 2곳 — 정의 [`sixAct.py:234`](../../src/dartlab/story/sixAct.py#L234) + 호출 [`landing/_scripts/buildCompanyCharts.py:125`](../../landing/_scripts/buildCompanyCharts.py#L125). **registry.py 미호출**. (registry ~960 은 `calcValuationSins`/`calcPlausibilityBand` 호출처지 sixActScore 아님.)
- 정정: bake 가 `sixActScore(company)` 를 **직접 호출**(신규). L3 정합 — sixActScore 는 company facade(`c.credit()`/`c.quant()` 등)를 안전 조회하므로 L3 bake 에서 직접 호출 정당. "registry 가 이미 호출" 논거 폐기.

### F3 — 터미널 `EvidencePanel` 컴포넌트는 **부재** → EvidenceStrip 신규 구축

- 실측: [`sixAct.py:18-20`](../../src/dartlab/story/sixAct.py#L18) docstring 이 "evidence 는 evidenceIds list — landing/EvidencePanel 이 같은 키 row 와 join" 이라 적었으나, `EvidencePanel` grep 은 **viz spec 레이어**(`viz/spec/refs.py`·`viz/generators/core.py`·`ChartRenderer.svelte`·`KpiRibbonChart.svelte` 등)만 매치. **터미널/landing 에 렌더되는 `EvidencePanel` 컴포넌트 없음.** 같은 docstring 이 "본격 evidence 회로(rcept_no 까지)는 Phase 2 viz refs 와 정합" = 회로 미완 자인.
- 정정: 보고서의 `EvidenceStrip` 은 "기존 join 패턴 재사용"이 아니라 **기존 evidenceIds 데이터를 칩으로 첫 렌더하는 신규 구축**이다. 축②(근거완전성) 1차 천장은 "표면화율"이 아니라 **신규 구축 후 표면화율**.

### F4 — `SixActScore` 는 6축 0~100 **종합점수 레이더** → NEVER-CLAIM 준수 위해 점수 비노출

- 실측: [`sixAct.py:1-15`](../../src/dartlab/story/sixAct.py#L1) "회사간 단일 시각화를 위한 0~100 점수 … landing/company hero radar 와 viz `spec_six_act_radar` 의 데이터원". `_GRADE_TO_SCORE A=92`. `asDict().score = {axis: value}`.
- 정정: dartlab NEVER-CLAIM 은 보고서 맥락에서 **종합점수/레이더 금지**(periodic-dossier 동일 헌법). 따라서 `EvidenceStrip` 은 **6축 점수를 노출하지 않는다** — 축별 `coverage`(ready/missing) + `evidenceIds` 칩만 노출. 6축 score 는 honest-skip reject-gate 의 *내부* 신호로만 사용(화면 비노출). 기존 hero radar(landing/company)는 별도 surface 로 보고서에 import 하지 않음.

## 5. 정정의 함의

이 4건의 결과로 **"검증된 자산의 표면화"라는 핵심 주장은 여전히 참이되 범위가 명확해진다**: story 엔진 콘텐츠·sixActScore.evidence·narrate 레이블·breakevenEstimate 등은 *실재*하고(표면화 대상), 그 위에 ① **catalog `SectionMeta.act` 사용**(파생 불필요·manifest 이미 bake) ② bake 의 sixActScore 직접호출(asDict 의 `score` 는 `_internalScore` 로 분리, 화면 미참조) ③ EvidenceStrip 신규 렌더 ④ sourceEngine 정적 catalog 필드 ⑤ **per-company 직렬화 확장**(섹션→blockKey 골격은 manifest 에 이미 baked = 25 섹션 `keys`; bake 는 *회사별 present 블록 + sourceEngine + emphasized* 만 신규 emit) = **명시된 신규 작업**을 있는 그대로 계상한다. "거의 0 작업"·"이미 다 있음"이라는 과장은 폐기.
