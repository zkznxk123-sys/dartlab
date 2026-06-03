---
id: operation.docsBuilderRefactor
title: docs 파이프라인 — viewer.do HTML → document.xml zip 정공법 전환
kind: curated
scope: builtin
status: observed
category: operation
purpose: |
  기존 viewer.do HTML → htmlToText() plain text 파이프라인이 heading hierarchy
  lossy → sections layer 가 regex 추론 → 8 commit 덕지덕지 fix 누적. document.xml
  zip 의 <TITLE ATOC AASSOCNOTE> + <TABLE rowspan/colspan> 직접 사용 정공법으로
  전환. zip 은 로컬 임시 보관만 (HF 미공개), parquet 만 공개.
whenToUse:
  - docs 파이프라인 빌더 변경
  - sections layer regex 추론 폐기 검토
  - 새 보고서 schema 추가 (XBRL/주석/별첨)
  - viewer.do → document.xml 전환 회귀 의심
inputs:
  - 대상 종목 / rcept_no
  - 파이프라인 단계 (sync / build / upsert)
  - 검증 범위 (sectionsRawCompare / sectionsParity)
outputs:
  - data/dart/docs/{code}.parquet (공개 SSOT)
  - data/original/dart/docs/{code}/{rcept_no}.zip (로컬 임시, HF 미공개)
  - sections layer 입력 (기존 schema 호환 + atocid/assocnote 신규)
runtimeCompatibility:
  server:
    status: supported
  localPython:
    status: supported
  mcp:
    status: supported
  webAi:
    status: limited
  pyodide:
    status: limited
testUniverse:
  market: KR
  stockCodes:
    - "005930"
---

## §1 — 정공법 원칙

**1.1 원본 = SSOT, parquet = derived**
- `data/original/dart/docs/{code}/{rcept_no}.zip` 은 DART 의 *불변 원본*. 재빌드 시언제든 복원 가능.
- `data/dart/docs/{code}.parquet` 은 *derived* — zip 으로부터 언제든 재빌드.

**1.2 XML 원본 직접 사용**
- DART OpenAPI `document.xml?crtfc_key=<key>&rcept_no=<rcpNo>` 가 자체 schema XML zip 반환.
- 안에 `<TITLE ATOC="Y" AASSOCNOTE="D-0-3-1-0" ATOCID="11">` 가 chapter/sub-section
  hierarchy 를 *명시*.
- `<TABLE>` 의 rowspan/colspan 이 *직접 보존*.
- `<SPAN USERMARK="F-14 B">가. 주요 제품 매출</SPAN>` 이 가/나/다 bold sub-sub marker.
- 추론 0 — sections layer 의 regex inline split 폐기 가능.

**1.3 zip 비공개 (사용자 결정 2026-05-21)**
- zip 은 docs.parquet 와 중복 정보 → HF 미공개.
- `.gitignore` + HF upload guard + GitHub Actions artifact path 3 층 가드.

**1.4 원본 영구 백업 전환 (사용자 결정 2026-06-03)**
- 2026-05-21 의 "안정화 후 zip 단계 폐기" 옵션은 **철회** — 원본은 가공 0 ground truth 로
  **영구 보관**(parquet 운영 방향 변경 시 재파생 테스트). "비공개" 는 유지(publish-ready-gated).
- 통일 백업 store `data/original/` 신설 — DART(정기 `dart/docs/` + 비정기 `dart/allFilings/`) +
  EDGAR(`edgar/docs/{cik}/{accession}.txt` full submission, 전 form). 수집기 = `gather.original`
  (gather 자체포함, `gather ↛ providers` 준수). `allFilingsCollector`(parquet content_raw)와 공존.
- 본 docs 파이프라인의 정기 zip 보관 위치도 `data/original/dart/docs/`로 통일 이전 완료 —
  panel/sections/refScan/freshness 경로 rewire 동반(옛 `dart/original/docs` 폐기).

## §2 — schema 비교

**기존 (viewer.do plain text):**
```
corp_code / corp_name / stock_code / year / rcept_date / rcept_no /
report_type / section_order / section_title / section_url / section_content
```
- section_content = chapter 통째 본문 (4MB+)
- hierarchy 없음 → sections layer 가 regex 추론

**신규 (document.xml `<TITLE>` 기반):**
```
+ atocid     (TITLE 의 TOC unique ID)
+ assocnote  (path-id, D-0-{chapter}-{sub}-{subsub})
```
- section_content = `<TITLE>` 직속 본문만 (sub-section 분리)
- hierarchy 명시 (assocnote path-id)
- `<SPAN USERMARK B>` 가/나/다 → markdown `## prefix` 변환
- `<TABLE>` → markdown table (rowspan 자동 보존)

**호환:** 기존 컬럼 모두 유지. atocid/assocnote 만 신규 추가. sections layer 가
optional 활용 — 호출자 영향 0.

## §3 — 마이그레이션 매트릭스 (8 commit regex fix 폐기)

| commit | 폐기 가능 근거 | 폐기 phase |
|---|---|---|
| `324bbc73` verb-ending negative lookbehind | XML `<TITLE>` 명시 — inline split 불필요 | B-1 |
| `65b78f73` conjunction adverb 차단 | 동일 | B-2 |
| `1e6500f4` table rowspan column shift 정규화 | XML `<TABLE>` rowspan 직접 보존 | B-3 |
| `c4f1a975` circle/bracket inline split | `<SPAN USERMARK B>` 가/나/다 명시 | B-4 |
| `31390efc` heading cell `\n\n` concat 차단 | AASSOCNOTE 가 row identity 제공 | B-5 |

각 단계 — fix 제거 + 5 종목 audit 통과 + 회귀 0 확인 후 다음 단계.

## §4 — 증분 contract (rcept_no upsert)

`ZipDocsCollector.collect(quarters=8)`:
1. `listFilings(stockCode, start="20160101", filingType="A")` → 정기보고서 list
2. 기존 parquet 의 `rcept_no` 이미 있으면 skip
3. 신규 rcept_no 만:
   - `document.xml` API → zip bytes
   - `data/original/dart/docs/{code}/{rcept_no}.zip` 저장 (이미 있으면 skip)
   - XML parse → `<TITLE>` 별 row list
   - 기존 parquet 에 append (`writeParquetSorted` 사용)
4. rebuildFromZips: 저장된 모든 zip 재파싱 → parquet 풀 재빌드 (debug 시)

## §5 — 회귀 가드

**5.1 sectionsRawCompare audit (PR gate)**
```powershell
uv run python -X utf8 tests/audit/sectionsRawCompare.py --codes 005380,005930,035720,207940,000660 --strict
```
- spurious=0 + missing=N (전부터 known) — 회귀 0

**5.2 sectionsParity audit (PR gate)**
```powershell
uv run python -X utf8 tests/audit/sectionsParity.py --codes 005380,005930,035720,207940,000660 --strict
```
- fragmentHeadings=0, chapterMixes=0, koreanInversions=0

**5.3 unit test**
```powershell
bash tests/test-lock.sh tests/sections/test_zipDocsCollector.py -v
```

## §6 — GitHub Actions 통합

**6.1 `.github/workflows/sync-docs.yml`** (신규)
- 매일 02:00 KST + workflow_dispatch
- 4 partition matrix (730 종목/job)
- HF baseline pull → delta zip 다운 → parquet upsert
- artifact upload: `data/dart/docs/` 만 (zip 제외)

**6.2 `.github/workflows/sectionsAudit.yml`** (신규)
- PR 트리거 — sections/ 또는 openapi/zipDocs* 변경 시
- sectionsRawCompare + sectionsParity strict

**6.3 ci-fast 게이트 (29 → 31)**
- sections-parity-fast (기존)
- sections-raw-compare-fast (신규)

## §7 — zip 비공개 강제 (3 층 가드)

1. `.gitignore` — `data/dart/original/` + `data/original/` 라인
2. HF upload script (`.github/scripts/sync/bulkUploadHf.py`) — `original` category explicit 거부 (`/data/original/` 도 `DATA_RELEASES` 미등록이라 업로드 경로 진입 0)
3. GitHub Actions artifact upload path — `data/dart/docs/` 만

## §8 — 호출 cookbook

**8.1 단일 종목 수집 (사용자):**
```python
from dartlab.providers.dart.openapi.zipCollector import ZipDocsCollector
c = ZipDocsCollector("005930")
c.collect(includeQuarterly=True)
```

**8.2 sections layer 호출:**
```python
from dartlab.providers.dart import Company
sec = Company("005930").sections   # 새 schema 입력으로 자동 동작
```

**8.3 GitHub Actions 수동 트리거:**
```powershell
gh workflow run sync-docs --ref master -f codes=005930
gh run watch
```

## §9 — 안정화 후 미래 옵션

docs.parquet 완벽 판단 (sectionsRawCompare spurious=0 종목 비율 ≥ 95%) 시:
- zip 저장 단계 폐기
- `document.xml` → bytes → 메모리 streaming 파싱 → parquet upsert (디스크 zip 0)
- `data/dart/original/` 폴더 완전 삭제
- 사용자 명시 결정 시에만 진행 — 자동 폐기 X

## §10 — Phase A 본진 합류 결과 (2026-05-21)

**근본 회귀 차단 (zipDocsXml.py):**
- `parseSectionsByTitle` body.iter() 재귀가 외부 TABLE 의 markdown 추가 + 내부 P/SPAN
  도 leaf 로 별도 처리 → 035720 카카오 종목 한 rcept content 420MB+ 폭증. DFS 명시
  walker + leaf-return 으로 nested duplication 0.
- `_tableToMarkdown` iter('TR') / `.//TD` xpath 가 nested table 의 TR/cell 까지 외부
  row 로 캡쳐 → 한 table 의 markdown 420MB+ (5030 row + 26517 cell). 직속 TR /
  TBODY/THEAD/TFOOT 안 TR 만 + cell 도 직속 자식 only.

**streaming 빌더 (`ZipDocsCollector.rebuildFromZips`):**
- `data/original/dart/docs/{code}/*.zip` 로컬 zip 만으로 streaming pyarrow ParquetWriter
  풀 재빌드. API 호출 0. rcept 단위 row group append → 메모리 누적 0.
- cell split (`MAX_CELL_BYTES=1MB` paragraph 단위) + regular `pa.string()` schema —
  polars `iter_rows` PyObject panic + 32-bit offset 회귀 차단.

**5 종목 검증 (005380/005930/035720/207940/000660):**
- sectionsParity: 0 violations / 5 codes
- sectionsRawCompare: spurious=11 → **Phase B-1 후 spurious=2** (commit 153bbdd45)
- polars panic: 0
- OOM: 0 (035720 broken builder 2.4GB → 14MB fixed)
- pytest `tests/sections/test_zipDocsCollector.py`: 7 passed

**Phase B-1 — `_detectHeading` 가드 추가 (commit 153bbdd45):**
- `_RE_PAREN_NUM` 결과 label 가 trailing `)` 끝나면 (citation fragment) 차단 + circle
  marker (①~⑳⓪) 포함 시 차단.
- `_RE_SHORT_PAREN` inner 가 `舊 X` (옛 사명 marker) / `,` 포함 (citation) /
  `*` only (placeholder) / `") 참조"` 끝남 → 본문 annotation marker 차단.
- 결과: 207940 (2→0), 000660 (6→0). 005380 의 `마. 동 기준` 2x 만 잔여.

**Phase B-2 — closing noun 합성어 suffix 가드 (commit 65ac3199f):**
005380 잔여 spurious 2x `"마. 동 기준"` 의 근본: `_splitInlineMultiHeadingOnce` 의
closing noun split 이 "동 기준서로 인한..." 의 "기준" 명사를 split 경계로 잡아 가짜
heading 생성. `_LABEL_NOUN_SUFFIX_CHARS` 신설 — closing noun 직후 1-char Korean
suffix 가 합성어 형성 시 split 차단 (기준서/내역서/현황표/계획안 등).

**Phase B-3 — `_RE_KOREAN` 1-char label 가드 (commit 5fe0694db):**
DART XML 본문 line-break 결함으로 단어 끊김 ("...있습니" / "다. 메" / "모리 반도체...")
시 sections 의 `_RE_KOREAN` 가 "다. 메" 를 L3 heading 으로 잡아 textPath segment "메"
잘림. label 이 1글자 한글이면 None 반환.

**Phase B-4 — XML word-wrap join (commit b953860b9):**
DART XML `<P>` 안 `<SPAN>` 들이 word-wrap 단위 분할되는 패턴. 원래 `" ".join` 이
"국내 에서 는" 같은 잘못 추가 공백 생성. `"".join` + multispace 정리로 단어 끊김
복원. tests/sections/test_zipDocsCollector.py 8 passed.

**Phase B-5 잔여 (별도 트랙):**
textPath 잘림 잔여 (예: `사업부문별 > ...` 의 "현황" 누락, `생산능력, 생산실 > ...`
의 "적, 가동률" 누락, 비정상 trailing `'` quote) 은 DART XML 의 `<P>` 단위 분할
구조 — Phase B-4 의 SPAN join 으로 단어는 복원했으나 P 간 join 은 미해결. sections
layer 의 line-join 회복 로직 또는 XML parser 의 consecutive short-P merge 추가
검토 필요. 사용자 명시 시 진행.

## §11 — 2026-05-22 진척 (R1/R2/R3 + 본진 zip 수집 API + 추가 가드)

**본진 zip 수집 API (`bulkZipFetcher.py`, 커밋 224a08c28 + ae88dad09):**
- `DartClient`: `_KeySlot` 풀 스레드 안전 재설계 (커밋 224a08c28).
- `_acquireSlot`: **sequential exhausted 패턴** 으로 재변경 (커밋 5de760ff7) — finance/
  syncRecent.py 의 `_activeClient` 와 동일. 키 1개로 580 rpm 소진 후 다음 키 (매 요청
  rotation 아님). 매 요청 키 rotation 패턴이 DART per-IP anti-abuse 트리거 → 차단.
- `fetchZipsParallel(client, targets, outDir, workers=4)` — ThreadPoolExecutor +
  `safeWriteBytes(.tmp.{tid}.{ns} → os.replace atomic)`. workers=4 = finance 의
  `asyncio.Semaphore(4)` 패턴.
- `collectAllOriginalZips(codes=None)` — 고수준 진입점. `data/dart/docs/*.parquet` 의
  rcept_no 자동 수집. 사용자: `from dartlab.providers.dart.openapi import
  collectAllOriginalZips; stats = collectAllOriginalZips()`.

**R1/R2/R3 진척 (1,846 / 2,928 corps 새 schema = 63%):**
- R1 sequential 패턴 검증 (커밋 5de760ff7 + 본문 §13):
  - Round 1-4 (옛 매-요청 rotation): saved ≤ 1k / 세션, 즉시 IP 차단
  - **Round 5 sequential exhausted: saved=28,091 / failed=26,110** (28× 더 진행, IP 차단 X)
  - 잔여: 5 키 일일 한도 020 도달 → midnight KST reset 후 진행
- R2: rebuildAllFromZips offline — **1,846 corps / 2,735,701 rows / errors=0**
- R3: 5 baseline sectionsParity=0 / sectionsRawCompare spurious=0.
  - 100 random sample v6 (R2 round 1 직후): spurious=0 corps **70.4%** / spurious total 68
  - 100 random sample v9 (R2 finalized + B-5 P-merge + 4 가드 + 15 perf opts):
    spurious=0 corps **75.5%** / spurious total **46** (**-32%**)
  - 제품 기준 ≥90% 여전히 미달. 잔여 worst (003480 sp=7, 033920 sp=5, 015230 sp=3)
    는 corps 별 특수 패턴 — 일반 가드로 잡기 어렵. 향후 corp 별 deep audit 필요.

## §14 — Phase 3 디스크 캐시 + 병렬 batch API (2026-05-23)

사용자: "sections만드는시간이 8초인데 더줄일수는 없을까" + "테스트로 확실히가능한건지 확인하고 본진투입결정"

**옵션 1 — sections 디스크 캐시 (`diskCache.py`, 커밋 0e08ef731):**
- `data/dart/sectionsCache/{stockCode}_{topicsHash}.parquet` 저장
- Freshness: `docs/{stockCode}.parquet` mtime > cache mtime → stale → rebuild
- `topicsHash` = `blake2b(",".join(sorted(topics)), digest_size=3)`. None = `"all"`.
- 효과:
  - 1st cold build: 13.48s (+ 디스크 save)
  - 2nd in-mem hit: 1.05s
  - 3rd disk hit (in-mem cleared): **1.27s** (cold 7s 대비 ~5×)
- **5 baseline disk hit total: 4.99s = mean 1.0s/corp** = **마법 수준 sub-2s 달성**
  (cached path 한정. cold 5-8s 는 별도 큰 refactor 필요).
- 프로세스 재시작 후에도 build cost 회피.

**옵션 3 검증 — ProcessPool batch (`buildBatchParallel`, 커밋 344a45779):**
- POC (sectionsParallelPoc.py): 5 baseline 직렬 61.6s → 병렬 5 worker 19.0s = **3.25×**
- 본진 API `buildBatchParallel(codes, workers=None)`:
  - default workers = `min(len(codes), os.cpu_count())`
  - 각 process 1 corp build + 디스크 캐시 자동 저장
  - 결과 `dict[code, bool]`
- 검증: 5 corps via 본진 API **16.42s** (3.7× speedup, 모두 success)
- 후속 호출은 디스크 cache hit (~1.3s)

**사용 예:**
```python
# 단일 corp — in-mem + disk cache 자동 hit
sec = Company('005930').sections   # 1.3s if disk cache hit, 7s if cold

# 배치 — ProcessPool 병렬 + 디스크 캐시 일괄
from dartlab.providers.dart.docs.sections.diskCache import buildBatchParallel
results = buildBatchParallel(['005930', '035720', '005380', '207940', '000660'])
# 16s (5 corps), 후속 단일 호출 모두 ~1.3s.
```

## §15 — DART per-IP 발견 → sequential exhausted 정공법 (2026-05-22)

**문제:** 5-key 매-요청 rotation 패턴 (`_acquireSlot` 가 매번 가장 빨리 가용한 slot 선택)
이 DART per-IP anti-abuse 트리거. 같은 IP 에서 5 키 빠르게 번갈아 사용 = "한도
회피 시도" 분류 → ~1k 요청 후 TCP 연결 차단.

**해결:** `.github/scripts/sync/syncRecent.py` 의 `_activeClient` 패턴 동일 적용:
- 키 1 개 580 rpm 소진 후 (020) 다음 키
- 같은 키로 동시 worker N=4 (finance 의 `asyncio.Semaphore(4)`)
- 매 요청 rotation X — single-key 사용 sustained

**검증 (Round 5):**
- saved=28,091 / failed=26,110 (vs 옛 패턴 saved≤1k / failed≈55k)
- 28× 다운로드 진행, 그 후 5 키 일일 한도 020 도달 (정상 — daily reset 까지 대기)
- 본 패턴 == DART 가 의도한 사용 방식.

**Phase B-5 가드 4종 추가 (`textStructure.py`, 커밋 70a0c56ed):**
- `_RE_PAREN_NUM` body sentence detection — `" : "` 콜론, `" 등주)"`, `,` 다중 ≥ 2.
- `_RE_PAREN_NUM` connector `내지` 시작 차단.
- `_RE_PAREN_KOR` temporal marker (당/전/전전/당기/전기/...) 차단 (재무제표 기간 컬럼
  위장).
- `_RE_PAREN_KOR` connector `내지` 시작 차단.
- `_RE_CIRCLED` multi-marker line (① ② ③ 동시) 차단 — body list item 식별.
- 5 baseline parity 회귀 0.

**HF 업로드 파이프라인 (`.github/scripts/sync/bulkUploadHf.py`, 커밋 56b841944):**
- `--force` — 전체 재업로드 (schema 마이그레이션).
- `--since N` — 최근 N초 안 mtime 변경 파일만.
- R1+R2 완료 후 `bulkUploadHf.py docs --force` 가 최종 단계.

**P-단위 line-join 완료 (커밋 fd76bdb8a):**
`zipDocsXml.parseSectionsByTitle._mergeShortPs` — 인접 P 둘 다 len ≤ 20 + 첫 P 가
sentence-end (다./요./니다././?/!/);]) 아님 → 같은 line concat. word-wrap 결함
"사업부문별\n\n현황" → "사업부문별현황" 복원. 5 baseline parity 회귀 0.

## §12 — Sections 성능 최적화 (2026-05-22)

**5 baseline cold build 3-trial mean (모든 cache clear, baseline 1052s):**
- Trial 1: 28.40s / Trial 2: 27.58s / Trial 3: 27.74s
- **Mean: 27.91s ± 0.44s** (per-corp 5.58s)
- **Speedup: 1052s / 27.91s = 37.7×**
- Cold→warm cache 8× 추가 (warm 3.6s for 5 baseline)
- 10 random R2-rebuilt corps mean: 7.03s/corp

**최적화 commit 11종 (모두 5 baseline parity 회귀 0):**
1. `467ec1b7c` `_detectHeading` first-char dispatch frozenset(43) — 본문 line 즉시 None
2. `2d4e2be63` `_splitInlineMultiHeadingOnce` trigger short-circuit — 7 finditer 절약
3. `c1b413340` `_normalizeRowspanShift` 핫 패스 short-circuit (`|  |` count < 3)
4. `5342165ad` `_cleanLine` fast-path — `&`/` `/`\t` 무 시 rstrip 만
5. `42458a153` `_repairLineBreaks` substring prefilter — `니다.` 무 시 regex 회피
6. `5cc845d92` `_gateHeadingLabel` regex precompile + length-based short-circuit
7. `7b152dba4` `_detectHeading` lru_cache 16384 → 65536 (4.3× 추가)
8. `0b22317a3` `_normalizeRowspanShift` 단일 패스 + dict allocation 제거
9. `307ee9bb2` `_normalizeHashCell` fast-path — paren/digit/period 무 시 5 regex 절약
10. `00ccc708c` 분리자 검출 set allocation 제거 (strip('-:') 직접 비교)
11. `3a6e6ce1a` `_headingPathStrings` helper — 3 list 1 패스 + 5 join (expansion.py)
12. `f10e815d0` textStructure 경로 문자열 1 패스 (body flush + heading push)
13. `c3cf13769` 추가 lru_cache 사이즈 확대 (_normalizeHeadingText 2048 → 16384 등)
14. `f1a789827` parseTextStructureWithState stack copy-on-write — 65k dict copy 회피
15. `05279a3ec` 주기 GC 를 gen 0 만 호출 — 8 회 × 60ms → 8 회 × 10ms 단축

**상위 핫스팟 (post-optimize, 035720 profile):**
- `_normalizeRowspanShift`: 2.0s (12k 호출, prefilter 통과한 진짜 shift table 만)
- `str.strip`: 1.56s (15M 호출, C 구현 → 100ns/call 한계)
- `_splitInlineMultiHeadingOnce`: 1.1s (57k 호출, trigger 통과만)
- `pipeline.sections`: 1.0s (orchestrator entry)
- `_expandStructuredRows` cumtime: 5.3s
- `parseTextStructureWithState` cumtime: 3.3s

**다음 잠재 win (large refactor, 미진행):**
- Polars vectorization of `_expandStructuredRows` per-row Python loop → 1.6s 가능
- Cython/Rust 의 `_normalizeRowspanShift` → 300ms 가능
- 위 2개 적용 시 sub-2s/corp ("마법 수준") 도달 추정.

**메모리 측정 (035720, tracemalloc):**
- Build peak: 168MB
- Final DataFrame estimated_size: **6MB**
- **28× 비효율** — intermediate dict allocations (`topicMap` / `rowMeta` /
  `_expandStructuredRows` 의 dict copy) 가 peak 의 핵심.

**메모리 최강 잠재 win (large refactor, 미진행):**
- `_expandStructuredRows` Iterator → Polars 컬럼별 직접 build (Python dict 0)
- `topicMap` 의 `dict[tuple, dict[str, str]]` → Polars MultiIndex DataFrame 직접 build
- 위 적용 시 peak ~ 20-30MB ("마법 수준") 도달 추정.
