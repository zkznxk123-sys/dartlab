# 공시검색 OS — 정리 + 자동증분 파이프라인 + 터미널 UI/UX (PRD SSOT)

> 무게중심: **dartlab 핵심 = "공시를 정말로 빠르게 찾는 것"** — 검색은 간판이다.
> 전체 깊은 PRD(21 섹션) 정본: `C:\Users\MSI\.claude\plans\calm-painting-mango.md` (승인 2026-06-18).
> 본 파일 = 요약 + as-built 진행 원장. 근거: engine-cleanup 10-agent 토론(`wf_2784509e-349`) + 파이프라인/배선/UIUX 3-way 실측 + UI/UX 전문가 설계.

## 결론 (깎는 것 / 못 깎는 것)
- **delta 세그먼트 폐기 → compact-only**: 병합 로직 2벌(Python+JS) → 0벌. 신규 공시는 매일 catalog compaction(`rebuildMainFromCatalog`, 평문 ~4분)으로 main 반영.
- **npz 폐기 → STORED sidecar 단일 SSOT**: Python도 `loadShardedSegment`로 CSR 무손실 복원(_scoreBM25 그대로). postings 2벌→1벌, 디스크 −132MB.
- **단일 choke point**: `saveSegmentWithSidecar`(유일 writer) + `indexPublishNames`/`_segmentFiles`(파일명 SSOT). 생성·열거 11곳 → 1 helper.
- **못 깎음(정직)**: meta 2벌(parquet=엔진 전체스캔 / meta.bin=브라우저 top-k, 접근패턴 상이) · STORED 형식 불가피(무서버 range) · `fieldIndexRebuild.py` >800 LoC(별도 분할 과제).
- 정량: 인덱스당 파일 20→8, postings 2→1, 병합 2→0, 열거 11→1, ~580 LoC 삭제(목표), pip 영향 0.

## 4 기둥
1. **엔진**: compact-only + sidecar SSOT + choke point (위).
2. **파이프라인**: catalog always-compact 단일 워크플로(`searchIndexBuild`) — 매일 catalog diff → 변화 시 main 재빌드+clean publish, 무변화 시 manifest re-point. per-source 하한 가드 + legacy raw 제거 + 항상 manifest-pointer.
3. **공통배선**: `createSearchPort(createDataCore())` 퍼블릭/로컬 동일·HF 직독(완료). UI main-only.
4. **UI/UX**: cmdBar(종목점프) 불변 + 신규 `FilingSearchDialog`(커맨드팔레트, `⌘⇧F`+statusBar). 행 클릭=`pick(stockCode)` soft-swap + dart/edgar "원문 ↗". lazy 콜드 stats. 퍼블릭/로컬 동일. 정직 한계: 본문 직행 불가(회사점프+외부링크 floor)·회사인덱스 검색 없음(cmdBar).

## 진행 원장 (as-built)
- ✅ **P0** 엔진 양읽기 — `loadShardedSegment`(벡터 varint-decode) + `loadSegment` 양읽기 + round-trip/BM25 parity 테스트. **실데이터 475,968 docs array-equal + 5쿼리 BM25 byte-parity** 검증. 콜드 npz 1.2s vs sharded 9.2s. commit `ef17da7e0`.
- ✅ **P1-engine** compact-only — searchContent/_getSegments main 단일, rebuildDelta/_clearDelta 삭제, api.rebuildContentDelta=NotImplementedError, saveSegmentWithSidecar + indexPublishNames/_segmentFiles, manifest/push/pull main-only. **45 search 테스트 green**. commit `162db241d`.
- ✅ **P1-UI** main 단일 — filingSearch.ts delta 병합·dedup 제거(−33 LoC), manifest pointer resolve 유지. tsc 0. commit `1f9cb8d7f`.
- ⏳ **P1-pipeline** (운영자 coordinated) — `buildSearchMain.py` per-source 가드+indexPublishNames+no-change 흡수, `buildSearchDelta.py`(374) 삭제, `searchIndexDelta.yml`→`searchIndexMain.yml` body 재사용으로 `searchIndexBuild` 단일화(cron 변경=운영자 게이트), clean publish. **buildSearchDelta 삭제는 searchIndexDelta.yml 재배선과 커플링**(워크플로 깨지 않게 동시).
- ⏳ **P2** npz/saveSegment 삭제 + INDEX_SCHEMA_VERSION bump + 죽은 UI delta 분기 정리 — **P0 PyPI 선배포 후**.
- ⏳ **P3** `FilingSearchDialog.svelte` + TerminalSurface 4지점 배선 — sidecar 배포(P1 run) 후 + 운영자 dev 눈검수/push.

## 배포 순서 (운영자 게이트)
1. P0 → PyPI 선배포(양읽기). 2. P1 코드 push + `searchIndexBuild` 1회(clean publish, HF flip) + cron 변경. 3. P2 정리 push. 4. P3 dev 눈검수 후 push.
**현재 5 커밋 미push**(P0/P1-engine/P1-UI + 무관 2). UI surfaces/runtime·CI 변경이라 운영자 push 승인 필요.

## 정직한 미해소
본문 직행 진입(ViewerStudio rceptNo prop 부재·후속) / 회사인덱스 검색(cmdBar) / snippet 고정 400자 / `fieldIndexRebuild` >800 LoC.
