# 공시검색 OS — 정리 + 자동증분 파이프라인 + 터미널 UI/UX (PRD SSOT) ✅ 완료·_done 이관

> 무게중심: **dartlab 핵심 = "공시를 정말로 빠르게 찾는 것"** — 검색은 간판이다.
> 전체 깊은 PRD(21 섹션) 정본: `C:\Users\MSI\.claude\plans\calm-painting-mango.md` (승인 2026-06-18).
> 본 파일 = 요약 + as-built 진행 원장. 근거: engine-cleanup 10-agent 토론(`wf_2784509e-349`) + 파이프라인/배선/UIUX 3-way 실측 + UI/UX 전문가 설계.

## ✅ 종결 상태 (as-built 정정 — 2026-06-23 git/HF 실측)
- **코드 P0~P3 7커밋 전부 origin/master 배포 완료** — `ef17da7e0·162db241d·1f9cb8d7f·b55003fe6·53e13f60a·d0609517f·578ff6dab` 모두 `merge-base --is-ancestor` PASS. 아래 본문의 "미push 3"은 **STALE**(과거 세션 기록이며 이후 push됨).
- **검색 기능 라이브 정상** — `FilingSearchDialog`/`filingSearch.ts`는 순수 프론트(PyPI 의존 0), HF contentIndex 직독으로 작동. 라이브 인덱스 builtAt 2026-06-20·allFilings 196k행·sourceDataAsOf 신선.
- **searchIndexBuild 파이프라인 GREEN** — 2026-06-19~20 self-canary flaky 회귀를 4커밋(`34287b83c·318014849·b2b11b492·e0f1ab493`)으로 결정론화 수정. 일간/월간 cron 정상 실행 중.
- **유일 잔여 = sidecar/compact 마이그레이션의 PyPI 릴리즈** (운영자·되돌릴 수 없는 발행). 현재 PyPI 0.10.7 = search-os 이전(npz 리더), HF 데이터 = 여전히 npz(main.npz 143MB, sidecar 미flip). 이는 **디스크 −132MB·파일수 절감의 내부 최적화**이고 사용자 기능을 막지 않음 → 운영자 릴리즈 트랙으로 분리. 순서는 아래 "배포 순서" 참조.

## 결론 (깎는 것 / 못 깎는 것)
- **delta 세그먼트 폐기 → compact-only**: 병합 로직 2벌(Python+JS) → 0벌. 신규 공시는 매일 catalog compaction(`rebuildMainFromCatalog`, 평문 ~4분)으로 main 반영.
- **npz 폐기 → STORED sidecar 단일 SSOT**: Python도 `loadShardedSegment`로 CSR 무손실 복원(_scoreBM25 그대로). postings 2벌→1벌, 디스크 −132MB.
- **단일 choke point**: `saveSegmentWithSidecar`(유일 writer) + `indexPublishNames`/`_segmentFiles`(파일명 SSOT). 생성·열거 11곳 → 1 helper.
- **못 깎음(한계)**: meta 2벌(parquet=엔진 전체스캔 / meta.bin=브라우저 top-k, 접근패턴 상이) · STORED 형식 불가피(무서버 range) · `fieldIndexRebuild.py` >800 LoC(별도 분할 과제).
- 정량: 인덱스당 파일 20→8, postings 2→1, 병합 2→0, 열거 11→1, ~580 LoC 삭제(목표), pip 영향 0.

## 4 기둥
1. **엔진**: compact-only + sidecar SSOT + choke point (위).
2. **파이프라인**: catalog always-compact 단일 워크플로(`searchIndexBuild`) — 매일 catalog diff → 변화 시 main 재빌드+clean publish, 무변화 시 manifest re-point. per-source 하한 가드 + legacy raw 제거 + 항상 manifest-pointer.
3. **공통배선**: `createSearchPort(createDataCore())` 퍼블릭/로컬 동일·HF 직독(완료). UI main-only.
4. **UI/UX**: cmdBar(종목점프) 불변 + 신규 `FilingSearchDialog`(커맨드팔레트, `⌘⇧F`+statusBar). 행 클릭=`pick(stockCode)` soft-swap + dart/edgar "원문 ↗". lazy 콜드 stats. 퍼블릭/로컬 동일. 기능 한계: 본문 직행 불가(회사점프+외부링크 floor)·회사인덱스 검색 없음(cmdBar).

## 진행 원장 (as-built)
- ✅ **P0** 엔진 양읽기 — `loadShardedSegment`(벡터 varint-decode) + `loadSegment` 양읽기 + round-trip/BM25 parity 테스트. **실데이터 475,968 docs array-equal + 5쿼리 BM25 byte-parity** 검증. 콜드 npz 1.2s vs sharded 9.2s. commit `ef17da7e0`.
- ✅ **P1-engine** compact-only — searchContent/_getSegments main 단일, rebuildDelta/_clearDelta 삭제, api.rebuildContentDelta=NotImplementedError, saveSegmentWithSidecar + indexPublishNames/_segmentFiles, manifest/push/pull main-only. **45 search 테스트 green**. commit `162db241d`.
- ✅ **P1-UI** main 단일 — filingSearch.ts delta 병합·dedup 제거(−33 LoC), manifest pointer resolve 유지. tsc 0. commit `1f9cb8d7f`.
- ✅ **P1-pipeline** — `buildSearchMain.py`에 no-change 단락(previous==current+이전 manifest clean→pointer만 re-point, delta 잔존시 clean 풀압축 강제)+per-source 하한 가드(allFilings130k/panel70k/edgar40k/news70k, env 대체)+`indexPublishNames` clean publish(previousManifestPath seed 안함→fileSources delta키0). `buildSearchDelta.py`(374) 삭제. `searchIndexMain.yml`+`searchIndexDelta.yml`→**단일 `searchIndexBuild.yml`**(일간 cron+월간 cron force_full+4 source workflow_run+build_mode catalog/legacy[operator-only recovery]·gate 일간·workflow_run=ops/월간·수동=release). `checkSearchRemoteEvidence` delta키0 assert. 로컬 활성/해상(resolveActiveIndexDir/selfcheck/_activeIndexDir/ensureContentIndex)을 main.npz→**main.postings.bin(sidecar SSOT)|legacy npz** 판정으로 전환(sidecar-only 오판 회귀 수정). `_encodeVarintArray` 빈 스트림 가드. monitor·planSearchBootstrap·drill/roundtrip·테스트 정합. **424 search/pipeline 테스트 green**. commit `b55003fe6`. ⏳cron 변경+searchIndexBuild 1회 실행(HF flip)=운영자.
- ✅ **P2** npz 완전 폐기 — `saveSegment`(npz writer) 삭제→`writeSegmentCompanions`(stems/info/parquet, npz 없음)·`saveSegmentWithSidecar`=companions+sidecar(=postings SSOT) 단일 writer·`loadSegment` sidecar 전용(npz fallback 제거)·`_CORE_POSTINGS_ANY`/`_hasMainPostings`=postings.bin 단독. **INDEX_SCHEMA_VERSION 유지(=3, bump 안 함)** — npz→sidecar 는 직렬화 변경일 뿐 CSR/토크나이저/BM25 동일(byte-parity), bump 시 flip 직후 v3 sidecar 를 v4 라이브러리가 거부(compatibleMax 위반)하는 자해라 의도적 비-bump(플랜 §10 deviation). 테스트 12개 npz→sidecar 정합. **195 search + 260 engine 테스트 green · sidecar-only 검색 end-to-end 실측**. commit `53e13f60a`. ⚠**flip 전 미배포** — P0 PyPI(dual-read)+P1 HF flip 후에만 PyPI 발행(미push, P0 발행은 본 커밋 이전 commit/tag 에서 빌드).
- ✅ **P3** `FilingSearchDialog.svelte`(커맨드 팔레트 ⌘⇧F+statusBar) + TerminalSurface 4지점(import·state·onDocKey ⌘⇧F·statusBar 버튼·마운트). useDartLabRuntime().search 경유·140ms 디바운스+stale 토큰·lazy 콜드·행 클릭 soft-swap+원문↗(DART rcpNo/EDGAR 회사브라우즈)·최근검색·기능 한계 라벨. 전 스타일 컴포넌트 scoped(terminal.css 무변경). **svelte-check 0 err·runtime tsc·checkUiDataWiring PASS**. commit `d0609517f`. ⏳운영자 dev 눈검수+push.

## 배포 순서 (운영자 게이트 — 코드는 전부 구현·검증 완료, 남은 건 배포 액션뿐)
1. P0 → PyPI 선배포(dual-read). **본 커밋 이전 commit/tag(예 `1f9cb8d7f`)에서 빌드** — P2(`53e13f60a`)가 HEAD 라 HEAD 빌드 금지. 2. P1 push(`b55003fe6`) + `searchIndexBuild` 1회(clean publish→HF sidecar-only flip) + cron 변경. 3. P2 push(`53e13f60a`) + PyPI 발행(dual-read 전파+flip 후). 4. P3 push(`d0609517f`, dev 눈검수 후).
**현재 미push 3(이번 세션): `b55003fe6`(P1-pipeline) · `d0609517f`(P3·UI) · `53e13f60a`(P2)** — 전부 운영자 push/발행 게이트. P0/P1-engine/P1-UI+PRD는 origin/master.

## 미해소 한계
본문 직행 진입(ViewerStudio rceptNo prop 부재·후속) / 회사인덱스 검색(cmdBar) / snippet 고정 400자 / `fieldIndexRebuild` >800 LoC.
