---
id: engines.company.docsInternals
title: Company Docs Internals
category: engines
kind: curated
status: observed
purpose: Company 의 docs (사업보고서 sections) 내부 파이프라인 — fetch → parse → topic 매핑.
sourceRefs:
  - dartlab://skills/engines.company.docsInternals
knowledgeRefs:
  - engines.company
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
whenToUse:
  - Company docs 파이프라인 내부 추적
  - fetch → parse → topic 매핑
  - sections 디버깅
---

## 엔진 역할

`docsInternals` 는 `engines.company.sections` 의 내부 구현 SSOT. 외부 사용자 API 는 `c.sections` / `c.show()` 가 모두지만, 그 내부에서 일어나는 row identity 결정 · 테이블 수평화 알고리즘 · Rust 포팅 로드맵을 본 spec 이 보관.

본 spec 의 청중 — dartlab 코어 컨트리뷰터 + sections pipeline R&D 진행자.

### 데이터 손실 정책 (의도 drop + 잠재 손실 가시화)

`c.sections` 는 원본 `docs.parquet` 의 *모든* row 를 보존하지 않는다. 의도된 drop 5 종:

1. **chapter 결정 전 prelude row** — `parseMajorNum` 미인식 + 첫 chapter 헤딩 등장 전 sub-section row drop (`reportRows.py:1067-1072`).
2. **chapter row catch-all dedup** — sub-section 에 cover 된 chapter row block drop. 8자 미만 line 만 있는 block 은 unique 후보에서 제외 (`reportRows.py:1023`).
3. **projection-suppressed sourceTopic** — chapter II 합산 topic 이 `applyProjections` 로 분배된 후 원본 sourceTopic row drop (`aggregation.py` line ~95).
4. **detailTopic suppression** — `detailTopicForTopic(topic) is not None` 매치 row drop — 이미 detail 분류된 row 가 본체에서 제거 (`aggregation.py` line ~97).
5. **정정공시 silent drop** — `providers/reportSelector.py::selectReport` 가 원본 우선 / 정정공시만 있을 때 최신 type 1 건 선택. 정정 전 본문 비교는 sections layer 에선 불가능 (logger.info 한 줄로 관찰 가능).

본 정책의 정량 관찰치 (5 종목 baseline 박제 전 005930 단일): byte 보존율 **0.511**. 즉 원본 byte 의 ~49% 가 의도 drop 으로 빠짐.

**잠재 손실 3 종** (silent → 측정 가능):

- **pivot last-wins 충돌** — `aggregation.py` pivot 직전 `(topic, segmentKey, periodKey)` 중복 카운터 logger.warning. `DARTLAB_SECTIONS_STRICT=1` → ValueError 승격.
- **chapter dedup 8자 임계** — `reportRows.py:1023` 의 `len(ln) >= 8` 임계. 짧은 row 만 있는 chapter-only 표 손실 가능.
- **정정공시 silent drop** — 위 (5) 와 동일 — `logger.info` 한 줄.

회귀 가드:
- `tests/audit/sectionsLossAccount.py` — round-trip 회계 (byte/line/row 보존율 baseline tolerance 0.02).
- `tests/audit/sectionsMemoryAudit.py` — Python heap peak + RSS growth baseline tolerance 20%.
- `tests/providers/dart/docs/test_sectionsInvariants.py` — invariant 3 (pivot 충돌 0, 8자 임계, selectReport 정책).

상세: `operation.sectionsRefactor §9-11`.

## 공개 호출 방식

내부 helper 는 `RunPython` 으로 직접 호출 가능:

```python
import dartlab
from dartlab.providers.dart.docs.sections import pipeline

c = dartlab.Company("005930")
df = c.sections

# structure 진단 (5 종)
reg = pipeline.structureRegistry(df, topic="businessOverview")
col = pipeline.structureCollisions(df, topic="businessOverview", nodeType="body")
evt = pipeline.structureEvents(df, topic="businessOverview", nodeType="body")
sum_ = pipeline.structureSummary(df, topic="businessOverview")
chg = pipeline.structureChanges(df, topic="businessOverview", latestOnly=True)

# semantic spine 진단 (2 종)
sreg = pipeline.semanticRegistry(df, topic="mdna")
scol = pipeline.semanticCollisions(df, topic="mdna")

# freq projection (annual / quarterly / mixed)
ann = pipeline.projectFreqRows(df, freqScope="annual", includeMixed=True)
```

## 호출 동작

### 1. sections row identity

핵심 4 가지:
- `textPathKey + occurrence` — 논리 row identity (raw block 위치보다 우선).
- `sourceBlockOrder` — 원래 큰 블록 경계 보존용.
- `@topic:{topic}` root — 같은 topic 가리키는 top-level heading alias 묶기.
- `textSemanticPathKey` — 안전한 wording drift 흡수, raw `textPathKey` 덮어쓰지 않는 병렬 의미 구조선.

row 메타 해석:
- `freqScope=annual` — 연간 row
- `freqScope=quarterly` — 분기 전용 row
- `freqScope=mixed` — 연간 / 분기 공용 row
- `latestAnnualPeriod` · `latestQuarterlyPeriod` — 각 freq 의 마지막 실존 period

운영 구조 4 파일:
- `mapper.py` — title normalization · `sectionMappings.json` lookup
- `extractors.py` — topic → subtopic DataFrame 재구성
- `pipeline.py` — raw markdown 기반 horizontalization
- `runtime.py` — projection · semantic / detail topic 보조

### 2. structure event 진단

`structureEvents(df, nodeType="body")` — comparable spine 기준 period 전이 event row. `periodLane` 기준 같은 report-kind 끼리만 비교 (annual / q1 / q2 / q3). 교차 주기 (`Q3 → annual`) 는 구조 event 로 간주하지 않는다.

`eventType` 값:
- `variant` — 같은 slot, wording 차이
- `moved` — slot 이동
- `reassigned` — parent 변경
- `split` — 1 → N
- `merge` — N → 1
- `parallel_change` — 동시 다발 변형

`structurePattern` 값 (registry 결과):
- `same` · `variant` · `moved` · `reassigned` · `split` · `merge` · `split_merge` · `parallel`

### 3. textComparablePathKey vs textSemanticPathKey

- `textPathKey` — raw 위치
- `textSemanticPathKey` — wording drift 흡수 (보수적 검증된 alias 만)
- `textComparablePathKey` — 구조 슬롯 비교용 (businessOverview 부문명 변경, 판매경로 세부 slot 같이 raw semantic leaf 가 바뀌어도 같은 비교 슬롯)

### 4. 텍스트 품질 향상 3 층

`sectionMappings.json` 하나만으로 안 된다. 3 층:

1. **section title mapper** — `section_title → topic` 정규화 (현 `mapper.py` + `sectionMappings.json`)
2. **text structure mapper** — body 내부 `가.`, `1.`, `(1)`, `①` 같은 소제목 레벨 복원 (`headingPath`, `segmentOrder`, `level` 구조 메타 생성)
3. **segment matcher** — 기간 간 같은 텍스트 segment 정렬, 추가/삭제/이동 보수 판정

viewer 는 이 구조의 *소비자*. viewer 안에서 소제목/문단을 다시 추정하는 로직은 임시 보정으로만.

### 5. 다종목 검증 (2026-03-18)

검증 종목 — `005930` · `000660` · `035720` · `035420` · `373220` · `068270`.
대표 topic — `companyOverview` · `businessOverview` · `mdna`.

세 평가:
- `companyOverview` · `mdna` — safe alias 가 실제 row merge 로 이어진다.
- `businessOverview` — semantic rename 많지만 대다수 회사에서 row count 거의 안 줄어든다. 병목은 wording drift 가 아닌 **부문 이동 / 구조 이동**.
- 그래서 semantic alias 위에 comparable slot spine + `structurePattern` 진단 병행.
- 최신 연간 sparse 의 큰 원인 하나는 raw source 가 아닌 chapter content drop. 장 제목 content 보존 후 `005930` 최신 annual `businessOverview` coverage `177 / 436 (40.6%)` 회복.

안전 alias 예:
- `연결대상 종속기업/종속회사 개황 → 연결대상 종속사 현황`
- `조직개편 / 조직의 변경 → 조직변경`
- `유동성 및 자금조달과 지출 → 유동성 및 자금조달`
- `감사위원회에 관한 사항 → 감사위원회`
- `...에 관한 사항 → slot name` 계열의 좁은 정규화

금지 merge 예:
- `DX부문`, `CE부문`, `DS부문` — 부문명 자동 merge 금지
- 법인명 suffix 차이 (`PTE` vs `PTE. LTD`) — heading alias 아닌 별도 법인명 정규화 레이어 필요
- `산업의 특성`, `시장여건`, `경쟁환경` — 형제 slot, alias 아님

### 6. 테이블 수평화 (table horizontalization)

현재 상태 (2026-03-18):
- 실제 `show()` 기준 — **수평화 62.9%**, 원본 fallback 37.0%, 데이터 반환률 99.9%
- sections pipeline 은 안 건드림 — Company 의 `show()` 레이어에서만 처리
- 위치 — `company.py::_horizontalizeTableBlock()`

적용된 개선 7 가지:
1. **헤더 시그니처 그룹핑** — `_groupHeader()` 로 기간별 다른 구조 분리
2. **matrix multi-column 분리** — `vals ≤ headerNames` 일 때 `항목_헤더명` 분리
3. **sparse 감지** — 항목 > 15 · `fillRate < 0.5` → 원본 fallback
4. **수평화 실패 시 원본 텍스트 fallback**
5. **주석번호 정규화** — `(*)`, `(*1)`, `(*1,2)` → 제거 (75 건 통합, 오탐 0)
6. **1 block topic 자동 반환** — `show("IS")` → 바로 DataFrame
7. **pure_kisu 차단 제거**

실험 / 기각 9 가지:

| 접근 | 결과 | 판정 |
|------|------|------|
| fuzzy matching (RapidFuzz) | 사내이사 ≈ 사외이사 89% 오탐 | 기각 |
| suffix 분리 fuzzy | 전전기 ≈ 전기 80% 오탐 | 기각 |
| 괄호 기반 통합 | 813 건 중 오탐 208 건 (25.6%) | 기각 |
| 임계값 완화 (Jaccard 0.15, 목록 100) | +7.6%p 이지만 엉망 수평화 증가 | 기각 |
| 임베딩 (ko-sroberta) | threshold 분리 불가, 속도 38 분 | 기각 |
| 값 교차 검증 | DART 항목명 불일치 0 건, 전제 틀림 | 기각 |
| 정규형 단독 | 기존보다 -6.6%p | 기각 |
| Valentine | 행 매칭 불가, 기수 오매칭 | 기각 |
| datamatch | 런타임 에러, 유지보수 중단 | 기각 |
| py_stringmatching | 설치 실패 (Visual Studio 필요) | 기각 |
| ML 분류기 (RandomForest) | +17%p 이나 실패 recall 낮음 | 규칙 3 개만 추출 |

**핵심 교훈** — 외부 도구 / 통계적 유사도보다 **dartlab 정규화 (94%) 가 JaroWinkler (75%) 보다 정확**. DART 항목 매칭은 한국어 정규화 + 도메인 지식이 핵심.

### 7. Canonical Schema 실험 결과

**아이디어** — 기간별 독립 파싱 → 전 기간 동시 스캔.

```
사전계산 (Company 초기화 시 1회):
  전 기간 테이블 동시 스캔 →
  1. canonical header (가장 많은 기간 등장 헤더)
  2. canonical items (전 기간 항목 합집합)
  3. synonym map (같은 위치 표기 변형 자동 통합)
  4. tableCategory (이력형/목록형 전 기간 통계 확정)
  → CanonicalSchema 캐시

show() 호출:
  스키마 로드 → 확정된 구조로 파싱 → synonym map 으로 정규화
```

검증 — 삼성전자 1 종목 **51.7% → 73.0% (+21.3%p)**. 283 종목 전수 — **34.1% (기존 58.4% 보다 못함)**.

```
스키마 성공:    43,723 (34.1%)
기존 성공:       74,832 (58.4%)
기존만 성공:     39,972 건
스키마만 성공:    8,863 건 (대부분 null 채움, 품질 나쁨)
```

**결론** — 1 종목 PoC 가 과대평가. 283 종목 전수에서 -24.3%p. 흡수 불가.

### 8. 보조 개선

- **구조 분해 매칭** (F1 95%, 오탐 0) — core + qualifier + annotation 분리
- **셀 핑거프린트** (99.1% 구조 판별) — `_groupHeader` 보조 지표
- **ML 발견 규칙 3 개** — `avgDateRatio > 0.28` 등 이력형 조기 감지

### 9. 중기 연구 후보

- **Magneto 식 SLM + LLM 2 단계** — 기존 매퍼 34,000 개 학습 데이터 활용
- **STARMIE / Watchog 컬럼 임베딩** — 테이블 간 unionable 컬럼 자동 탐색
- DART 테이블 수평화 연구는 세계적으로 없음 — dartlab 이 최초

## 대표 반환 형태

### structureSummary

```text
topic / textComparablePathKey
  latestPeriod : str           # 마지막 실존 period
  latestPeriodLane : str       # annual | q1 | q2 | q3
  latestPathCount : int        # 최신 경로 수
  eventCount : int             # 누적 event 수
  latestEventType : str        # variant | moved | split | merge | parallel
  latestEventFromPeriod : str
  latestEventToPeriod : str
```

### structureChanges

```text
+ structureSummary 컬럼
  anchorPeriod : str           # latest 변화 기준 period
  anchorPeriodLane : str
  isLatest : bool
  isStale : bool
```

기본 `latestOnly=True` · `changedOnly=True` — `eventCount > 0` 인 recent event 만.

## Rust 포팅 로드맵

### 실측 프로파일 (2026-03-20, 삼성전자)

| 구간 | 시간 | 비율 | Rust 대상 |
|------|------|------|----------|
| DataFrame 조립 (dict 누적 → `pl.DataFrame`) | 1,468ms | 50.6% | Phase 3 |
| `_expandStructuredRows` (textStructure 파싱) | 714ms | 24.6% | Phase 2 |
| `_reportRowsToTopicRows` (상태 머신) | 576ms | 19.8% | Phase 2 |
| ├─ `_splitContentBlocks` 단독 | 318ms | 11.0% | Phase 1 |
| `iterPeriodSubsets` (selectReport) | 220ms | 7.6% | 비대상 |
| `loadData` (parquet I/O) | 145ms | 5.0% | 비대상 |
| `mapSectionTitle` 체인 | 3.7ms | 0.1% | Phase 1 (합성용) |

다종목 — 2.4~3.2 초 / 종목 (행 6,851~13,967 × 컬럼 63~70).

### 포팅 원칙

1. **변하지 않는 것만 Rust 로 굳힌다** — 스키마 진화 중인 메타는 Python 유지
2. **bottom-up** — 잎 함수 → 합성 → 파이프라인
3. **Python fallback 유지** — Rust 빌드 실패 시 자동 대체
4. **테스트 동일성** — Python 구현과 byte-identical

### Phase 1 — 잎 함수 (순수 문자열)

8 개 leaf:

1. `_splitContentBlocks(content)` → `Vec<(String, String)>` (`text` | `table`). 위치 `pipeline.py:196-241` · 318ms · 안정.
2. `_detect_heading(line)` → `Option<(u8, String, bool)>`. 위치 `textStructure.py:149-193` · 안정. 매칭 우선순위 — `[]` / `【】` (level 1, temporal marker 면 structural=false) → `I. II. III.` (level 1) → `1. 2. 3.` (level 1) → `가. 나.` (level 2) → `(1) (2)` (level 3) → `(가) (나)` (level 4) → `① ② ③` (level 4) → 짧은 괄호 ≤ 48 자 (level 3). 제외 — 빈 줄, `|` 시작, 120 자 초과, noise (`단위`/`주1`/`참고`/`출처`/`비고`).
3. `_normalize_heading_text(text)` → `String`. `textStructure.py:77-86`. 6 단계 — `stripSectionPrefix` / `[] 【】` 제거 / 짧은 괄호 내부만 / `ㆍ → ·` / 공백 단일화 / 후행 구두점 (`-–—:：;,`) 제거.
4. `_heading_key(text)` → `String`. `textStructure.py:90-94`. `_normalize_heading_text` + `· ㆍ` 제거 + 비단어 (`[^0-9A-Za-z가-힣]`) 제거.
5. `normalizeSectionTitle(title)` → `String`. `mapper.py:96-105` · **99.95% 매핑률**. 7 단계 — `stripSectionPrefix` / 업종 접두사 (`(금융업)`) 제거 / 재 strip / 로마숫자 제거 / `ㆍ · → ,` / 공백 단일화 / 후행 구두점 제거.
6. `mapSectionTitle(title)` → `String`. `mapper.py:120-128`. 1) `normalizeSectionTitle` → 2) `sectionMappings.json` HashMap (182 매핑) → 3) `_PATTERN_MAPPINGS` 85 regex 순차 매칭 → 4) 첫 매칭 / fallback normalized.
7. `parseMajorNum(title)` → `Option<u8>`. `chunker.py`. 로마숫자 `I. II. ... XII.` → `1~12` / None.
8. `_semantic_segment_key(labelKey, topic)` → `String`. `textStructure.py:112-130`. `@` prefix 반환 / topic alias dict (`_TOPIC_SEGMENT_ALIASES`) / `에관한사항` 접미사 제거 / `종속기업` · `종속회사 → 종속사` / topic별 변형 (`businessOverview` `영업의개황 → 영업현황`, `mdna` `환율변동영향 → 환율변동`).

### Phase 2 — 합성 함수

3 개:

1. **`parseTextStructureWithState(text, sourceBlockOrder, topic, initialHeadings)`** — `textStructure.py:196-315`. 상태 머신: `stack: [{level, label, key, semanticKey}, ...]` + `bodyLines: 현재 body 버퍼` + `segmentOrder: 카운터`. 줄 순회 — 빈 줄 → body 버퍼 / `_detect_heading` 성공 → `flush_body()` + heading node + structural 이면 stack pop/push / 아니면 node 만 / heading 아님 → body 버퍼 / 마지막 `flush_body()`. 의존 — Phase 1 의 1-2 / 1-3 / 1-4 / 1-6 / 1-8.

2. **`_reportRowsToTopicRows(subset, contentCol)`** — `pipeline.py:244-338` · 576ms. 상태 머신 — `currentMajorNum` / `pendingChapter` / `topicBlockCounts: (chapter, topic) → 다음 blockOrder`. 행 순회 — `parseMajorNum` 성공 → 이전 pending flush + 새 pending / 일반 행 → `_registerContent` 호출 (chapter 결정 → topic 결정 → `_splitContentBlocks` → emit).

3. **`_expandStructuredRows(rows)`** — `pipeline.py:341-460`. projection 있으면 `(majorNum, orderSeq, sourceBlockOrder)` 정렬 → 각 row table / text 분기 → text 면 `parseTextStructureWithState` 후 nodes 개별 row 확장 → 마지막 occurrence 카운팅 (`(topic, segmentKeyBase)` 기준 `segmentKey = "{base}|occ:{N}"`).

### Phase 3 — DataFrame 조립

현재 1,468ms (50.6%). Python dict 누적 패턴 — `topicMap` / `rowOrder` / `rowMeta` / 5 개 더. 최종 `pipeline.py:1588-1673`.

Rust 대안 — 전체 루프 Rust 에서 + Arrow RecordBatch 반환 (`pyo3-polars`).

### 정적 데이터 (Rust 임베드)

| 데이터 | 크기 | 로딩 |
|--------|------|------|
| `sectionMappings.json` | 182 매핑 | 빌드 타임 `include_str!` 또는 런타임 1 회 |
| `_PATTERN_MAPPINGS` | 85 regex | `lazy_static!` 컴파일 |
| `_TOPIC_SEGMENT_ALIASES` | 4 topic × 5~15 | `phf::Map` 또는 HashMap |
| `_BUSINESS_OVERVIEW_COMPARABLE_ROOTS` | 6 | HashMap |
| `_STRUCTURE_SLOT_ALIASES` | 2 topic × 3~15 | HashMap |
| `REPORT_KINDS` | 4 튜플 | `const` |

### Rust crate 구조 (제안)

```
dartlab-core/
├── Cargo.toml
│   pyo3 = "0.22" (features=["extension-module"])
│   polars = "0.45" (features=["lazy"])
│   pyo3-polars = "0.18"
│   regex = "1"
│   serde_json = "1"
│   once_cell = "1"
│   blake2 = "0.10"
│
├── src/
│   ├── lib.rs           # PyO3 모듈 진입점
│   ├── content.rs       # _splitContentBlocks
│   ├── heading.rs       # _detect_heading + _normalize + _heading_key
│   ├── mapper.rs        # SectionMapper
│   ├── structure.rs     # parseTextStructureWithState
│   ├── chunker.rs       # parseMajorNum
│   ├── topic_rows.rs    # _reportRowsToTopicRows
│   ├── expand.rs        # _expandStructuredRows
│   ├── assembly.rs      # build_sections_dataframe (Phase 3)
│   └── data/
│       └── sectionMappings.json
│
└── tests/
    ├── test_content.rs · test_heading.rs · test_mapper.rs · test_structure.rs
```

### 검증 전략

1. **Golden test** — Python 5 종목 (`005930`/`005380`/`035720`/`000660`/`051910`) 함수 입출력 JSON 덤프 → Rust 출력 byte-identical 비교.
2. **벤치마크** — Python vs Rust 동일 입력 wall-clock (`criterion.rs`).
3. **회귀 방지** — Rust 빌드 실패 시 Python fallback 자동 전환.

```python
try:
    from dartlab_core import split_content_blocks
except ImportError:
    from dartlab.providers.dart.docs.sections.pipeline import (
        _splitContentBlocks as split_content_blocks,
    )
```

### 예상 효과

| Phase | 대상 | Python | Rust 예상 | 배수 |
|-------|------|--------|----------|------|
| 1 | `_splitContentBlocks` | 318ms | ~10ms | 30 x |
| 1 | heading 감지 체인 | ~50ms | ~2ms | 25 x |
| 2 | `parseTextStructureWithState` | ~650ms | ~30ms | 20 x |
| 2 | `_reportRowsToTopicRows` | ~250ms* | ~15ms | 17 x |
| 3 | DataFrame 조립 | 1,468ms | ~50ms | 29 x |
| **합계** | | **~2,750ms** | **~110ms** | **~25 x** |

*`_splitContentBlocks` 제외 나머지.

종목당 **3 초 → 0.1 초** 목표.

## production 정책 (sections 우선 topic)

`Company.show()` 가 sections extractor 먼저 탄다. sections 에서 안정적으로 재구성 안 되는 topic 만 legacy parser 유지. `show()` 는 sections 결과 우선, legacy 는 fallback.

현재 전회사 (283) 기준 failure 0:
- `salesOrder` · `riskDerivative` · `segments` · `rawMaterial` · `costByNature`
- `tangibleAsset` — legacy 유지 기준으로 검증 완료

사용자 진입점 — `c.show("sections")` (raw DataFrame). `c.docs` public namespace 는 Plan v10 에서 제거됨.

분석 메서드는 내부 `_DocsAccessor` (`c._docs`) 또는 `SectionsAnalyzer` (`c._analyzer`) 가 보유:
- `c._docs.sectionsOrdered()` · `c._docs.sectionsCoverage()` · `c._docs.sectionsFreq(...)` · `c._docs.sectionsSemanticRegistry()` · `c._docs.sectionsSemanticCollisions()` · `c._docs.sectionsStructureRegistry()` · `c._docs.sectionsStructureCollisions()` · `c._docs.sectionsStructureEvents()` · `c._docs.sectionsStructureSummary()` · `c._docs.sectionsStructureChanges()` — 모두 내부 호출 (사용자 노출 X).
- `periods()` / `ordered()` / `coverage()` — 최신우선 + 연간 `Q4` alias projection.

`show()` · `diff()` · viewer · AI 가 같은 text structure 를 공유한다.

## 변경 이력

- 2026-03-18 — sections row identity / structure event 진단 / 다종목 검증 정착
- 2026-03-20 — Rust 포팅 실측 프로파일 + Phase 1~3 인터페이스 확정
- 2026-05-12 — `providers/dart/docs/dev/{sections,tableMatching,rust-porting}.md` → 본 sub-spec 통합 (Skill OS 운영 SSOT 승격)

## 기본 검증

- 호출 결과는 `tableRef` · `valueRef` · `dateRef` · `executionRef` 로 ref 남긴다.
- 데이터 갱신 시점 (캐시 TTL · 자동 수집 cron) 명시.
- 스킬과 실제 공개 API 의 호출 방식·반환 형태·오류/제한 동작이 다르면 같은 변경에서 스킬을 갱신한다.

