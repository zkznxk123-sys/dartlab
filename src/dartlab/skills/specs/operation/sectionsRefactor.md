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
- DuckDB fast path skeleton (`_sectionsFastDuckdb`, ~30 줄 NotImplementedError).
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

본 리팩터링/최적화의 *완료 순서*:

1. **§4 부채 1 — pipeline.py 모듈 분리** (1834 → 7 모듈). 한 번에 PR. 외부 API 변경 0. parity test 가 가드.
2. **§4 부채 2 — chapter row dedup 단일화**. Phase 1 의 unique-block fix 가 모든 케이스 cover 하는지 확장 검증 후 Phase 4 `_dropChapterCatchAllDuplicates` 폐기. 회귀 시 parity test 가 catch.
3. **§4 부채 5 — heading stack 부모 보존**. 같은 level heading 이 형제로 들어와도 부모 정보 유지. `textStructure.py` 의 stack pop 로직 수정. notes topic textPath 깊이 1 → 2~3 으로 회복.
4. **§6 후보 B — 5 group_by 통합**. 측정 후 20%+ 개선이면 채택.
5. **§4 부채 3 — `SegmentKeyer` 추상화**. segmentKeyBase 룰을 단일 클래스로 모음. literal 문자열 분산 차단.
6. **§4 부채 4 — mapper L1.5 reference 이전**. 의존성 사이클 검토 후. 우선순위 낮음.

각 항목은 단일 commit 단위. parity test + ruff format/lint + 5 종목 baseline regen 동행.

## 8. 회귀 가드

본 리팩터링 진행 시 *항상* 같이 확인:

- `bash tests/test-lock.sh tests/providers/dart/docs/sections/ -v` — 94 test PASS.
- `bash tests/test-lock.sh tests/providers/dart/docs/test_sectionsPolarsParity.py -v` — 5 종목 baseline parquet 과 shape/dtypes/values 일치.
- 시각 검증: `sections('000660', topics=None)` 의 결과를 viewer 에서 확인. 2026Q1 placeholder 위치 (`companyOverview` blockOrder=0/1) + table textPath 부여 (`consolidatedNotes` 모든 table row null 0) + blockOrder contiguous (gap 0).

본 문서는 *부채 원장*. 항목별 진행 commit 메시지에 `sectionsRefactor.md §N` 참조하고, 완료된 항목은 본 문서에서 제거 또는 *완료 표시* 후 회귀 재발 시 reopen.
