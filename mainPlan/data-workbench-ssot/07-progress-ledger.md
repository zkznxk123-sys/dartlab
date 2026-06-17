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

## NEXT (재개 시)

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
