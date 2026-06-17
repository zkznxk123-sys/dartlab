# 06. 진행 원장 (Progress Ledger)

상태: 비전 PRD v0.2 (2026-06-14, 2차 대대적 조사·적대검증 반영)
목적: 현재 결정·토론 출처·문서 상태·NEXT·메모리 포인터. 세션 간 재개 단일 진입점.

---

## 1. 현재 결정 (2026-06-14)

- **방향 확정**: A(profit-pool) → B(공급망 evidence) → C(백분위 통일) **3단계 전부**, 선결조건순 순차. 운영자 승인(2026-06-14): "3개 다 하되 순서 지켜서".
- **핵심 재구성(v0.2 정정)**: industry 엔진은 약한 게 아니라 *만들어 묻어둔* 엔진 — 단 "묻어둔"은 **함수·화면·DataFrame 노출**에 한정한다(orphan은 build/insights.py 함수가 verb/화면에 안 나옴 + /industry static JSON이 격자/밴드 미렌더 + edges() 컬럼 누락 + engine.ts marketShare inert dead). 산업 분석 *능력* 자체는 `recipes.industry/` 8 curated·validated가 이미 RunPython 런타임 가동 → 중복 신설 금지. lifecycle도 orphan 아님(industryBadge.phase 자동 부착 live). 1순위 = 묻어둔 *함수* 배선 + 정직 라벨 + 분기 통일. 신규는 profit-pool 격자 하나.
- **킬 확정**: 시장점유율·컨센서스·TAM·operational KPI·대체재·S-curve·경험곡선·platform KPI(EXCLUDED) / Porter 5힘 점수·HHI DOJ 라벨·moat 라벨·진입장벽 점수·GE 9box·7 Powers·Leontief 명명(REJECT) / profit-pool migration(코호트 노이즈 kill) / Capital Cycle·Damodaran 자본효율(OWNED-ELSEWHERE).
- **거처**: 엔진 EXTEND + 퍼블릭 `/industry/[id]` EXTEND + 로컬 터미널 CenterStack/RightStack 배선. 새 파일·verb·패널 0(집중도 함수는 calcs/concentration.py 승격이지 새 능력 아님). 엔진 리팩토링 = **design-only**([03 §8](03-architecture-and-reuse.md)).

---

## 1.05 졸업 완료 — 산업 양극화(polarization) verb (2026-06-18)

`tests/_attempts/industryAnalysisLab/` 전수 발굴(9 루트 measure-first)의 산물을 본진 졸업. **거처=엔진 EXTEND**(새 패널·새 데이터 채널 0 — `Industry().__call__` 플래그 1개 + `calcs/` 모듈 1개).

- **무엇**: `dartlab.industry(id, polarization=True)` — 산업이 *승자독식으로 갈라지나 vs 동질 평준화* 를 **독립 두 자료원 교차검증**으로 판정. ① 마진 렌즈 = 멤버 OPM IQR(p75−p25) 다년 방향 ② 밸류 렌즈 = 멤버 P/B p90/p10 분산. 둘 다 넓음→승자독식·`교차검증=일치`, 갈리면→혼재·`불일치(렌즈 갈림)`.
- **왜 졸업 1순위였나**: 루트1(마진분산, 발산 8:2)·루트3(밸류괴리, 발산 3.3x) 둘이 robust PASS + **서로 교차검증**(제약이 양 렌즈 극단 일치). 단일 각도보다 교차검증이 folk통계 방어. 실측 일치: 제약 33→78·P/B 22.5 / 반도체 13→26·11.7 / 철강=마진좁음·밸류넓음 → **불일치 정직 포착**(렌즈 갈림 자체가 통찰).
- **산출 파일**: [polarization.py](../../src/dartlab/industry/calcs/polarization.py)(9섹션 docstring·`_distribution` 재사용) + [__init__.py](../../src/dartlab/industry/__init__.py) verb 배선 + `test_financials_sanity::TestPolarization`(7 테스트: `_crossVerdict` 4 + monkeypatch end-to-end 3) + SKILL.md/web.json 동기.
- **정직 경계(코드 1급)**: 음수자본 제외수 인용·생존편향(현 멤버십 소급)·5점 윈도(방향신호)·밸류 스냅샷(시점 1)·임계는 `_attempts` 실측 분포 기반 라벨(절대 진리 아님). 점유율·인과 금지. `concentration`(산업이 과점이냐)과 직교.
- **게이트 통과**: docstring4Section·camelcase strict·industry unit 61·architecture 39(L2→L1 prices import = 방향·cycle 위반 0).
- **남은 루트(졸업 보류)**: 4 accrual(de-mean 후 PASS, 다음 후보)·2 ΔHHI/7 상대강도(BORDERLINE·가드 선결)·5 수출/8 CAR(약함/보류). 카탈로그 SSOT=`_attempts/industryAnalysisLab/ROUTES.md`.

---

## 1.1 정정 이력 (2026-06-17 코드 재실측)

**검토 세션 1차(2건)** — PRD v0.2 사실 주장 재대조:
- **recipe 개수 9 → 8**: `recipes.industry/` 실제 8개(README 1차 진입 표·Glob 일치). README·00·03·05·06 정정.
- **engine.ts 인용 드리프트**: cross-universe-percentile(06-15)이 engine.ts 리팩토링 → industryPercentile 301-312→492 이동. 02·03·05·06 정정.

**구현 플랜 세션 2차(11에이전트 워크플로 → [07-implementation-plan.md](07-implementation-plan.md))** — 5구멍 조사·4렌즈 토론·적대 critic이 1차 정정 자체의 사실오류 3건 포함 추가 정정:
- ★**marketShare "producer 전무 inert dead"는 사실오류**(1차 정정이 틀림): [buildIndustryMap.py:816/868](../../.github/scripts/prebuild/buildIndustryMap.py#L816)이 상장사 상대비중을 실생산해 ecosystem.json에 싣고, [localTerminalData.ts:348](../../ui/web/src/features/terminalSvelte/localTerminalData.ts#L348)이 로컬 단일사에 `marketShare:100` 날조 → "null→'—' inert"가 아니라 *라벨 사칭 + 로컬 날조 시정*, 제거는 표시층 한정·EcoNode 필드 보존(landing map/compare 공유). 02·03·05 재정정.
- ★**백분위 "3분기 분기" framing 오류**: engine.ts:179 pctRank 단일 산식 + 모집단 파라미터화(이미 통일) — Phase C는 "통일"이 아니라 경계 문서화·compare 범주오류 정정·marketShare 사유 교정. 02·05 재정정.
- ★**로컬 격자/hop walk = EXTEND 아닌 신규 데이터 채널**: RawData(types.ts:179-189)에 edges 필드 부재·eco.nodes=1·map 포트 throw 게이트 → industries/{id}.json lazy 신규 채널 + industryPool.ts.
- ★**edges 642·7.9x·2%→43%는 재빌드 전 미검증 추정**(642 docstring 1곳·검증 0건): 04 §1 태그 + `Industry().build()` 2단계 재빌드 선결.
- ★**시니어 dev 렌즈의 "catalog 1500 vs agent 600 부분 재생성" 정밀화는 채택 거부**(critic 실측 반증, artifactSync.py:99 agent=catalog 동일 _searchDoc): SKILL.md 본문 편집 시 `syncArtifacts(write=True)` 전수 재생성.
- 검증 통과(변경 없음): `buildIndustrySummary` 첫 컬럼 `stage`·opMargin 미포함 · `Industry.edges()` amount/ratio select 누락 · 유령 모듈 4종 미존재 · calcs 3·build 13 파일.

**구현 세션 3차 (2026-06-17 marketShare 라벨 토론, 4에이전트 → [07 §구멍5](07-implementation-plan.md))** — 2차의 "터미널 표시 제거(필드 보존)" 결정을 코드실측이 뒤집음:
- ★marketShare 소비처가 터미널 2곳이 아니라 **퍼블릭 map(CompanyCard·TreemapView)·scan(metrics·presets)·compare 까지 7곳**, 전부 '점유율' 사칭. 2차 결정은 과소 범위 + 멀쩡한 metric(트리맵 크기·scan industry-leader 프리셋) 기능손실.
- ★3렌즈 만장일치 **제거 아닌 정직 재라벨**: 값(상장사 내 매출비중)은 정직, 이름만 사칭 → 전 소비처 '점유율'→'상장사매출비중'(키·metric·preset 보존, 회귀 0). map/scan 은 라벨만이라 SSOT 경계 무침범(별도 변경 단위). 로컬 100·industryRank:1·peerCount:1 은 단독유니버스 동어반복 날조라 값 제거.

**구현 진행 (Phase A, 2026-06-17 — 커밋, push 보류)**:
- 구멍2 ✅ `buildIndustrySummary` 파생 컬럼(영업이익률·coverageRatio)+테스트(872bd2888) + SKILL.md/카탈로그 동기화(b3a0e30c8, 기존 search 부채 동반 해소)
- 구멍1 퍼블릭 격자 ✅ `/industry/[id]` profit-pool 2D + `ui-surfaces/map/industryPool.ts` rollup + profitPoolParity.mts(6a0d34666). 터미널 CenterStack 버블(신규 lazy 채널)은 후속
- 구멍5 marketShare 재라벨 ✅ CU1~CU5(5fc87658f·5feb51359·b49e1b491·36edae6ab). 문서 정정 동반
- Phase C 분포 밴드 ✅ `/industry/[id]` industryStats p10~p90 박스플롯(percentile만·n<10 숨김·분포출처 라벨, fd8506f59). 신규 계산 0
- Phase B 642 진단 ✅ (read-only, cd2bb17f4) — 헤더 드리프트(exact lookup miss)가 원인, 재빌드 단독은 ~132 정상. 레버 A(퍼지화)가 커버리지 레버
- 구멍1 터미널 CenterStack 버블 ✅ — 신규 lazy 채널 `CompanyPort.industryProfitPool`(industryPoolSource: map/industries/{id}.json fetch, relations 패턴·정적자산 공유) + `Company.industry` raw id + CenterStack '이익 풀' Panel(공정별 매출막대×영업이익률, 이익최대≠매출최대 통찰). 기반 d134430f8, 소비처는 멀티세션 `git add -u` sweep으로 4739222c4에 혼입(코드 온전·master green). svelte-check 0err·build 통과
- 구멍 Killer#2 edges() ✅ — `Industry.edges()` 거래액·의존도(%) 컬럼(빈 schema+채움, None 보존) + docstring/SKILL.md(edges 반환 블록) + test_edges 2건 + 카탈로그 sync(5aaac4e12·ebd9fd210)
- Phase B Killer#2 공개 ✅ — `/industry/[id]` 공급망 의존도(%)·출처 칩 + 정직 캡션(4418768dd)
- Phase C 경계 SSOT ✅ — SKILL.md 백분위 경계 박제(단일 pctRank·band 이원화·compare 교차참조·marketShare≠점유율) + sync(60a3c4ecc·cf23cc295)
- **묻어둔 집중도 함수 런타임 노출 ✅** (2026-06-17, 2에이전트 적대토론 → 정공법) — `build/insights.py` → `calcs/concentration.py` 승격(이력보존 git mv, import re-point: enrichCompany 1 + test_l2 6 + edges/coverage baseline) + **`Industry()(id, concentration=True)`** 모드(산업 매출 시장구조 HHI/CR3 + 상위5사, `_lifecycle` 선례 동형, verb 0) + TestConcentrationVerb 3건 + SKILL.md(concentration 반환블록·args·정직경계) + 카탈로그 sync(web.json). **설계 모호 해소**: dict↔DataFrame은 calc 함수 dict 유지(계약 불변)·verb 어댑터 `_concentration`만 DataFrame 래핑(`_summary`/`_lifecycle` 패턴). **데이터 정직 가드**: revenue 기반(viable)만 노출·"상장사 매출 기준" 캡션·HHI라벨 반독점 어휘 금지 박제.
  - ★**적대토론 핵심 발견(정직 카탈로그)**: "런타임 노출" thesis는 *상당 부분 이미 충족됨* — `calcSupplyInsights` 출력은 enrichCompany→buildIndustryMap→`CompanyCard.svelte:505-550` 화면 노출 + `buildInsightRankings.py` HHI 랭킹. orphan은 *함수가 query verb DataFrame으로 안 나오는 것*뿐. 진짜 미노출 = `calcIndustryConcentration`(산업 시장구조, recipe·화면 어디에도 없음, `calcSectorMetrics` 백분위와 직교) 하나 → 이것만 노출. supply-side(amount 0.7%)는 거짓정밀이라 의도적 보류(깎아냄).

- **레버 A 졸업 + 전사 재빌드 ✅** (2026-06-17) — 비상장 매입처 미드롭 + 퍼지헤더. ② 실측(N=300 4.6x·642 정합)→본진:
  - `IndustryNode.supplyFacts`(비상장 leaf fact, 그래프 노드 미승격·buyer 속성) + `extractRawMaterialEdges` 퍼지헤더·leaf 할당 + `calcSupplyInsights` HHI 합산(코드 `799ceb18a`, 테스트 2건)
  - ★선결 버그 발견·수정: `_listingLookup`이 gov 마이그레이션(`종목코드`→`short_code`)으로 깨져 있었음 → 현 edges.json이 *마이그레이션 전 stale 빌드*였음 판명
  - perf: `extractDocsEdges` O(회사×행×2800) → 2-gram 조기reject(`2b0b9ddad`, 110→40분)
  - **전사 재빌드 산출**(`e132fbdaf`): **amount 커버리지 132 → 1,097 (8.3x)** = 상장엣지 123 + 비상장 leaf 974. supplyFacts 260사·1,152 facts. edges 18,418→20,560(supplier 3,191→6,679, listing 복구). peak RSS 2.83GB·80분. **재빌드 비용 실측 = O(n²) 80분 → 향후 CI/운영자 배치 권장(PRD 가드 확증)**
  - 실데이터 검증: 기아 공급 HHI 2979(집중·41조), 반도체 시장구조 HHI 5778(삼성 73%)

**완결 요약**: 3 killer 사용자 대면 전부 ✅ — #1 profit-pool · #2 공급망(edges+칩+**레버A 8.3x amount**) · #3 분포. 정직(marketShare) ✅. 집중도 런타임 노출 ✅. **PRD 정의 범위(3 killer 엔진+표면+정직 라벨) 완성.**

**남은 작업 (PRD 본체 외 — 보너스/게이트)**:
- **집중도 verb 화면배선** — `concentration=True`(전사 작동)가 엔진엔 있으나 터미널/랜딩 미노출. PRD 3 killer 넘어선 보너스·UI(검수 게이트). "강하게"의 본체 레버를 화면에 노출하는 다음 후보.
- **RightStack hop walk**(터미널 공급망) — `computeHop2` 캐시경계 후 게이트. 데이터(leaf facts)는 이제 준비됨.
- **운영자 액션**: 프론트 시각검수 후 push 승인(누적 프론트 + 본 백엔드 커밋들).

---

## 2. 토론 출처

- 1차 워크플로(2026-06-14): 조사 4건(세계 프레임워크 11종 + 세계 제품 + industry 엔진 코드실측 + 양 터미널 코드실측) → 4렌즈 토론(엔진강화·퍼블릭·로컬·덕지덕지 적대) → 후보 병합 → 적대검증 → 수렴 → PRD v0.1.
- 2차 워크플로(2026-06-14): PRD 적대검증 + 엔진 클린코드/리팩토링 감사 + 세계개념 *대대적* 재조사(전략매트릭스·산업경제학·데이터제품/한국) → 흡수설계 → 적대검증 → 개정 spec → PRD v0.2. **산물 = 기능 추가보다 사실오류 정정 + 부정 카탈로그**(강함은 깎아서).
- 코드실측 확정 사실(이 PRD의 근거):
  - `buildIndustrySummary` stage 집계 live, 반환 첫 컬럼 `stage`(docstring `공정`은 오기) ([financials.py:219](../../src/dartlab/industry/build/financials.py#L219))
  - `Industry.edges()` DataFrame amount/ratio 누락 ([__init__.py:359-371](../../src/dartlab/industry/__init__.py#L359)). 디스크 필드 `type`(supplier 3191·affiliate 12980·investor 2240·customer 7), in-memory만 `edgeType`
  - `computeHop2`/`calcSupplyInsights`/`calcHHI`/`calcTopNRatio`/`calcIndustryConcentration` *함수*는 enrichCompany 빌드+테스트만 호출(Industry verb DataFrame·화면 미노출) ([insights.py](../../src/dartlab/industry/build/insights.py)·[hop2.py:32](../../src/dartlab/industry/build/hop2.py#L32)). ★단 산업 분석 *능력*은 `recipes.industry/` 8 curated(industryStagePhase·marginCompressionScan·supplyChainConcentration·peerCapexWave·rdIntensityTrend 등, validated 2026-05-27)로 RunPython 런타임 live — orphan은 함수/화면/컬럼 한정
  - lifecycle은 orphan 아님 — `ai/tools/industryContext.py` getIndustryBadge로 모든 Company.panel/EngineCall 응답에 자동 부착 live. backend 4-phase + 재도약 합성 = surface 5-phase
  - 퍼블릭 `/industry/[id]`는 라이브 엔진 아닌 static JSON 소비 ([+page.ts](../../landing/src/routes/industry/%5Bid%5D/+page.ts))
  - `marketShare`(★2차 정정 — 1차의 "producer 전무 inert dead"는 사실오류): buildIndustryMap.py:816/868이 상장사 상대비중 실생산해 ecosystem.json에 실음 + localTerminalData.ts:348이 로컬 단일사에 `marketShare:100` 날조 → engine.ts에선 이미 제거됐고, 표시는 CenterStack.svelte:194/198·ScreenerModal.svelte:42에 잔존(퍼블릭=실 상대비중 표시·로컬=100 날조). 제거=표시층 한정, EcoNode 필드(types.ts:120)는 landing map/compare 공유라 보존. 사유=라벨 사칭+로컬 날조 시정([07 §구멍5](07-implementation-plan.md))
  - 백분위는 engine.ts:179 pctRank 단일 산식+모집단 파라미터화(industryPercentile:492·percentileIn:501 공유) — "3분기 분기" framing 오류, 이미 통일됨
  - 로컬 RawData는 eco.nodes=1 단일사·edges 필드 부재 → 격자/hop walk는 map/industries/{id}.json lazy 신규 채널(EXTEND 아님). industries edges는 옛 markdown 세대(amount 3/80)라 hop walk는 재빌드 후 게이트
  - Damodaran 자본효율(sales-to-capital·reinvestment·ROC)은 [synth/damodaranL15.py](../../src/dartlab/synth/damodaranL15.py):390-416에 이미 curated 구현
  - 데이터 빈곤: amount 132/18,418(0.7%)·customer 7(전원 ratio=None)·ratio 19(전부 supplier)·opMargin 82.4%·industryStats p10~p90 monotone
  - 유령 *verb/모듈*: `dartlab.industry.sectorMomentumLeadership(...)`·sectorMomentum.py 등 구현 0(README·카탈로그 전파). 단 `recipes.industry.sectorMomentumLeadership.md`는 라이브 recipe(삭제 금지)
- 적대검증 생존: profit-pool grid(conditional·overlap 없음)·edges ratio/amount(conditional·천장 낮음)·hop2(conditional)·percentile band(conditional·표시층 통일로만). kill: migration·BCG stack-fracturing 3차원·ASC275 인용·Capital Cycle·Damodaran 산업분포·Leontief 명명.

---

## 3. 문서 상태

| 문서 | 상태 |
|---|---|
| README.md | ✅ v0.2 |
| 00-product-prd.md | ✅ v0.2 |
| 01-reference-teardown.md | ✅ v0.2 (+§4 부정 카탈로그) |
| 02-differentiation-killer-features.md | ✅ v0.2 (사실오류 정정) |
| 03-architecture-and-reuse.md | ✅ v0.2 (+§5.1 recipe·§8 리팩토링) |
| 04-data-readiness-kill-list.md | ✅ v0.2 (정직 룰 SSOT) |
| 05-scope-phasing-guardrails.md | ✅ v0.2 (정직 룰 SSOT 포인터화) +2차 정정 |
| 06-progress-ledger.md | ✅ v0.2 (본 문서) +2차 정정 |
| 07-implementation-plan.md | ✅ v1 (구현 플랜 — 5구멍 gap-closure·착수 가능) |

---

## 4. NEXT (재개 포인터)

- **착수 = 운영자 go.** 코딩 아님(현재 = 비전 PRD + 구현 플랜 정착). ★구현 단위 file:line·테스트·롤백·AC SSOT = [07-implementation-plan.md](07-implementation-plan.md). 아래는 요약·07이 정본.
- **Phase A(선결 0, 신규 데이터 0)**: ① 구멍2 위생+SSOT 동기화(SKILL.md/docstring 정정 + `syncArtifacts(write=True)` — 옛 `generateSkills` 폐기) → ② `buildIndustrySummary` 파생 컬럼 + `test_financials_sanity::TestProfitPoolDerived` → ③ 구멍1 profit-pool 버블(**신규** industryPool.ts 채널 + 양셸 lazy fetch, **edges 무관**) + 퍼블릭 stage 2D 격자 + profitPoolParity.mts(ts 추출 선결) → ④ 구멍5 marketShare 표시 제거 + Phase C 재프레임 문서.
- **Phase B 선결(구멍3)**: `Industry().build()` **2단계 재빌드**(메모리 가드 하 운영자 실행 → 산출물 검증[source 라벨·amount 카운트·nodes.json diff] → commit, 롤백=git revert 2파일) → 642 vs 132 확정 → 레버 A 졸업 이관(레버 C는 KILL) → Industry.edges() 컬럼/인자 + test_edges.py → **그 후** RightStack hop walk. + `build/insights.py` → `calcs/concentration.py` 승격(import re-point 동행).
- **Phase C(경계 문서화 — 산식 이미 단일)**: 백분위 SSOT 경계 SKILL.md 박제(band 이원화=의도된 설계) + compare 범주오류 정정(compare.py percentile 0건 → 교차참조로만). "3분기 통일"·"post-06-15 재실측"은 ★실측 완료 — 단일 산식 확정([07 §구멍5](07-implementation-plan.md)).
- **운영자 단일 결정 2건**([07 §3](07-implementation-plan.md)): ① `.mts` CI 배선 vs 06 §4 수동줄 ② `Industry().build()` 재빌드 실행 시점(비용 미측정·OOM 위험 인지 후 go).
- **Phase D ledger 후보(본문 승격 금지)**: operating leverage(DOL) 산업 cross-section(panel 다년 회귀, _attempts 졸업·R²/N 동반·marginCompressionScan recipe와 직교 확인 선결). 다축 동시 추가=덕지덕지 → 1축 우선·ledger에만.
- **★흡수 거부 박제(재제안 차단)**: Capital Cycle 순수CAPEX·Damodaran 산업분포(damodaranL15 OWNED)·BCG stack-fracturing 3차원 인코딩·ASC275 customer 인용(supplier 사칭)·Leontief 명명 — [01 §4](01-reference-teardown.md) 부정 카탈로그 참조.
- **검증 게이트**: Python 변경 시 `uv run python -X utf8 tests/run.py preflight` + 단일 파일 `bash tests/test-lock.sh`. svelte 변경 시 svelte-check + build. 푸시 전 ci-fast-local.

---

## 5. 메모리 포인터

- 정본 = `mainPlan/industry-analysis-lab/` (README + 00~06). 메모리는 포인터만(내용 복제 금지).
- 관련 프로젝트: [[project_financial_statement_lab]](백분위 SSOT 경계·reverseDCF·moat 측정값 소유) · [[project_terminal_simulation_prd]](driver DAG·인과·시뮬 소유) · [[project_ui_platform_refactor]](터미널 거처) · [[feedback_always_check_clutter]](덕지덕지 self-check) · [[core_boundary]](L2 단방향).
- 엔진 근본 문서: `engines.industry`(SKILL.md) · `operation.architecture`.
