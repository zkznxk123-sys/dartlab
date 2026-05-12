---
id: engines.gather.listing
title: listing — 카탈로그 단일 진입점 (companies · filings · topics · dartlist)
kind: curated
scope: builtin
status: observed
category: engines
purpose: listing 은 "뭐가 있는지" 카탈로그 조회 단일 진입점이다. KRX 전 종목 · DART 비상장 포함 115,963 법인 · 종목별 공시 메타 · 토픽 목록을 하나의 `dartlab.listing(kind)` 함수로 통합. "내용 안에서 찾는다" 는 별도 엔진 `dartlab.search()` 사용. 트리거 — 'listing', '상장사', 'DART 법인', '공시 목록', '카탈로그'.
whenToUse:
  - 전 종목 목록
  - DART 비상장 포함 법인 조회
  - 특정 종목 공시 목록
  - 토픽 카탈로그
  - 카탈로그 탐색 (search 아닌)
inputs:
  - kind (companies / dartlist / filings / topics) + 한글 alias
  - corp (filings / topics 시 필수, 종목코드 또는 ticker)
  - market (companies 시 KR / US 선택)
outputs:
  - Polars DataFrame
  - 통일 컬럼 (id / date / period / reportType / url)
  - DART / EDGAR 원본 컬럼 보존
capabilityRefs:
  - Company.filings
  - Company.topicSummaries
  - Company.listing
toolRefs:
  - RunPython
knowledgeRefs:
  - engines.search
  - engines.gather
sourceRefs:
  - dartlab://skills/engines.gather.listing
requiredEvidence:
  - kind
  - corp
  - market
expectedOutputs:
  - 전 종목 DataFrame (KR KRX 또는 US EDGAR)
  - DART 비상장 포함 115,963 법인 (corp_code 8자리)
  - 종목별 공시 메타 (DART/EDGAR 통일 컬럼)
  - 토픽 목록 (topic + summary)
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
    status: limited
failureModes:
  - search 와 혼동 (listing 은 메타만, 본문 검색은 dartlab.search)
  - filings kind 호출 시 corp 인자 누락
  - 미지원 kind 호출 (ValueError "unknown kind")
  - dartlist 호출 시 DART API 키 필요 가정 (실제는 HF 프리빌드)
forbidden:
  - listing 으로 본문 검색 시도 (engines.search 사용)
  - filings 결과 컬럼 정규화 무시 (id/date/period/reportType/url 통일)
  - corpCode.py 직접 호출 (사용자 조회는 dartlist 경유)
examples:
  - dartlab.listing() → KRX 전 종목
  - dartlab.listing("dartlist") → DART 115,963 법인
  - dartlab.listing("filings", corp="005930") → DART 공시 메타
  - dartlab.listing("filings", corp="AAPL") → EDGAR 공시 메타 자동 분기
  - dartlab.listing("topics", corp="005930") → 토픽 목록
procedure:
  - 1 단계 — kind 결정 (companies / dartlist / filings / topics).
  - 2 단계 — dartlab.listing(kind, corp=...) 호출.
  - 3 단계 — 결과 DataFrame 의 통일 컬럼 (id · date · period · reportType · url) 활용.
  - 4 단계 — 본문 검색 필요 시 dartlab.search() 로 전환.
linkedSkills:
  - engines.search
  - engines.gather
  - engines.company
source:
  type: manual_skill
  format: markdown
lastUpdated: '2026-05-12'
---

## 엔진 역할

목록 조회 단일 진입점. "뭐가 있는지 본다" 는 모든 카탈로그성 API 를 한 함수의 `kind` 인자로 통합. "내용 안에서 찾는다" 는 별도 엔진 `dartlab.search()` 를 사용.

| 항목 | 내용 |
|------|------|
| 레이어 | 루트 facade |
| 진입점 | `dartlab.listing(kind, ...)` |
| 소비 | `gather/listing` (KRX · DART CORPCODE) · `providers/{dart,edgar}` (filings · topicSummaries) |
| 생산 | Polars DataFrame — 사용자/AI 가 카탈로그 탐색에 사용 |
| 원칙 | search 는 건드리지 않는다 (원문 역인덱스 엔진은 별개) |

## 공개 호출 방식

```python
import dartlab

# 기본 — KRX 전 종목 (기존 호환)
dartlab.listing()
dartlab.listing("companies")

# DART 비상장 포함 법인 (115,963)
dartlab.listing("dartlist")

# 종목별 공시 메타 (DART / EDGAR 자동 분기)
dartlab.listing("filings", corp="005930")
dartlab.listing("filings", corp="AAPL")

# 토픽 목록 (topic + summary 두 컬럼)
dartlab.listing("topics", corp="005930")

# 시장 명시
dartlab.listing(market="US")
```

한글 alias — `"기업"` · `"공시"` · `"토픽"` · `"법인"` · `"dart"`.

## 호출 동작

### listing vs search

- **listing** — "뭐가 있는지" 종목/공시메타/토픽 카탈로그 조회. 빠르다, 항상 동작.
- **search** — "내용 안에서 찾기" stem ID 역인덱스 기반 원문 매칭. 데이터 필요.

`listing("filings", corp=...)` 는 공시 **메타 목록**만 반환. 본문 검색은 `dartlab.search()`.

### kind 목록

| kind | 라우팅 | 필수 인자 | 비고 |
|------|--------|----------|------|
| `companies` (기본) | `gather.listing.getKindList` / `EdgarCompany.listing` | `market` (optional) | **기존 `dartlab.listing()` 100% 호환** |
| `dartlist` | `gather.listing.getDartList` | — | OpenDART CORPCODE.xml. 비상장 포함 115,963 법인. corp_code 8자리 |
| `filings` | `Company(corp).filings()` | `corp` | DART / EDGAR canHandle 자동 분기 + 컬럼 정규화 |
| `topics` | `Company(corp).topicSummaries()` → DataFrame | `corp` | dict → (topic · summary) 두 컬럼 |

미지원 kind — `ValueError("unknown kind: ... — supported: companies, filings, topics, dartlist")`.

### filings 반환 컬럼 통일

DART / EDGAR `filings()` 컬럼명이 다르다. listing facade 가 공통 컬럼을 앞쪽에 배치하고, 원본 컬럼은 뒤에 보존 (드롭하지 않음).

| 통일 컬럼 | DART 원본 | EDGAR 원본 |
|----------|----------|-----------|
| `id` | `rceptNo` | `accession_no` |
| `date` | `rceptDate` | `filed_date` |
| `period` | `year` | `period_key` |
| `reportType` | `reportType` | `form_type` |
| `url` | `dartUrl` | SEC URL 동적 생성 (`https://www.sec.gov/Archives/edgar/data/{cik}/{acc-no-clean}/{acc-no}-index.htm`) |

DART / EDGAR 양쪽에서 `df["url"][0]` 으로 바로 공시 뷰어 접근 가능.

### 설계 원칙

1. **search 는 건드리지 않는다** — stem ID 역인덱스 기반 독립 엔진. 성격이 다름.
2. **레이어 위반 없음** — `gather/listing.py` (KRX 매퍼) 그대로. 루트 facade 가 라우터.
3. **기존 진입점 유지** — `c.filings()` · `c.topicSummaries()` deprecated 처리 안 함. listing 이 그들을 호출하는 얇은 facade.
4. **반환 계약 통일** — 모든 kind 가 Polars DataFrame.

### dartlist 데이터 파이프라인

OpenDART CORPCODE.xml → parquet 변환. GitHub Actions 에서 kindList 와 함께 매일 자동 수집.

**자동화**:
- 워크플로 — `.github/workflows/kindlist.yml` (kindList + dartList 동시 수집)
- 스크립트 — `.github/scripts/updateDartList.py` (CORPCODE.xml ZIP → parquet 독립 실행)
- 스케줄 — 매일 UTC 00:00 (KST 09:00)
- 저장 — GitHub Release (`kindlist-latest`) + HuggingFace (`metadata/dartList.parquet`)
- 변경 감지 — SHA256 해시 비교, 변경 없으면 업로드 스킵

**사용자 로드 경로** — 캐시 우선순위: 메모리 → 파일 (`data/dartList/dartList.parquet`, 24h TTL) → HuggingFace 자동 다운로드. DART API 키 불필요 (HF 에서 프리빌드 parquet 을 가져온다).

**dartlist vs corpCode.py**:

|  | dartlist (`getDartList`) | corpCode.py (`loadCorpCodes`) |
|---|---|---|
| 데이터 소스 | HuggingFace (프리빌드) | OpenDART API (직접) |
| API 키 | 불필요 | `DART_API_KEY` 필수 |
| 용도 | 사용자 조회 (`dartlab.listing("dartlist")`) | 내부 API 호출 (8자리 corp_code 변환) |
| 갱신 | GitHub Actions 매일 자동 | 사용자 세션 24h 캐시 |

## 대표 반환 형태

```text
listing("companies", market="KR")
→ Polars DataFrame
   종목코드 : str (6 자리)
   종목명 : str
   시장구분 : str (KOSPI / KOSDAQ / KONEX)
   ...

listing("dartlist")
→ Polars DataFrame
   corp_code : str (8 자리)
   corp_name : str
   stock_code : str (상장사면 6 자리, 비상장이면 빈 문자열)
   modify_date : str (YYYYMMDD)

listing("filings", corp="005930")
→ Polars DataFrame
   id : str (rceptNo)         # 통일 컬럼
   date : str (rceptDate)
   period : str (year)
   reportType : str
   url : str (dartUrl)
   rceptNo · rceptDate · year ...  # 원본 컬럼 보존

listing("filings", corp="AAPL")
→ Polars DataFrame
   id : str (accession_no)    # 통일 컬럼
   date : str (filed_date)
   period : str (period_key)
   reportType : str (form_type)
   url : str (SEC URL)
   accession_no · filed_date · form_type ...

listing("topics", corp="005930")
→ Polars DataFrame
   topic : str
   summary : str
```

## 향후 (v2 후보)

- `kind="signals"` — 공시 키워드 트렌드. scan 에 signal 축이 구현되면 라우팅.
- `kind="reports"` — review publisher 가 발간한 보고서 목록.
- CLI 서브커맨드 `dartlab listing <kind>`.

## 관련 코드

| 파일 | 역할 |
|------|------|
| `src/dartlab/listing.py` | 루트 라우터 facade |
| `src/dartlab/__init__.py` | export (`from dartlab.listing import listing`) |
| `src/dartlab/gather/listing.py` | KRX/KIND 매퍼 + `getDartList` (companies / dartlist 데이터 소스) |
| `src/dartlab/providers/dart/company.py` | `_filings()` — DART 공시 메타 |
| `src/dartlab/providers/edgar/_docs_accessor.py` | `filings()` — EDGAR 공시 메타 |
| `.github/scripts/updateDartList.py` | CORPCODE.xml → parquet (GitHub Actions 독립 스크립트) |
| `.github/workflows/kindlist.yml` | kindList + dartList 매일 자동 수집 |
| `tests/test_listing_facade.py` | facade 테스트 8 건 |

## 변경 이력

- 2026-05-12 — `gather/LISTING.md` → 본 sub-spec 통합 (Skill OS 운영 SSOT 승격)
