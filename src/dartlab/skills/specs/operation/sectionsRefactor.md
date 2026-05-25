---
id: operation.sectionsRefactor
title: sections 파이프라인 — 구조 정리 + 리팩터링 + 속도 최적화 방향
kind: curated
scope: builtin
status: observed
category: operation
purpose: dart/docs/sections/ 9538 줄 16 파일 책임 경계 정리 + 부채 원장 + 리팩터링/속도 최적화 후보 정리. 새 작업 진입 전 본 문서 §N 참조.
whenToUse:
  - sections 파이프라인 리팩터링
  - sections 속도 최적화
  - sections 메모리 최적화
  - chapter row catch-all 회귀
  - placeholder textPath alias 회귀
  - table textPath 누락 회귀
  - blockOrder gap 회귀
inputs:
  - 작업 목적
  - 대상 단계 (mapper / 수평화 / 주석 수평화)
  - 검증 범위 (parity test + invariant test)
runtimeCompatibility:
  server:
    status: supported
  localPython:
    status: supported
  mcp:
    status: supported
  webAi:
    status: supported
  pyodide:
    status: supported
testUniverse:
  market: KR
  stockCodes:
    - "005930"
---

# sections 파이프라인 — 구조 정리 + 리팩터링 + 속도 최적화 방향

> dartlab 공시뷰어의 핵심 — DART 정기보고서 (사업/분기/반기) 의 raw parquet 을 (topic × period) wide 보드로 변환하는 4 단계 파이프라인. 본 문서는 현재 9,538 줄 16 파일의 책임 경계 정리 + 부채 식별 + 개선 방향.
>
> 라우팅: 사용자 API 는 `c.sections` / `c.show(topic)` / `c.notes()`. 본 모듈 직접 호출 금지 (`operation.apiContract`). 강행규칙은 `CLAUDE.md`, 4 계층 import 룰은 `operation.architecture`.

## 1. 책임 3 단계 + 파일 매트릭스

DART parquet (raw HTML chunked) → 사용자가 보는 (topic, blockType, blockOrder) × period wide DataFrame 까지의 변환은 **3 단계**.

| 단계 | 역할 | 핵심 파일 | LOC | 입출력 |
|---|---|---|---|---|
| ① **매퍼** | section_title (raw DART heading) → 16 topic 매핑 + DART chapter 구조 인식 | `mapper.py` `chunker.py` `sectionsBase.py` `textStructure.py` | 591 + 660 + 536 + 464 = **2251** | `"1. 회사의 개요"` → `("companyOverview", chapter=I, majorNum=1)` |
| ② **수평화 (sections)** | period 별 row 들을 (topic, segmentKey) 단위로 group → period 컬럼으로 pivot. text/table block 분리, heading state machine 으로 textPath 부여 | `pipeline.py` | **1834** | period 별 raw row → (topic × blockOrder × period) wide DataFrame |
| ③ **주석 수평화** | sections 결과에서 주석 (consolidatedNotes/financialNotes) topic 의 표를 heading 별로 추출 + period 간 merge | `extractors.py` `views.py` `viewsContext.py` `viewsRetrieval.py` `analysis.py` | 448 + 689 + 266 + 286 + 1248 = **2937** | sections wide → `TopicSubtables` (heading × period) |

부속:
- `types.py` (784) — `SectionChunk`/`SectionResult`/`YearSections` 데이터 클래스.
- `runtime.py` / `runtimeProjection.py` (776 + 187) — runtime topic projection (`chapterTeacherTopics`, `applyProjections`, `detailTopicForTopic`, `projectionSuppressedTopics`).
- `tableParser.py` (505) — markdown table 파싱.
- `artifacts.py` (197) — sections cache parquet 보관 경로.

## 2. 단계 ② sections 수평화 — 4 Phase 분해

`pipeline.py` 1834 줄의 본체. `sections(stockCode, topics)` 호출 시 내부 4 Phase 순서로 실행.

### Phase 1 — `_getPrepared(stockCode)` → `_PreparedRows`

LRU 캐시 (size=1) 진입점. 같은 stockCode 반복 호출 시 parquet 재로드 회피.

- `iterPeriodSubsets(stockCode)` — parquet 로드 + period 별 subset (`(periodKey, reportKind, contentCol, subset)` iter).
- `_reportRowsToTopicRows(subset, contentCol)` — period 별 row 생성 (line 928~).
  - parquet 의 `section_title` 행을 순회. `parseMajorNum` 로 chapter row vs sub-section row 구분.
  - **chapter row** (예 `"I. 회사의 개요"`) → pendingChapter 보류.
  - **sub-section row** (예 `"1. 회사의 개요"`) → pendingChapter 폐기 (sub-section 이 chapter content 의 concat 본을 cover), section_title prepend 후 `_registerContent`.
  - pendingChapter 는 다음 chapter 또는 끝 시점에 `_flushPending()` 으로 처리. sub-section 이 있으면 chapter content 의 block 중 sub-section line set 에 없는 *unique block* 만 lonely-등록 (chapter-only 표/footnote 손실 차단, commit `dd2c6c0a8`).
- 결과: 모든 period 의 row 를 `_periodKey` 컬럼 추가 후 vstack 누적 → `_PreparedRows.periodRowsDf` (단일 polars DataFrame).

### Phase 2 — `_expandStructuredRows(rows)` → generator of dicts

row 별 heading 구조 파싱. period 별로 호출.

- `parseTextStructureWithState(text, ...)` (textStructure.py) — text 본문의 heading 계층 파싱.
  - `_RE_BRACKET` / `_RE_ROMAN` / `_RE_NUMERIC` / `_RE_KOREAN` / `_RE_PAREN_NUM` / `_RE_PAREN_KOR` / `_RE_CIRCLED` 8 regex 로 level 1~6 heading 검출.
  - 이전 row 의 heading stack 상태를 `initialHeadings` 로 받아 *cross-block* heading 추적 (긴 본문이 여러 block 으로 split 됐을 때 path 보존).
- text block → `nodes` 분해. 각 node 는 `(text, textNodeType, textLevel, textPath, textPathKey, textSemanticPathKey, segmentKeyBase, ...)`.
- **table block** → 직전 heading state 의 textPath 를 row 에 박음 (commit `0f719c442`). 주석 topic 은 `segmentKeyBase = f"table|sem:{lastSemKey}"` (heading 기반 join), 비주석 topic 은 `f"table|sb:{sourceBlockOrder}"`.
- `segmentKey = f"{segmentKeyBase}|occ:{count}"` — 같은 (topic, segmentKeyBase) 내 occurrence count 부여 → 기간 간 같은 순서 같은 heading 의 row 가 동일 segmentKey 로 join.

### Phase 3 — `_sectionsPolarsOnly` → wide DataFrame

per-period row dict → polars 변환 후 group_by + pivot.

- 5 단계 polars 변환:
  - **2a** `metaDf` — (topic, segmentKey) 별 last() (최신 period 의 메타 값 보존).
  - **2b** `orderDf` — sortOrder/sourceBlockOrder/segmentOrder min + latestMissing/latestRank 조건부 집계.
  - **2c** `pathDf` — 4 종 textPathVariants set 누적 (period 간 textPath 차이 추적).
  - **2d/2e/2f** `topicChapterDf` / `topicFirstSeqDf` / `topicIndexDf` — topic 별 chapter / 첫 등장 (majorNum, sortOrder) / 정렬 index.
  - **pivot** — `(topic, segmentKey) × periodKey` → 각 period 컬럼 1 개. 미공시 cell = None.
- **Phase 4 freqMeta** — annual/quarterly period cell 카운트 + latest cell 검출.
- **Phase 5 sort** — 9-tuple sort key (`_topicMajorNum, _topicFirstSeq, _topicIndex, _freqScopePriority, latestMissing, latestRank, firstRank, _orderSegmentOccurrence, segmentKey`).
- **Phase 6 blockOrder** — topic 별 0-based contiguous `cum_count`.
- **Phase 7** — schema cast (Int64/Boolean/List/Categorical).

### Phase 4 — `_dropChapterCatchAllDuplicates(df)` → cleanup

post-hoc dedup. 옛 design 에선 chapter row catch-all 과 sub-section row 가 동일 sourceBlockOrder 로 중복됐었음. 현재 Phase 1 의 unique-block fix 로 *대부분* 차단되지만 defensive layer 로 남아있음. blockOrder contiguous 재부여도 여기서.

## 3. 단계 ③ 주석 수평화 — `extractors.py` 의 책임

`topicSubtables(blocks, topic)` 진입점. sections wide 결과를 받아 주석 topic 의 표를 heading 별로 정리.

- `_TopicSelector` — topic 별 row 필터 (NOTES_TOPICS 한정).
- `_parseOneCellTable` — 단일 cell 안에 여러 표가 concat 된 케이스 (DART 주석 흔한 패턴) 를 markdown 표 단위로 분리.
- `_mergeAcrossPeriods` — 같은 heading 의 표를 period 간 row alignment (key column 기준 outer join). 표 셀이 기간 따라 변하면 변화 추적 가능.
- 결과: `TopicSubtables` (heading × period 의 list of `ParsedSubtopicTable`).

## 4. 핵심 부채 (지금 코드의 문제)

### 부채 1. `pipeline.py` 1834 줄 단일 파일

7 책임이 한 파일에:
- LRU cache (`_PreparedRows` / `_getPrepared` / `clearPreparedCache`, ~100 줄).
- comparable path normalization (`_comparablePathInfo` 등, ~100 줄).
- period iteration (`iterPeriodSubsets`, ~100 줄).
- content block split (`_splitContentBlocks`, ~50 줄).
- polars-only main (`_sectionsPolarsOnly`, ~450 줄).
- topic row 생성 (`_reportRowsToTopicRows`, ~190 줄).
- heading state expansion (`_expandStructuredRows`, ~160 줄).
- freq meta (`_periodFreq` / `_freqSortKey` / `_rowFreqMeta`, ~80 줄).
- public entry (`sections`, ~430 줄 docstring 포함).
- dedup cleanup (`_dropChapterCatchAllDuplicates`, ~50 줄).

테스트 / 회귀 추적이 어렵고, 한 파일 변경이 7 책임 모두 영향. **분리 권고 (§5 참조)**.

### 부채 2. chapter row dedup 의 2 중 방어

같은 회귀 (chapter catch-all 중복) 를 두 곳에서 막음:
- `_reportRowsToTopicRows` 의 unique-block-only 등록 (Phase 1 단계).
- `_dropChapterCatchAllDuplicates` 의 post-hoc drop (Phase 4 단계).

전자가 강력하므로 후자는 *방어 layer* — 단, 동일 fix 의도가 2 곳에 분산되어 디버깅 시 어디서 일어났는지 추적 어려움. **둘 중 하나로 단일화 필요**.

### 부채 3. segmentKey 설계가 분산

key 부여 룰이 `_expandStructuredRows` 안에 4 곳:
- text/no-heading: `body|lv:0|a:empty`
- text/with-heading: `body|p:{semanticPath}` 또는 `body|lv:{n}|a:empty`
- text/heading-node: `heading|lv:{n}|p:...` 또는 `heading|{kind}|lv:{n}|p:...` (textStructure 안)
- table: `table|sem:{lastKey}` (notes) 또는 `table|sb:{sb}` (non-notes)

각 호출 시점에 occurrence count 누적. 룰이 코드 곳곳에 *literal 문자열* 로 분산되어 segmentKey 의 schema 가 명시 안 됨. **`SegmentKeyer` 클래스로 추상화** 권고.

### 부채 4. mapper.py 가 L1 (providers/dart) 안

`sectionMappings.json` 매핑 데이터 + `mapSectionTitle` 매핑 엔진이 `providers/dart/docs/sections/` 안. 4 계층 SSOT 원칙 (`operation.architecture`) 으로는 reference 데이터는 L1.5 `reference/docs/` 에 두는 게 옳음. EDGAR/EDINET 와 공유 가능성 (사실상 0 이지만, 격자 원칙).

### 부채 5. heading detection 의 textLevel 충돌

`textStructure.py` 의 8 regex 가 level 1~6. 주석 본문에서 흔한 패턴:
- "1. 회사의 개요 (연결)" → level 3 (numeric)
- "(1) 지배기업의 개요" → level 5 (paren_num)

heading stack pop/push 룰이 `level >= current` 일 때 pop. level 3 (numeric) 이 등장하면 level 4/5/6 모두 pop. 그러나 다음 level 3 heading 등장 시 *형제* 라야 하는데, 실제 textPath 는 직전 level 3 heading 으로 reset 됨 (이전 level 3 가 사라짐). DART 주석에서 흔히 발생 — `재고자산 (연결)` 다음 `금융위험관리 (연결)` 가 같은 부모 (`연결재무제표 주석`) 아래 형제. **현재 동작은 부모 정보를 잃음**.

이 부채는 textPath 길이가 1 (단일 heading) 인 row 가 다수 발생하는 원인. 부모 stack 보존 로직 필요.

### 부채 6. LRU cache size = 1

`_PREPARED_CACHE_MAX = 1` — 같은 종목 반복 호출만 cache. 다종목 batch (예 scan 엔진의 종목 reduce) 시 매번 재로드. 메모리 trade-off 로 인한 의도된 제한이지만, 멀티 종목 dashboard 빌더는 명시적 cache disable 후 일괄 처리가 더 적합.

## 5. 리팩터링 방향 — 7 모듈 분해

`pipeline.py` 1834 줄 → 7 모듈 분리. 각 모듈 단일 책임. 모두 같은 `dart/docs/sections/` 안.

| 새 모듈 | LOC 추정 | 책임 |
|---|---|---|
| `pipeline.py` (slim) | ~250 | 공개 `sections(stockCode, topics)` 진입점 + `_PreparedRows` + `_getPrepared` LRU cache. 다른 모듈을 thin orchestrate. |
| `periodIter.py` | ~100 | `iterPeriodSubsets` + `_periodSortKey` + period column 검출 헬퍼. |
| `reportRows.py` | ~250 | `_reportRowsToTopicRows` + `_splitContentBlocks` + pendingChapter 관리 + unique-block 추출. |
| `expansion.py` | ~250 | `_expandStructuredRows` generator + heading state machine 사용. |
| `aggregation.py` | ~500 | `_sectionsPolarsOnly` 본체 (5 단계 group_by + pivot + sort). |
| `pathNormalizer.py` | ~150 | `_comparablePathInfo` + `_normalizeComparableSegment` + business unit anchor. |
| `freqMeta.py` | ~100 | `_periodFreq` / `_freqSortKey` / `_rowFreqMeta` / freqScopePriority. |
| `dedupCleanup.py` | ~80 | `_dropChapterCatchAllDuplicates` (defensive, 향후 폐기 가능). |

총 ~1680 줄 (현 1834 줄). 외부 API 변경 0 — `from .pipeline import sections` 만 유지.

검증 : 5 종목 parity test (`tests/providers/dart/docs/test_sectionsPolarsParity.py`) 가 회귀 가드. baseline parquet shape/values 일치 강제.

## 6. 속도 최적화 — 측정 후 우선순위

현재 SK하이닉스 (~14,000 row, 41 period) 처리 시간 measure 필요. 직접 측정 시:

```python
import time
from dartlab.providers.dart.docs.sections.pipeline import sections, _preparedCache
_preparedCache.clear()
t0 = time.perf_counter()
df = sections("000660", topics=None)
print(f"first call: {time.perf_counter()-t0:.2f}s, shape={df.shape}")
t1 = time.perf_counter()
df = sections("000660", topics=None)
print(f"cached call: {time.perf_counter()-t1:.2f}s")  # _getPrepared cache hit
```

### 후보 A — Phase 1 의 vstack 누적 → pl.concat

```python
# 현재 (~ O(N × periods) 반복 vstack):
for ...: periodRowsDf = periodRowsDf.vstack(df)
# 개선 (단일 concat):
periodDfs.append(df)
...
periodRowsDf = pl.concat(periodDfs, how="diagonal_relaxed").rechunk()
```

이미 Phase 3 (`_sectionsPolarsOnly`) 의 periodDfs 변환은 단일 concat 사용. Phase 1 도 동일하게.

### 후보 B — `_sectionsPolarsOnly` 의 5 group_by 통합

`metaDf` / `orderDf` / `pathDf` 가 같은 `(topic, segmentKey)` grouping. 한 번의 group_by + 여러 agg 로 통합 가능:

```python
metaOrderPath = df.group_by(["topic", "segmentKey"]).agg([
    pl.col("blockType").last(),
    ...all meta...,
    pl.col("sortOrder").min().alias("firstRank"),
    ...all order...,
    _pathAgg("textPathKey").alias("textPathVariants"),
    ...all path...,
])
```

3 group_by → 1 group_by. polars 가 같은 키 grouping 을 hash 한 번에 처리. **20~40% 빨라질 가능성** (group_by 비용이 큰 step).

### 후보 C — `_expandStructuredRows` generator → polars

heading state machine 은 sequential dependency (이전 row 의 stack 이 다음에 영향) 이므로 polars expression 으로 옮기기 어려움. **유지**. 단, 대량 batch 시 multiprocess (rayon 안에서) 로 period 병렬 처리는 가능 — 같은 period 안의 row 들은 state machine 직렬, 다른 period 들은 독립.

### 후보 D — Categorical cast 시점 조정

현재 마지막에 모든 str 컬럼 Categorical cast. 그러나 일부 컬럼은 cardinality 가 매우 높음 (예 `text*` columns 자체는 cast 안 됨, period cell 만). 검토: cardinality 가 row 수에 근접하는 컬럼은 Categorical 이 오히려 메모리 낭비. profile 후 선별.

### 후보 E — `_PREPARED_CACHE_MAX` 환경변수화

다종목 batch 시 cache size 늘리는 옵션. 예 `DARTLAB_SECTIONS_CACHE=10` 환경변수. dashboard 빌더처럼 50 종목 처리 후 다시 같은 종목 안 보는 케이스는 size=1 적정 (기본 유지).

### 후보 F — Phase 1 의 `to_dicts()` 회피

`_reportRowsToTopicRows` 결과를 list[dict] 로 변환 후 `_expandStructuredRows` 에 넘김. heading state machine 이 dict 가정 — 변경 비용 큼. 그러나 dict 가 매 row 생성 = Python heap 압박. 큰 회사 (50k row) 에서 ~100MB Python heap. **장기적으로 polars Struct 컬럼으로 옮길 가치**.

## 7. 우선순위 권고

본 리팩터링/최적화의 *완료 순서* (✓ = 완료):

1. ✓ **§4 부채 1 — pipeline.py 모듈 분리** (1838 → 688 줄 slim + 7 신규 모듈). master `2e91d2ce9`.
2. **§4 부채 2 — chapter row dedup 단일화**. Phase 1 의 unique-block fix 가 모든 케이스 cover 하는지 측정 audit 박은 뒤 Phase 4 `_dropChapterCatchAllDuplicates` 폐기 (후속 PR).
3. **§4 부채 5 — heading stack 부모 보존**. 같은 level heading 형제 시 부모 보존. notes topic textPath 깊이 1 → 2~3 회복. **의미 변경** — parity baseline regen 필요 (별도 PR).
4. ✓ **§6 후보 B — group_by 통합**. 3 group_by → 1 group_by. master `6496da651`.
5. ✓ **§4 부채 3 — `SegmentKeyer` 추상화**. literal 4 곳 통합. master `ace890903`.
6. **§4 부채 4 — mapper L1.5 reference 이전**. 의존성 사이클 검토 후. 우선순위 낮음.

각 항목은 단일 commit 단위. parity test + ruff format/lint 동행.

## 8. 회귀 가드

본 리팩터링 진행 시 *항상* 같이 확인:

- `bash tests/test-lock.sh tests/providers/dart/docs/sections/ -v` — 94 test PASS.
- `bash tests/test-lock.sh tests/providers/dart/docs/test_sectionsPolarsParity.py -v` — 5 종목 baseline parquet 과 shape/dtypes/values 일치.
- `bash tests/test-lock.sh tests/providers/dart/docs/test_sectionsInvariants.py -v` — pivot 충돌 0 + 8자 임계 + selectReport 정책 3 invariant.
- 시각 검증: `sections('000660', topics=None)` 의 결과를 viewer 에서 확인. table textPath 부여 (`consolidatedNotes` 모든 table row null 0) + blockOrder contiguous (gap 0).

본 문서는 *부채 원장*. 항목별 진행 commit 메시지에 `sectionsRefactor.md §N` 참조.

## 9. 무손실 보장 — round-trip 회계

원본 `docs.parquet` 의 `section_content` 총량 vs `c.sections` 결과의 모든 period 컬럼 총량을 byte/line/row 3 지표로 비교. baseline 박제 후 회귀 tolerance 0.02 차단.

```powershell
uv run python -X utf8 tests/audit/sectionsLossAccount.py --check
uv run python -X utf8 tests/audit/sectionsLossAccount.py --write-baseline
```

`tests/audit/sectionsLossAccount.py` + `tests/audit/_baselines/sectionsLossBaseline.json`. nightly 게이트 `sections-loss`. 005930 단일 측정 결과 byte 보존율 **0.511** — 의도 drop (chapter 결정 전 prelude · projection-suppressed · detailTopic 매치) 누적의 첫 정량 관찰치.

해석: byte 보존율 자체보다 *baseline 회귀 추적* 이 본 audit 의 가치. 회귀 0.02 초과 시 fail.

### 잠재 손실 3 종 — invariant 가드

silent → 측정 가능 상태 전환:

1. **pivot last-wins 충돌** — `aggregation.py` 의 `_sectionsPolarsOnly` 가 pivot 직전 `(topic, segmentKey, periodKey)` 중복 카운터 계산 + logger.warning. `DARTLAB_SECTIONS_STRICT=1` 환경변수 시 ValueError 승격. invariant: `test_no_pivot_key_collision` (5 종목 fixture).
2. **chapter dedup 8자 임계** — `reportRows.py:1023` 의 `meaningful = [ln for ln in missing if len(ln) >= 8]` 임계. invariant: `test_chapter_dedup_8char_recall` (합성 골든).
3. **selectReport 정정공시 silent drop** — `providers/reportSelector.py::selectReport` 가 정정공시 drop 시 `logger.info` 한 줄 (year, kind, drop 건수, 선택 type). invariant: `test_selectReport_correction_policy` (합성 DataFrame).

본 invariant 는 `tests/providers/dart/docs/test_sectionsInvariants.py` 에 단일화. 모두 PASS 가 가드.

## 10. 정밀도 트랙 (후속 PR)

무손실 인프라 (§9) 가 박힌 위에서 정밀도 향상을 측정 가능. 본 트랙은 *의미 변경* 이라 parity baseline regen 필요:

1. **heading stack 부모 보존** (§4 부채 5) — textStructure.py 의 stack pop 룰. 같은 level heading 형제 시 부모 보존. notes topic textPath 깊이 1 → 2~3 회복. 측정: invariant 1 (충돌 0 유지) + memory peak 유지 + parity baseline regen.
2. **mapper.py 미매핑 패턴 측정·보강** — `tests/audit/sectionsMappingRate.py` 신설 (sample 200 종목 × `measureMappingRate`). 매핑률 < 98% 시 fail. unmapped top-10 stderr.
3. **chapter dedup 8자 임계 골든** — 005930 또는 특정 종목의 chapter row + sub-section row 골든 박제. 임계 조정 시 회귀 가드.

각 항목 진행 전 §9 의 4 audit (loss + memory + 신규 mapping + 신규 benchmark) baseline 박제 필수.

## 11. 속도·메모리 측정 인프라

### 속도

`operation.sectionsRefactor §6 후보 B` 적용 (3 group_by → 1 group_by, master `6496da651`). 후속 측정 audit `tests/audit/sectionsBenchmark.py` (신설 예정) — 5 종목 × 3 시나리오 × 3 회 median 박제, regression 10% warn.

`DARTLAB_SECTIONS_CACHE` 환경변수 (default 1) — 다종목 batch 시 cache size 증가로 parquet 재로드 회피.

### 메모리

```powershell
uv run python -X utf8 tests/audit/sectionsMemoryAudit.py --check
uv run python -X utf8 tests/audit/sectionsMemoryAudit.py --write-baseline
```

`tracemalloc` Python heap peak + `psutil` RSS growth 측정. baseline tolerance 20% 회귀 차단. 005930 측정 결과: rows=7899, pythonPeak=124.6MB, rssGrowth=0.0MB (호출 후 회수).

aggregation.py 의 gc.collect() 빈도: period 별 5 → 3 로 강화 (master `f4e52f9a5`).

nightly 게이트 `sections-loss` + `sections-memory` 양쪽 blocking=False — 정보 표시 우선, 회귀 시 별도 commit 으로 baseline 재박제.

## 12. sections SSOT 3 원칙 — 본 모듈의 정체

> 사용자 명시 (2026-05-20 ~ 21 두 세션). 본 모듈이 *왜 존재* 하는지 + *완성 기준* 의 단일 진실값.

**정체**: DART parquet 의 원본 본문을 *period × content* 의 wide-format DataFrame 으로 변환하는 **SSOT**. viewer/AI/MCP/외부 모두 본 wide-format row 를 dumb 소비.

### 원칙 1. 원본 그대로 보존
- 원본 heading hierarchy (Chapter → 가/나/다 → (1)/(2) → ...) 그대로.
- 원본 표 형식 (`| 일자 | 주소 | 비고 |`) 그대로 — transpose 금지 (transpose 는 viewer 의 책임).
- 원본 본문 순서 (가 → 나 → 다 → ... → 사) 그대로.
- 원본에 없는 heading 합성 금지.

### 원칙 2. 같은 의미 같은 row
- period 간 같은 의미 본문 = wide-format 의 row × cell 단위로 정합.
- row identity = period-invariant. `sourceBlockOrder` 같은 period-dependent 정보를 segmentKey 에 *섞지 않는다*.
- annual=표 / quarterly=disclaimer 같은 동일 의미 다른 형태도 같은 row.
- row N 개에 같은 path 의 cell 분산 = SSOT 위배.

### 원칙 3. dumb 소비
- viewer/AI/MCP/외부 = sections row 의 cell 값 *그대로* 사용.
- 추가 가공 (paragraph re-split / changeSummary / horizontalize / heading 합성) 은 sections 의 책임이 아니면 다른 layer 도 책임 아님.
- sections 가 *정규화 책임*. parquet 본문이 비일관해도 sections 가 강제 정규화.

## 13. SSOT 정공법 8 종 (2026-05-20 ~ 21 세션 적용)

원칙 2 (period-invariant row identity) 위배 다중 회귀 → 8 메커니즘 정공법:

1. **heading segmentKey 의 `lv:` prefix 제거** ([segmentKeyer.py](../../../src/dartlab/providers/dart/docs/sections/segmentKeyer.py))
   같은 path 인데 source format 차이로 level 만 다른 경우 (한글 "가." L=3 vs numeric "1." L=2) segmentKey 분기 → 다른 row. path = ancestor chain + label = 같은 heading 이므로 lv prefix 불필요.

2. **alias-redundant heading 시 descendant pop** ([textStructure.py](../../../src/dartlab/providers/dart/docs/sections/textStructure.py))
   `redundantTopicAlias` 시 직전 sub-section 의 stack entry (L=7 bracket 등) 잔존 → 후속 body textPath 오염 차단. alias entry 이후 descendant 모두 pop.

3. **body / heading / table path-anchored merge** (segmentKeyer + pipeline)
   `body|p:{path}` / `heading|p:{path}` base 는 occurrence 미부여 → 같은 path = 1 row. pivot 충돌 시 cell concat. table 은 `table|p:{path}|h:{headerHash}` (path + header) — 같은 section 안 다른 header 표는 별 row, 같은 표 (period 갱신) 는 같은 row.

4. **bracket caption period-variable strip** (textStructure `_semanticSegmentKey`)
   "기업집단에소속된회사 20171231 기준계열사 95개사" 류 caption 의 date + 회사수 strip → "기업집단에소속된회사기준계열사" 통합.

5. **heading gate 강화** (textStructure `_gateHeadingLabel`) — body fragment promotion 차단:
   - 길이 > 80 자 → reject (heading 은 명사구라 짧음)
   - 조사 prefix (`은/는/이/가/을/를/의/도/만/과/와/및/또는/이며/...`)
   - 종결 어미 (`...니다./입니다./같습니다./...`)
   - 절 conjunction (`...하여/되어/함으로/함에/되면/하면/...`)
   - conjunction adverb (`또한/그러나/그리고/이러한/다만/아울러/특히/한편/이에/그러므로/따라서`)
   - 명사형 종결사 long-label (`...분석함./평가함./관리함./...`)
   - 동사 mid-sentence (`인식하/적용하/사용하/포함하/...`)
   - 주어 marker 중간 (`[은는이가]\s+\S` — 본문 sentence 시그널)

6. **tableHeaderHash 정규화** ([tableParser.py](../../../src/dartlab/providers/dart/docs/sections/tableParser.py))
   - "제 N기 N분기" / "제 N기 반기" / "제 N기" 통합 strip
   - "2016년 상반기" / "2016년 1분기" / "2016년 하반기" — 한글 period 표현 통합 strip
   - 독립 "상반기/하반기/N분기/반기" token 추가 strip
   - 빈 괄호 `()` noise 제거
   - intro sentence row skip — 본문 sentence ("...같습니다.") 첫 row 인 경우 next row 의 header 사용

7. **pipeline cross-path table consolidation** ([pipeline.py](../../../src/dartlab/providers/dart/docs/sections/pipeline.py))
   같은 (topic, headerHash) 표가 다른 path 에 분기된 경우 1 row 통합. longest semantic path = canonical. 옛 cell 부재 period 만 짧은-path row 에서 보충. parquet 구조 variance ("주요제품서비스등 > X" vs "X") 흡수.

8. **▣/▶/◈ DART sub-section marker + inline 한글 heading split** (textStructure)
   - `▣ 현대로템` / `▶ 카테고리` — line 시작 + inline (한글 직후 line-break 누락) 모두 split + L=5 heading 인식
   - `활동가. 연구개발활동의 개요` — inline 한글 heading marker pattern (1-char Korean + `. ` + 한글) split

### 주석 단 정공법 — 의미 기반 (한글 이름) 매핑

[notesSplit.py](../../../src/dartlab/providers/dart/builder/notesSplit.py) 의 `_resolveNoteIdentity`:
- cell 첫 줄에서 `N. {한글 이름}` 추출.
- *한글 이름* normalize + alias map → 표준 (NN, slug) 매핑. 회사 N 번호 무시.
- 매칭 실패 시 회사 N 번호 fallback (`_NOTES_BY_NUMBER`).

회귀 사례:
- 005380 "30. 퇴직급여제도" → 옛 룰: `financialNotes_30_segment` (틀림 — 표준 30=부문). 새 룰: alias "퇴직급여제도" → 표준 14 `definedBenefit` → `financialNotes_14_definedBenefit`.
- 005930 "4. 공정가치금융자산" → 옛 룰: `_04_financialInstruments`. 새 룰: 한글 이름 → 표준 6 `fairValueAssets` → `financialNotes_06_fairValueAssets`.

192 topic 중 매칭률 63% → 85% (+22pp). 잔존 27 은 cell 잘림 또는 회사 자체 비표준 주석.

## 14. 회귀 가드 — 3 단계

### 단계 1. fast tier — 5 종목 sanity ([sections-parity-fast](../../../tests/run.py) gate)
```powershell
uv run python -X utf8 tests/audit/sectionsParity.py --codes 005380,005930,035720,207940,000660 --strict
```
3 검사: `fragmentHeadings` / `chapterMix` / `koreanInversion`. 모두 0 = 통과. PR 차단 blocking gate.

### 단계 2. nightly tier — 200 종목 bulk scan ([sections-parity-bulk](../../../tests/run.py) gate)
```powershell
uv run python -X utf8 tests/audit/sectionsBulkScan.py --sample 200 --seed 42 --json
```
parity FAIL 자동 식별 + row count outlier (3× IQR) + dup excess high-10 자동 출력. nightly 회귀 발견 즉시 보고.

### 단계 3. ad-hoc — 특정 종목 디버그
```powershell
uv run python -X utf8 tests/audit/sectionsBulkScan.py --codes 084690,003410,015890
```
종목별 row count + dup metric + parity 즉시 측정.

### known-defect 등록
`tests/audit/sectionsParity.py` 의 `_KNOWN_DEFECTS` dict 에 등록. 신규 누락은 fail, 등록된 누락은 pass. 예:
```python
_KNOWN_DEFECTS: dict[str, dict[str, list[str]]] = {
    "028260": {"companyOverview": ["나"]},  # 삼성물산 — parquet 본문 결손
}
```

## 15. 빠른 진단 호출 cookbook

### 전체 sections frame
```python
c = Company("005380")
df = c.sections  # wide-format DataFrame, ~6300 rows × ~72 cols
```

### topic 별 sections row 직접
```python
df.filter(pl.col("topic") == "companyOverview").sort("blockOrder")
df.filter(pl.col("topic") == "businessOverview")
df.filter(pl.col("topic") == "financialNotes_30_segment")  # 표준 30 = 부문보고
df.filter(pl.col("topic") == "financialNotes_14_definedBenefit")  # 표준 14 = 확정급여
```

### dup excess 빠른 점검
```python
g = df.group_by(["textSemanticPathKey", "blockType", "textNodeType"]).agg(pl.len().alias("n")).filter(pl.col("n") > 1)
excess = g.select(pl.col("n").sum() - pl.len()).item()
print(f"dup groups: {g.shape[0]}, excess rows: {excess}")
```

### 정규화된 주석 dict (extractor)
```python
c.show("inventory")     # 재고자산
c.show("receivables")   # 매출채권
c.show("borrowings")    # 차입금
```
extractor 기반 — sections markdown 을 *항목 × 연도* DataFrame 으로 파싱. AI/코드 분석용.

## 16. 본 모듈의 완성 기준

- [x] 30 종목 sectionsParity 100% (fast gate)
- [x] 100 종목 random sample 100% (bulk scan 2026-05-21)
- [x] 회사별 주석 번호 변동 의미 기반 매핑 (85% 정확)
- [x] CI gate 등록 (`sections-parity-fast` blocking + `sections-parity-bulk` nightly blocking)
- [x] 본 spec 의 §12 ~ §15 SSOT 박제
- [ ] 200 종목 nightly bulk scan 통과 (실측 대기)
- [ ] frontend 의 sections row dumb render 완료 검증
