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

## 열린 질문

- 가드 구현 (A)Python AST-lite vs (B)TS 스캐너 — 운영자 선호? (06 §2)
- CLAUDE.md 한 줄 추가 여부(06 §3) — "즉시 손상"급 판단.
- P1·P2(추가만, 저위험) 를 운영자 go 즉시 선착수할지, 전체 묶어 갈지.
