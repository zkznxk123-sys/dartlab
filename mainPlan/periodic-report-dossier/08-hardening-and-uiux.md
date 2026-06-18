# 08 — 경화 검증 + UI/UX 심화 (적대 재검토 delta)

> 사용자 명령: "PRD의 완벽성을 검증한다 정말로 강한지 더 체크하고 ui ux까지 더많이 고려하라 + 우측 정기보고서 팩트 '불러오는 중' 멈춤 고쳐라."
> 근거: 실제 버그 1건 수정(아래 §1) + 4에이전트 적대 재검토(`wf_c451d741-93f`, 2026-06-19, in-code 검증). **이 문서는 00~07 에 대한 경화 delta** — 평결·정정·신규 가드를 박는다.

---

## 0. 평결 — 조건부 강함: 강한 제품, 약한 기반

PRD는 **제품 프레이밍**(분산+스파인 IA·순 패널 −1·올라가면/내려가면 리프레임)과 **데이터 *값* 정직**(ref-trace·as-of·결측 −/미공시)과 NEVER-CLAIM 규율에서 진짜 강하다. 그러나 **데이터 *경로(path)*·로딩 *상태(state)* 가정**에서는 방금 고친 40초 DuckDB 멈춤과 **동일한 맹점 지문**을 안고 있다 — SHIP 기능마다 데이터경로·로드상태를 *추적/측정 없이 주장*("structured-ready"·"reportSource read"·"백엔드 0"·"체이닝 1.4x"·"공개+로컬 동일"). 3개 독립 렌즈가 **같은 구조 결함**으로 수렴했다.

> **"정말 강한가?"의 정직한 답**: 비전은 강하다. 데이터배선 사고는 약하다. 방금 고친 perf 버그는 단발이 아니라 *PRD가 추적 안 한 데이터경로를 주장한* 체계적 검증 갭의 신호다. Phase-0 사전점검으로 *고칠 수 있으나*, **현 상태로는 "정말 강함" 아님.**

---

## 1. 실제 버그 수정 (as-built) — 정기보고서 팩트 멈춤

- **증상**: 우측 "DART 정기보고서 팩트" 패널이 "불러오는 중"만 뜨고 수십 초 멈춤.
- **근본원인**: `loadLiveCompanyReportFacts`(`companyLive.ts`)만 **DuckDB-WASM** 경로 잔류 — 단일워커 직렬큐에 6개 전시장 parquet 뷰 등록+SQL 스캔, 종목전환마다 재등록, 캐시·타임아웃 0. 형제 패널(인력·주주환원)은 이미 hyparquet(`reportSource.ts`)로 이관됨. `reportSource.ts:1-6` 주석이 명시: *"DuckDB-WASM 경유 금지 — 첫 표시 수십 초(실측 40s)"*.
- **수정**(commit `e801f42f0`): reportFacts를 동일 hyparquet 경로(`createDataCore().requestParquetRows` + stockCode 필터 + 60분 캐시)로 이관. 변환함수·주입 배선 불변, 시각 변화 없음. `factYear`는 4자리 달력연도만 인식(`auditOpinion`의 '제58기 1분기' 기수 라벨 오정렬 차단).
- **실측 검증**: node로 6개 parquet 직접 read → **콜드 병렬 4.3초**(삼성 612배당·415임원행 정확), 재방문 캐시 즉시. svelte-check **0 error**. (수십초·멈춤 → 4.3초)
- **잔여(F1 편입)**: reportFacts가 runtime dataCore가 아닌 **private `_reportFactsCore`** 사용 → dividend/treasury를 shareholderReturn과 캐시 미공유(콜드 중복 read). **회귀는 아님**(옛 DuckDB도 독립 read였음). F1 chainTriplet 구현 시 runtime core 주입으로 해소 → §3 F1 갱신.

---

## 2. 검증된 실제 갭 (in-code, SHIP 전 정정 필수)

| # | 갭 | 증거 | 정정 | 반영 |
|---|---|---|---|---|
| G1 | **F2 비용 성격별이 SHIP-ready 오기재** — '백엔드 0·신규 reportSource read·1 note read'인데 실제로 note-cell(`fetchNotesDetail` Python L2 panel) 읽음. reportSource는 `dart/scan/report/*.parquet`만 읽고 note-cell 접근 0. **F3 희석을 연기한 바로 그 벽.** | `_costStructureDeep.py:92-98` fetchNotesDetail · reportSource `read()` parquet only · `dart/scan/report/costByNature.parquet` 부재 · 07 line 80(F3 연기근거)이 16/57/61/98/126(F2 SHIP)과 모순 | **F2 → NEEDS-PARSING/CI-bake 재분류**(rndIntensity F4와 동급). CI consolidation이 `report/costByNature.parquet`(per-company {category,year,amount,ratio,direction,insight}) bake → reportSource가 *그 parquet* read(엔진 아님). bake 전 공개 불가. F2+F4 = 단일 bake 의존. | 04·07 인라인 |
| G2 | **F5 인적자본 bake가 없는 파일 지목** — `src/dartlab/scan/workforce/snapshot.py` 부재(디렉토리=`__init__`/`growth`/`scanner`만). | 실제 bake = `src/dartlab/scan/builders/kr/snapshot.py:159-161`. ("scanRevenuePerEmployee만 baked" claim 자체는 *맞음* — 경로만 틀림) | 모든 snapshot 참조를 `scan/builders/kr/snapshot.py:159-161`로 정정. | 01·05 인라인 |
| G3 | **NEVER-CLAIM grep 가드가 '확장'할 대상 부재** — `valuationPublishLint.py`는 simulation 마크다운만 스캔, "src .py 는 영원히 스캔 안 함", UI surface 불가. | 04 §3/03 §7/05 Phase1이 "G3-style grep 가드 확장"이라 *append*로 예산. 실제로 우량/주주친화/좋은고용주를 Svelte/cardGuide.ts에서 잡는 lint 0. | **net-new lint 명세**: 대상=`ui/packages/surfaces` 터미널 `*.svelte`+`cardGuide.ts` 문자열, 토큰목록, 엔진토큰 allowlist, `tests/run.py` 배선. *확장 아닌 신규 게이트*. | 05 §NEVER-CLAIM lint |
| G4 | **lossPct 표면화가 '0-fetch 표면화만' 아님** — `lossPct`/`lossBook`이 `HoldingsDialog.svelte:120-121` 로컬 `$derived`, 재사용 `buildHoldingsModel`(holdings.ts) 미포함. | holdings.ts에 lossPct 없음(grep). 02 §3 '전부 계산, 표면화만(0-fetch 진짜)' 과장. | F3 임팩트에 **추출 작업 추가**: lossBook/lossPct를 holdings.ts(또는 controlShiftSummary 형제 순수함수)로 lift → 헤더+다이얼로그 단일 SSOT. | 05 §4/§5 |
| G5 | **공개+로컬 동일 렌더 게이트가 코드와 모순** — local `companySource.ts:33` `reportFacts()=>[]`. createReportSource는 public에서만 생성. | 05:9,21,41 '공개+로컬 동일'·'로컬전용 금지'. 단 그 stale 주석('duckdb 셸 주입')은 *이관 후 거짓* → 로컬 배선 가능해짐. | **택1**: (a) `createReportSource(localCore)`+실 reportFacts를 로컬 company port 배선(hyparquet라 duckdb/셸 의존 없음→가능), or (b) dossier를 공개전용으로 명시·패리티 게이트 삭제. 주장한 패리티를 *배선*. | 05 §common-wiring |
| G6 | **순 패널 −1이 4개 팩트형 *드롭* 위험** — 평면 'DART 정기보고서 팩트' 패널은 dividend/treasury(주주환원에 재이주 가능) + **executive/auditOpinion/majorHolder/corporateBond(형제 패널 없음)** 포함. | `companyLive.ts:311-316` 6개 fact, 4개 무-형제. 03 §7이 '정합성 증명'으로 단정. | **net-panel-down 정직 감사**: 6개 fact형 전부 열거 → 각 재이주 증명 후 삭제. 4개 무-형제는 리본 or 새 슬롯에 재배치 명시. | 03·05 |

추가 미검증 주장(측정으로 대체): 체이닝 1.4x(dividend frmtrm/lwfr non-null율 미측정)·cost-by-nature 6%(엔진 docstring, 라이브 미측정)·R&D 59.7%/세그먼트 4.6%(census **shard0 단일**, 대표성 미확인). → §4 Phase-0 probe.

---

## 3. UI/UX 심화 — 상태 기계 (사용자 핵심 요구)

PRD는 *정상상태(steady-state)* 픽셀을 정교히 설계했으나 **시간/상태 차원**이 거의 비었다 — 정확히 사용자가 데인 곳(타임아웃 없는 40초 멈춤). **정직 교리가 데이터 *값*엔 적용됐는데 *로드/에러 상태*엔 안 됨.** 03 에 **§8 상태 기계** 신설:

### 3.1 4-상태 계약 (loading·ready·empty·error) — 전 dossier surface 균일
- 현재 `factsState`='loading'|'ready'|'empty' 만(`RightStack.svelte:162`), **'error' 없음**. `.then()`에 `.catch`·타임아웃 0(L210-214). **실패/지연이 honest absence('없음')와 같은 화면** → PRD 자체 정직 교리 위반(empty='봤는데 없다', error='못 봤다' — 혼동 금지, "확신오정렬 > 정렬실패").
- **수정**: ① 'error' 상태 추가. ② `Promise.race([fetch, 8s timeout])`. ③ 별도 정직-실패 블록 '불러오지 못했습니다 · ↻ 다시 시도'. 형제 패널(인력·주주환원·출자)에도 동일 4-상태.

### 3.2 조립 안무 (reading-story 보존)
- 3개 간판 패널이 `{#if wfLast}`/`{#if srLast}`/`{#if inv}` bare 게이트(`RightStack.svelte:540/554/568)·**로딩 분기 없음** → 3개 독립 promise가 *해소 순서대로* pop-in → 설계된 top-down 서사(누구→인력→주주환원→자본흐름)가 **무작위 순서·layout shift**로 조립.
- **수정**: 패널별 `wfState`/`srState`/`invState` + **고정높이 스켈레톤**(기존 `.chartLoad::before dlSkel` shimmer 재사용, 스피너 아님) 실 행수로 → 1프레임부터 서사 스택 안정. 로더 un-bundling(`reportSource.ts:35-37`, 16MB investedCompany를 가벼운 패널과 분리)은 perf상 *맞으나*, reserved-height 스켈레톤이 서사 슬롯을 잡아야 순서 유지.

### 3.3 점진 콜드-페인트 (첫인상)
- 60분 캐시로 재방문 즉시지만 **콜드 첫 페인트는 6 parquet fan-out ~4.3초**가 단일 blank '불러오는 중' 뒤. F1 스파인 리본이 6 read fan-out이라 가장 느린 타일.
- **수정**: 6개 fact 행을 *각자의 parquet 해소 즉시* 렌더(Promise.all 게이트 제거, 행별 shimmer). 헤더 'N/6 공시'를 **0/6→6/6 라이브 카운터** — 한 메커니즘이 체감성능 + (PRD가 원하던) 커버리지 라벨 둘 다 충족. 좌측레일 종목 hover 시 스파인 read 워밍(LeftRail 이미 디바운스).

### 3.4 마커 지각성 (정직 신호)
- 정정 빗금·proxy hollow·근사정합 마커가 *유일 신규 픽셀*이고 F1 정직 주장 전체가 여기 의존하나, **지각 한계 미달 가능**. MiniFinChart 막대 `width=Math.max(0.8, barW-0.6)`(한자리 px) + **이미 hover-dim에 fill-opacity 0.4-0.9 사용** → 'proxy=50% opacity'는 hover된 clean 막대와 구별 불가, 6px 막대의 `url(#hatch)`는 solid로 보임. 상시 범례 없음(`note` 1절=접힘).
- **수정**: ① proxy에 opacity 금지(hover와 충돌) → **글리프 마커**(clean=solid, restated=solid+막대 위 ▾ caret, proxy=outline+점선top+○). ② 차트 제목 아래 **상시 8px 인라인 범례** '■공시값 ▾정정반영 ○전기재현'(접힘 note 아님). ③ 데모 게이트에 *실 정정 케이스 실밀도 스크린샷 눈검수*(feedback_ui_rules — 정량 PASS가 6px 빗금 안 보임을 못 잡음).

### 3.5 접근성 (체계 부채)
- `RightStack.svelte` aria-live/role=status **0**(SR 사용자에 로드/실패 미고지). 정정 마커는 *fill 패턴만*(텍스트 대안 없음). `prefers-reduced-motion`은 surfaces 3파일·**터미널 0**인데 dlSkel/filingFlash/dlTermPulse 무조건 실행. (코드베이스는 올바른 키보드 패턴을 *앎* — `RightStack:611` role=button tabindex=0 onkeydown Enter — 리본 ↗·상세보기에 미적용.)
- **수정**: ① 모든 loading/empty/error body = `role=status aria-live=polite aria-busy`. ② 정정/proxy `<rect>`에 `aria-label`(prov 1줄) + 상시 텍스트 범례. ③ `terminal.css`에 `@media(prefers-reduced-motion:reduce)` 1블록(dlSkel/filingFlash/dlTermPulse → static). ~15줄 net-new, 저렴·정직 주장에 load-bearing.

### 3.6 메타 긴장 (정직한 해소)
'순 패널 −1 / subtract not add'는 *zero 새 UI*를 자랑하나, **로드 하에서 정직한 dossier는 패널별 상태 기계가 *필요*하다**. 정직한 해소: loading/error/skeleton은 안티클러터 위반이 아닌 *필요 추가* — 현재의 *침묵 pop-in*(그 자체가 혼란-클러터)을 *대체*하기 때문.

---

## 4. 신규 가드 (04/05 에 박음)

### 4.1 Phase-0 사전점검 데이터 커버리지 probe (SHIP-게이팅)
모든 feature phase 전, 1회성 Python/Polars(`uv run python -X utf8`, src 미커밋, stdout — 워크스페이스 위생)로 전(全) ~2,800 filer 측정:
- (a) dividend frmtrm/lwfr **non-null율 per se-line** → 주장된 '체이닝 1.4x' 확정.
- (b) costByNature note 가용률 → '~6%/173사' 확정(현재 엔진 docstring).
- (c) shPeriods named[] 기간수 분포 → 'control-shift 0-fetch' 확정.
> **스키마 존재 ≠ populated**: frmtrm/lwfr은 `saver.py` 컬럼이나 reportSource는 thstrm만 read → 커버리지 미검증. F1/F2/F3 SHIP 숫자를 *측정값으로 대체*.

### 4.2 DuckDB 금지 가드 (per-company)
> **dossier 경로에 per-company DuckDB point-lookup 금지.** 모든 per-company read는 hyparquet(`createDataCore().requestParquetRows` / `loadHfCompanyChanges`). **금지**: `loadLiveCompanyPanelExcerpts`(DuckDB), `loadLiveCompanyChanges`(DuckDB). SSOT 패턴 = `reportSource.ts:1-6` 주석.
- **휴면 지뢰**(스파인 서사가 부활시킬 위험): `loadLiveCompanyChanges`(`companyLive.ts:758`, changes.parquet DuckDB 뷰) — 빠른 `loadHfCompanyChanges`(`changesRuntime.ts:91-128`, stockCode 필터)가 *이미 있으나 company port 미사용*. F1 스파인이 per-company 변경 노출 전 rewire. `loadLiveCompanyPanelExcerpts`(DuckDB REGEXP+LIKE, 캐시·타임아웃 0, 현재 import 0) — F7 원문발췌는 *뷰어 렌더 텍스트* 사용(이미 명시), 이 함수 금지/삭제.

### 4.3 콜드-페인트 예산 + fetch 우선순위
종목전환당 **~25+ parquet read**(reportFacts 6 + shareholderReturn 2 + ownership 2 + investments 1[16MB] + execBoard 2 + debtProfile 3 + capitalChanges 1 + workforce 1 + shPeriods 1 + filings 2 + news + relations). first-meaningful-paint 목표 + **tier 분리**: tier-1(전환 시 즉발=리본·workforce·shareholderReturn) / tier-2(상세보기·FinFullscreen 시=investedCompany 16MB·debtProfile 3-parquet). **측정 4.3초는 reportFacts-6 단독이지 전환 예산 아님** — 혼동 금지.

### 4.4 타임아웃+재시도 게이트 (Phase-0 스파인)
reportFacts/workforce/shareholderReturn read는 ~8s 타임아웃 race → 타임아웃/reject 시 error+재시도, *영구 '불러오는 중' 금지*. 수용기준에 DevTools 3G throttle 테스트(무한 로더 0) — 방금 고친 버그의 *클래스*를 게이트에 박음.

---

## 5. perf 교훈 (SSOT 가드)

> **"추적하라, 주장하지 말라 — read 경로 *와* 로드 상태 둘 다."** Phase-0 진입 게이트.

1. **per-company DuckDB 금지**(§4.2). DuckDB-WASM = 단일워커 직렬큐(cold-init+register+scan, 전환마다, 캐시·타임아웃 0) = per-company read의 *구조적 hang 생성기*(40s↔hyparquet 4.3s 콜드/즉시 웜). 살아있는/휴면 DuckDB 3곳(statements `companyLive.ts:326`·changes:758·panelExcerpts) 어느 것도 F1/F7이 부활 가능.
2. **상태 기계 가드**(§3.1/4.4): 모든 per-company read는 ① 8s 타임아웃 ② empty와 구별되는 'error' ③ 영구 '불러오는 중' 금지.
3. **측정 가드**: 스키마 존재 ≠ populated. 'structured-ready/N reportSource read/백엔드 0' 주장은 실제 `dart/scan/report/*.parquet` read 경로로 추적되거나 NEEDS-PARSING/CI-bake로 재분류.

reportFacts hang은 단발이 아니라 *PRD가 추적 안 한 데이터경로를 주장한* 결과 — 그 클래스를 Phase-0 게이트로 차단.
