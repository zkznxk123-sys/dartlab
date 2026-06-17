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
- [ ] **운영자 go 대기** (착수 전)
- [ ] P1 fetch 코어 + RuntimeCache/RequestDedup 실배선
- [ ] P2 오리진 레지스트리
- [ ] P3 source 이관(순서 05 §1)
- [ ] P4 폴더 구조화 + 가드 + operation/ui.md 박제

## NEXT (착수 시 첫 스텝)

1. 운영자 go 확인.
2. P1: `data/fetch/request.ts` 신설 — `request<T>`·`requestParquetRows`. 내부에 RuntimeCache·RequestDedup·cacheStore·fetchResilient 합성(첫 인스턴스화). vitest 단위(캐시 hit/miss·동시호출 1 fetch·에러 미캐시·TTL).
3. `createPublicRuntime`·`createLocalRuntime` 에 코어 인스턴스 1개 생성(주입 배선만, source 미이관).
4. 타입체크 3패키지 0 + 코어 단위 green → 커밋.
5. P3 첫 이관 후보 = `nonRegularFilingsSource`(이번 세션 신규·dedup 없음, 골든 픽스처 동행).

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
