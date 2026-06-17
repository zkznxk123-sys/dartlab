# 07. 진행 원장 (세션 간 재개)

상태: 원장 v0.1. 다른 세션이 surface 작업 중 → 본 작업은 런타임/data 계층만 건드려 충돌 최소. 재개 시 이 파일 NEXT 부터.

---

## 결정 로그

- 2026-06-17: PRD v0.1 작성(전문에이전트 3 렌즈 조사 + grep/read 검증). 핵심 = "죽은 작업대(RuntimeCache·RequestDedup) 실배선 + 오리진 레지스트리 + 로컬 provider 게이트 + 폴더 구조화 + 운영문서/가드 박제". 착수는 운영자 go 대기.
- 확정 사실: origin.ts=HF URL SSOT(Phase0) 살아있음 / RuntimeCache·RequestDedup=인스턴스화 0건(grep) / 산재 캐시 20+(reportSource 11) / 오리진 7+종 / 로컬 /api 4 source 분산 / TS 가드 0 / operation/ui.md 데이터층 섹션 0.
- 계약(17 포트) 불변·점진 이관·무중단 원칙 합의. 전면 재작성 KILL.

## 현재 상태

- [x] 조사·감사(01) 완료
- [x] 설계(02·03) 완료
- [x] 경계·페이즈·가드 설계(04·05·06) 완료
- [x] 운영자 go (2026-06-17, /goal)
- [x] **P1 fetch 코어 + RuntimeCache/RequestDedup 실배선** — `data/fetch/request.ts`(createDataCore: request·requestParquetRows) + `data/origins/registry.ts`(hf·hfRange 흡수) 신설. 어댑터당 1 코어(createPublicRuntime·createLocalRuntime 생성·filing 주입). 죽어있던 RuntimeCache·RequestDedup 첫 인스턴스화. 커밋 0b0d80c11.
- [~] **P3 source 이관 진행** — nonRegularFilingsSource 두 함수(loadRecentFilingsForCodes·loadCompanyNonRegularFilings) 완전 이관(자체 Map 2개 폐기 → 코어 캐시·dedup·10분 TTL). 커밋 77bd78160.
- [ ] P3 잔여 source 이관 — **다음 = reportSource(11 함수·11 Map → 코어, 최대 정리; publicReportPort(core) 양 어댑터)**, 이후 finance·macro·gov·price·productIndex·relations·industryPool·news·naver(news/naver 는 P2 워커 오리진 선행).
- [ ] **vitest 하니스** — runtime 패키지에 테스트 러너 없음(check=tsc만). 코어 단위테스트(캐시 hit/miss·동시 dedup 1fetch·에러 미캐시·TTL)는 vitest devDep+config+lock 필요 → **동시 세션 lockfile 편집 중이라 보류**. 잠잠해지면 install+테스트(또는 운영자 승인 후). 현재 검증=tsc+svelte-check 0 errors + 이관 함수 로직 불변.
- [ ] P2 오리진 레지스트리 확장(news·naver 워커·localApi·duckdbHf·landingJson)
- [ ] P4 폴더 구조화(`cache/`→`data/cache/` 등) + 가드(`tests/audit/checkUiDataWiring` TS AST) + operation/ui.md 박제 + 강행규칙 한 줄

## 구현 진척 (2026-06-17, 에이전트 돌파 wave)

- [x] **P1 코어 + 죽은 작업대 실배선** (0b0d80c11) — createDataCore(request·requestParquetRows), RuntimeCache·RequestDedup 첫 인스턴스화, 어댑터당 1 코어.
- [x] **vitest 하니스 + 코어 5 단위테스트** (323aba7df) — 캐시 hit·dedup·에러미캐시·TTL·scope none. 5/5 통과.
- [x] **P3 이관 4 소스 (~16 캐시 구현 소멸)**: nonRegularFilingsSource 2함수(77bd78160) · reportSource 11 Map factory(6806c1d94) · financeSource rowsCache·bundleCache(a0f7181fa).
- [x] **P4 가드** (4a76c021c) — tests/audit/checkUiDataWiring.mjs (TS AST) + uiDataWiring.baseline.json(9건 미이관 부채). 신규 위반 fail·이관 시 ratchet.
- [x] **P4 운영문서 박제** (4b1c9c439) — operation/ui.md 데이터층 SSOT 섹션 + web.json 동기화(artifactSync).
- [x] **P4 강행규칙** (로컬) — CLAUDE.md(gitignore L-local) UI 데이터 호출 단일 작업대 규칙 1줄.

작업대(코어+테스트+가드+문서+규칙)는 *완성·강제됨*. 남은 건 미이관 소스의 *채택*(가드가 신규 위반 차단·debt ratchet down).

## 추가 이관 (2026-06-17 후속 wave)
- [x] **macro·gov(price·index)·productIndex·index·fred 이관** (01d3a91bd) — 코어에 `requestParquetWholeFile` 추가. 캐시 Map 다수 폐기. baseline **9→7**. legacy 무인자(ui/web·localCompanyPort)=module-local fallback(가드 allowlist 5건: finance·macro·gov·idx·product).
- 잔여 baseline **7** = 전부 *다른 오리진*이라 P2 선행 필요: 로컬 SSE(aiSource)·export(/api ×3)·naver 워커·news 워커·gov dev `/__gov`.

## ✅ 작업대 완성 (2026-06-17)

- [x] **P2 워커 오리진 + news·naver 이관** (7b0c2aa16) — newsWorker·naverWorker 레지스트리 등록(env 게이트 흡수)+originConfigured. baseline 7→5.
- [x] **로컬 provider 게이트** (c063cde58) — `adapters/local/api/{localApi,stream}` 단일 :8400 진입점(getJson·postJson·fetchRaw·SSE). aiSource·export·filing·price 게이트 이관, 로컬 sources raw fetch **0**. baseline 5→1. (운영자 명시 deliverable 완료.)

**작업대 = 완성·테스트·강제·문서·규칙·전소스 채택.** 코어(request·requestParquetRows·requestParquetWholeFile, vitest 5/5) + 오리진 레지스트리(hf·hfRange·newsWorker·naverWorker) + 11소스 이관 + 로컬 게이트 + 가드(baseline 1) + operation.ui + 강행규칙(로컬). 캐시 구현 ~20+ → 코어 단일 SSOT 수렴. RuntimeCache·RequestDedup 죽은코드 → 실배선.

## 잔여 (선택 polish — 작업대 본체 무관)

- **relations·industryPool**: loadJson(dartlabData/cacheStore) 기반 — raw fetch 아니라 가드 미플래그(위반 0). 코어 이관하려면 `landingJson` 오리진 등록 + 코어 `request` 의 `persist` scope(cacheStore 연동) 구현 선행. 저우선(이미 cacheStore 영속+local-fallback 보유).
- **gov dev `/__gov`** (baseline 1): Vite dev 미들웨어 live-fill, dev 전용·prod 무관. acceptable debt.
- **P4 폴더 구조화**(03): `cache/`→`data/cache/`·`hfRange`→`data/parquet/`·`origin.ts`→`data/origins/hf.ts`(re-export 다리). 순수 재배치(import churn) — 동시 세션 잠잠할 때. 저우선.
- **module-local-core fallback 7건**(finance·macro·gov·idx·product·news·naver): legacy 무인자 호출(ui/web localTerminalData·localCompanyPort) 대응. 가드 allowlist. 정답=ui/web/localCompanyPort 에 core 주입(ui-platform-refactor 편승).

## 이전 NEXT (해소됨)
- **P2 오리진 레지스트리 확장**: `newsWorker`·`naverWorker`(env-gate·dev `/__news`·`/__naver` 분기 → 레지스트리로) → newsSource·naverPriceSource 를 `core.request`(JSON) 로 이관. `landingJson` 오리진 → relationsSource·industryPoolSource(loadJson) 이관.
- **로컬 provider 게이트** `adapters/local/api/`: aiSource(SSE)·exportSource(/api ×3)·gov dev `/__gov` 를 단일 게이트로. localApi 오리진(어댑터 apiBase 주입형 — 정적 레지스트리와 다른 처리 필요). SSE 는 캐시 부적합 → 게이트가 stream 경로 분리.
- 각 이관 후 가드 `--write-baseline` 로 ratchet, 0 수렴 목표.
- **P4 폴더 구조화**(03): `cache/`→`data/cache/`·`hfRange`→`data/parquet/`·`origin.ts`→`data/origins/hf.ts`(re-export 다리). 마지막.

1. **reportSource 이관** — 11 load 함수의 `cached()`+11 Map 을 코어 requestParquetRows 로 교체(각 함수 `core` 인자). `publicReportPort(core)` 로 변경 + createPublicRuntime·createLocalRuntime 양쪽 `report: publicReportPort(dataCore)` 전달. 각 함수 `cacheKey=report.{metric}:{code}`. tsc+svelte-check green → 커밋.
2. financeSource(rowsCache·bundleCache)·macroSource(srcCache)·productIndexSource·gov*·price 순 이관(05 §1).
3. **vitest 하니스** — lockfile 잠잠할 때 `npm i -D vitest -w @dartlab/ui-runtime` + `vitest.config` + `request.test.ts`(fetch·now 주입 결정론) + `test` script. CI 등록.
4. P2 오리진 레지스트리 확장(news·naver 워커·localApi·duckdbHf·landingJson) → news/naver/relations/industryPool 이관.
5. P4 폴더 이동(re-export 다리) + 가드(`tests/audit/checkUiDataWiring` TS AST·baseline) + operation/ui.md 박제 + 강행규칙 한 줄(가드 green 후).

## 검증 메모

- 현재 가용 검증 = `npm run check -w @dartlab/ui-runtime`(tsc) + `npm run check -w @dartlab/ui-surfaces`(svelte-check). 둘 다 0 errors 유지가 이관 게이트.
- 이관은 변환 로직 불변 + 캐시/dedup 만 코어 위임이 원칙 — 반환 객체 동일(회귀면 = svelte-check + 추후 vitest 골든).

## 충돌 회피 메모

- 본 작업 = `ui/packages/runtime/src/{data,cache,adapters}` + `tests/audit` + `operation/ui.md`. surface(`ui/packages/surfaces`)·landing 미수정 → 다른 세션과 경로 분리.
- source 이관은 1개 커밋 1 source(되돌리기 쉽게). 폴더 이동(P4)은 re-export 다리 두고 마지막에.

## 해소된 결정 (2026-06-17, 운영자 위임 → 정공법 확정)

- **가드 구현 = TS AST(typescript 컴파일러 API) 가드** `tests/audit/checkUiDataWiring`. 정규식/Python-lite 기각(TS 미파싱 → false pos/neg). 신규 의존 0(toolchain 의 `typescript` 재사용). baseline 부채원장. (06 §2)
- **CLAUDE.md 강행규칙 = 추가 확정.** 아키텍처 무결성 가드 계열(4계층 import·prebuild 경계와 동급), dev=퍼블릭 위반이 실제 회귀를 냄. 한 줄 + operation 위임, 가드 green 후(P4 동행). (06 §3)
- **operation/ui.md 데이터층 섹션 = 추가 확정.** (06 §1)
- **SvelteKit Remote Functions = KILL.** adapter-static(서버 0) 실측 — 작동 불가 + 서버0 floor 위반 + SSOT 역행. (04)
- **#3 페이즈 = 전체 끝까지(정공법), 순서대로.** P1 만 cherry-pick 하지 않는다. go 즉시 P1·P2(추가만·저위험) 선착수 → P3 source 1개씩(골든픽스처) → P4 폴더+가드+문서까지 완주. 각 페이즈 독립 출시·롤백.

## 열린 질문

- (없음 — 착수 전 결정 전부 해소. 운영자 go 만 대기.)
