# Search *(beta — AI 사용 비권장)*

> ⚠ **현재 상태**: 인덱스 신선도 부족. max date = `20260331`(2026-04-19 기준 19일 갭). 매일 증분(`rebuildContentDelta`) / 풀빌드 자동화 미완성.
> AI 도구에서는 우선 사용 비권장 — 단일 종목 공시는 `Company.disclosure` / `Company.liveFilings` 경유.
> 인프라(GitHub Actions cron + HF push) 구축 후 stable 승격 검토.

공시 검색 — DART 사이트는 유형/기업/기간 필터만 지원하고 텍스트 검색이 안 된다. dartlab은 scope 분리로 두 종류 검색을 지원한다.

- `scope="title"` (기본): report_nm + section_title ngram 검색. 제목형 쿼리 전용 ("유상증자", "대표이사 변경").
- `scope="content"`: section_content 본문 BM25 검색. 개념/내용형 쿼리 전용 ("반도체 HBM 투자", "환율 변동 리스크").

두 엔진은 독립. 가중치 합산 없음 — 실험 116에서 합산 방식은 품질 저하 확인됨.

## 호출 계약

```python
import dartlab
# 제목형 검색 (기본) — ngram, 95% precision
dartlab.search("유상증자")
dartlab.search("대표이사 변경", corp="005930")

# 본문형 검색 — BM25, 개념 매칭
dartlab.search("반도체 HBM 투자", scope="content")
dartlab.search("환율 변동 리스크", scope="content")

# 종목 찾기
dartlab.searchName("삼성")
```

## 노트북

[![marimo](https://marimo.io/shield.svg)](https://marimo.app/github.com/eddmpython/dartlab/blob/master/notebooks/marimo/10_search.py)
[![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/eddmpython/dartlab/blob/master/notebooks/colab/10_search.ipynb)

---

> **search vs listing**: search는 "내용 안에서 찾기"(원문 역인덱스 매칭). 카탈로그성 "뭐가 있는지"(종목/공시메타/토픽) 조회는 `dartlab.listing()` → src/dartlab/gather/LISTING.md.

| 항목 | 내용 |
|------|------|
| 레이어 | L0 (core/search/) |
| 진입점 | `dartlab.search()` |
| 소비 | allFilings(수시공시) + docs(사업보고서) |
| 생산 | 검색 결과 + dartUrl(공시 뷰어 링크) |
| 상태 | alpha — 데이터 범위 확장 중 |

## 구조

```
core/search/
├── __init__.py       # search(scope=...), buildIndex(), rebuildContent()
├── ngramIndex.py     # title ngram 인덱스 (기존, scope="title")
├── fieldIndex.py     # content BM25 인덱스 (실험 116, scope="content")
│                     # — main/delta 세그먼트 + word 토크나이저
├── derived.py        # 파생 집계 (보류 — 가치 미확정)
providers/dart/openapi/
├── allFilingsCollector.py  # 수시공시 2단계 수집
```

## content 인덱스 세그먼트 구조 (신규)

```
data/dart/contentIndex/
├── main.npz            # CSR (offsets/docIds/termFreqs/docLengths)
├── main_stems.json     # stem → id
├── main_meta.parquet   # rcept_no / corp_name / report_nm 등
├── main_info.json      # nDocs / avgDocLength / builtAt
├── delta.npz           # 증분 세그먼트 (동일 구조)
├── delta_stems.json
├── delta_meta.parquet
└── delta_info.json
```

병합 검색: `search(scope="content")` → `BM25(main) ∪ BM25(delta)` 후 score 정렬.
중복 시 delta 우선 (`rcept_no` + `section_order` 기준).

## search() API

```python
import dartlab

dartlab.search("유상증자 결정")                     # 공시 검색
dartlab.search("대표이사 변경", corp="005930")       # 종목 필터
dartlab.search("전환사채", start="20240101")         # 기간 필터
```

- 외부 모델/서버 불필요
- 결과에 dartUrl 포함 — DART 공시 뷰어 바로 이동
- 종목 찾기는 `dartlab.searchName("삼성전자")`

## 핵심 기술 — stem ID 역인덱스

bigram/trigram 토큰에 정수 ID를 부여하고 CSR 역인덱스로 검색.

### Stem ID

텍스트를 bigram/trigram 토큰으로 분해하고 각 토큰에 정수 ID를 부여.
DART 공시 어휘가 제한적이라 **400만 문서에서도 ~5,500 stems**.

```
"유상증자 결정" → ["유상", "상증", "증자", "자 ", " 결", "결정", "유상증", "상증자", "증자 ", ...]
각 토큰 → stemId (정수)
```

### CSR (Compressed Sparse Row)

역인덱스를 두 numpy 배열로 저장:

```
offsets[stemId] ~ offsets[stemId+1] → docIds 범위
docIds[start:end] → 해당 stem을 포함하는 문서 ID 목록
```

scipy CSR과 동일 구조, numpy만으로 동작.

### bincount 검색

매칭 docId 배열을 `np.concatenate` → `np.bincount()`로 문서별 매칭 수 집계.

### BM25F 필드 가중치 리랭킹

검색 결과를 report_nm/section_title 매칭 여부로 리랭킹한다.

```
report_nm에 쿼리 키워드 있으면 → score × 5
section_title에 있으면 → score × 2
```

효과: "대표이사 변경" 검색 시 사업보고서가 아닌 **대표이사변경 공시**가 1위.
인덱스 변경 없이 검색 후처리만으로 구현.

### content 인덱싱은 하지 않는다

실험 014에서 content[:50] 인덱싱을 시도했으나, stems 폭발(8K→260K)로 노이즈 유발.
precision 95% → 35%로 급락. content 인덱싱은 기각.

비공식 표현("사장", "횡령")은 **AI 레이어**(`dartlab.ask()`)에서 처리한다.
search는 DART 공식 용어(report_nm + section_title)만 정확 매칭하는 역할.

### TF×IDF는 사용하지 않는다

실험에서 IDF 가중치를 시도했으나, 희귀 stem 과대평가로 비공식 쿼리 precision 하락 (88%→76%).
DART 공시에서는 TF(bincount) + 필드 가중치 리랭킹으로 충분했다.

### 계층적 유형 라우팅 (실험 015)

DART 114개 정규화 유형을 L0 라우터로 사용:

```
L0: 114개 유형에서 Jaccard+Coverage로 쿼리 매칭 → 후보 유형 선택
L1: 후보 유형의 문서만 필터 → 노이즈 원천 차단
L2: 필터 내 BM25F 리랭킹
```

비공식 표현은 L0에서만 변환 (114개 대상이라 노이즈 없음):
- "M&A" → "합병 인수" → 유형 "합병등종료보고서" 매칭
- "CB 발행" → "전환사채" → 유형 "전환사채" 매칭

L0 비공식 변환은 22개 규칙 — 114개 유형에만 적용.

### 역할 분리 — search vs AI

| 역할 | 담당 | 처리 |
|------|------|------|
| DART 공식 용어 검색 | `dartlab.search()` | ngram + BM25F (88%, 124ms) |
| 비공식 → 공식 변환 | L0 유형 라우팅 (114개 대상) | "M&A"→"합병", "CB"→"전환사채" |
| 완전 자연어 이해 | `dartlab.ask()` | AI가 "사장이 바뀌었어" → search("대표이사변경") |

search 내부에서 처리 가능한 범위(유형 라우팅)와 AI가 필요한 범위(자연어 이해)를 분리한다.

### 통합 인덱스

allFilings(수시공시) + docs(사업보고서) → 단일 stemIndex.
중복은 (rcept_no, section_order)로 제거, allFilings 우선.

## 저장 구조

```
data/dart/stemIndex/
├── stemIndex.npz       # CSR 역인덱스 (offsets + docIds, int32)
├── stemDict.json       # stem → ID 매핑
└── meta.parquet        # 문서 메타 + text[:2000]

data/dart/allFilings/
├── {date}.parquet      # 수시공시 원문 (일자별)
├── {date}_meta.parquet # 목록만 (원문 미수집)
```

## 2단계 수집

```
Phase 1: collectMeta() ← 목록만 (일자당 API ~15회, 가볍다)
  → {date}_meta.parquet

Phase 2: fillContent() ← 원문 채우기 (건당 API 1회, 무겁다)
  → {date}.parquet (승격, _meta 삭제)
```

## 인덱스 빌드 파이프라인

```python
from dartlab.core.search import (
    collectMeta, fillContent,
    rebuildIndex,         # title 인덱스 (scope="title")
    rebuildContent,       # content 인덱스 main (scope="content")
    rebuildContentDelta,  # content 인덱스 delta (일 단위 증분)
    pushIndex,
)

# 1. 수시공시 수집
collectMeta("20260301", "20260330")
fillContent()

# 2. title 인덱스 (~220초, 월 1회)
rebuildIndex()

# 3. content 인덱스 main (~18분 추정, 월 1회)
rebuildContent()

# 4. 매일 증분 — content delta (수 초)
rebuildContentDelta(daysBack=30)

# 5. HF 공유
pushIndex(token="hf_xxx")
```

## 증분 전략

- **title 인덱스**: 전체 리빌드 (220초, 간단)
- **content 인덱스**: main + delta 세그먼트 분할
  - main: 월 1회 풀리빌드 (docs + 전체 allFilings, ~18분)
  - delta: 매일 증분 (최근 N일 allFilings만, 수 초)
  - 병합 검색 시 rcept_no+section_order 중복 제거 (delta 우선)

## HF 배포

```python
from dartlab.core.search import pushIndex, pullIndex

pushIndex(token="hf_xxx")  # stemIndex.npz + stemDict.json + meta.parquet 업로드
pullIndex()                 # 다운로드 → 즉시 검색
```

stemIndex.npz가 이미 압축된 numpy 형태라 별도 압축 불필요.

## 실험 105 결과

| 방법 | precision@5 | cold start | 속도 | 의존성 |
|------|:---:|:---:|:---:|------|
| **Ngram+Synonym** | **95%** | **0ms** | **1ms** | **없음** |
| Trigram 단독 | 88% | 0ms | 1ms | 없음 |
| 임베딩(ko-sroberta) | 83% | 12,700ms | 58ms | PyTorch 2GB |
| BM25(FTS) | 71% | 0ms | 14ms | 없음 |

대규모 (400만 문서):
- 인덱스 빌드: 218초 (3.6분)
- 인덱스 크기: ~320MB
- 검색 속도: 140ms (bincount)

실험 과정에서 DART 공시 유형 분류(15카테고리), Model2Vec 임베딩 등도 시도했으나 채택하지 않음.

## 왜 임베딩 없이 되는가

DART 공시는 법적 정형 문서다:
- 공시 유형(report_nm)이 257개로 고정 — "유상증자결정", "대표이사변경" 등 표준 용어
- 섹션 제목(section_title)이 반복 패턴
- 용어가 법률로 규정 — 같은 의미를 다른 단어로 표현하지 않는다

어휘가 고정되어 있으므로 ngram 정확 매칭만으로 충분하다. 임베딩의 장점인 의미 유사도 검색이 이 도메인에서는 오히려 노이즈를 만든다 (실험 105에서 확인).

비공식 표현("사장", "M&A")은 22개 변환 규칙으로 처리하고, 완전한 자연어("사장이 바뀌었어")는 AI 레이어(`dartlab.ask()`)로 위임한다.

## 파생 집계 레이어 (보류 — 가치 미확정)

`buildNgramIndex()` 시 meta.parquet에서 group_by로 추출하는 파생 데이터.
코드는 `core/search/derived.py`에 구현되어 있으나, **실제 가치가 검증되지 않아 현장 배치 보류.**

| 파생물 | 내용 | 상태 |
|--------|------|------|
| companyProfile.parquet | 기업별 공시 건수/유형/속도 | 보류 — 유형 건수만으로 인사이트 부족 |
| eventTimeline.parquet | 유형×월 빈도 시계열 | 보류 — "그래서 뭐?" 문제 |
| dna.npz | 114차원 유형 빈도 벡터 | 보류 — 행동 peer 가치 미검증 |

**보류 사유**: allFilings meta의 공시 유형 건수 집계만으로는 의미 있는 인사이트가 나오지 않는다. 진짜 가치는 공시 내용(section_content)에 있다. 전체 데이터 축적 + 실제 사용 사례에서 가치가 입증되면 배치 위치를 결정한다.

**현장 배치 완료된 것**:
- AI 시스템 프롬프트에 `dartlab.search()` 도구 설명 추가
- AI sandbox에 `disclosureSearch()` 노출
- AI prefetch에 `_preGroundDisclosure()` (companyProfile 기반 — 프로필 파일 있을 때만 동작)

## 관련 코드

| 파일 | 역할 |
|------|------|
| `src/dartlab/core/search/__init__.py` | 통합 진입점 — `search(scope="title"\|"content"\|"both")` |
| `src/dartlab/core/search/ngramIndex.py` | title 인덱스 — ngram + BM25F (scope="title") |
| `src/dartlab/core/search/fieldIndex.py` | content 인덱스 — word + BM25, main/delta 세그먼트 (scope="content") |
| `src/dartlab/core/search/derived.py` | 파생 집계 (companyProfile, eventTimeline, dna) — 보류 |
| `src/dartlab/providers/dart/openapi/allFilingsCollector.py` | 수시공시 수집기 |
| `experiments/116_fieldSeparatedBM25/STATUS.md` | scope 분리 설계 검증 기록 |
