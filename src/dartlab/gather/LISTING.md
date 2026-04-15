# Listing

목록 조회 단일 진입점. "뭐가 있는지 본다"는 모든 카탈로그성 API를 한 함수의 `kind` 인자로 통합.
"내용 안에서 찾는다"는 별도 엔진 `dartlab.search()`를 사용한다.

## 호출 계약

```python
import dartlab
dartlab.listing()                          # 전체 상장사 목록 (KR 2700+)
dartlab.listing("dartlist")                # DART 전체 법인 (비상장 포함, corp_code 8자리)
dartlab.listing("filings", corp="005930")  # 특정 종목 공시 목록
```

## 노트북

[![marimo](https://marimo.io/shield.svg)](https://marimo.app/github.com/eddmpython/dartlab/blob/master/notebooks/marimo/11_listing.py)
[![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/eddmpython/dartlab/blob/master/notebooks/colab/11_listing.ipynb)

---

| 항목 | 내용 |
|------|------|
| 레이어 | 루트 facade |
| 진입점 | `dartlab.listing(kind, ...)` |
| 소비 | gather/listing(KRX, DART CORPCODE), providers/dart/edgar(filings, topicSummaries) |
| 생산 | DataFrame — 사용자/AI가 카탈로그 탐색에 사용 |
| 원칙 | search는 건드리지 않는다 (원문 역인덱스 엔진은 별개) |

## listing vs search

- **listing** = "뭐가 있는지" — 종목/공시메타/토픽 카탈로그 조회. 빠르다, 항상 동작.
- **search** = "내용 안에서 찾기" — stem ID 역인덱스 기반 원문 매칭 (→ src/dartlab/core/search/README.md). 데이터 필요.

`listing("filings", corp=...)`는 공시 **메타 목록**만 반환한다. 본문 검색은 `dartlab.search()`로.

## API

```python
import dartlab

dartlab.listing()                              # 전 종목 (기본 = "companies", 기존 호환)
dartlab.listing("dartlist")                    # DART 전체 법인 (비상장 포함, corp_code 8자리)
dartlab.listing(market="US")                   # EDGAR 종목
dartlab.listing("filings", corp="005930")      # DART 공시 메타
dartlab.listing("filings", corp="AAPL")        # EDGAR 공시 메타 (자동 분기)
dartlab.listing("topics", corp="005930")       # 토픽 목록
```

한글 alias: `"기업"`, `"공시"`, `"토픽"`, `"법인"`, `"dart"`.

## kind 목록

| kind | 라우팅 | 필수 인자 | 비고 |
|------|--------|----------|------|
| `companies` (기본) | gather.listing.getKindList / EdgarCompany.listing | `market` (optional) | **기존 `dartlab.listing()` 100% 호환** |
| `dartlist` | gather.listing.getDartList | — | OpenDART CORPCODE.xml. 비상장 포함 115,963 법인. corp_code 8자리 |
| `filings` | `Company(corp).filings()` | `corp` | DART/EDGAR canHandle 자동 분기 + 컬럼 정규화 |
| `topics` | `Company(corp).topicSummaries()` → DataFrame | `corp` | dict → (topic, summary) 두 컬럼 |

미지원 kind는 `ValueError("unknown kind: ... — supported: companies, filings, topics, dartlist")`.

## filings 반환 컬럼 통일

DART/EDGAR `filings()` 컬럼명이 다르다. listing facade가 공통 컬럼을 앞쪽에 배치하고, 원본 컬럼은 뒤에 보존(드롭하지 않음).

| 통일 컬럼 | DART 원본 | EDGAR 원본 |
|----------|----------|-----------|
| `id` | `rceptNo` | `accession_no` |
| `date` | `rceptDate` | `filed_date` |
| `period` | `year` | `period_key` |
| `reportType` | `reportType` | `form_type` |
| `url` | `dartUrl` | SEC URL 동적 생성 (`https://www.sec.gov/Archives/edgar/data/{cik}/{acc-no-clean}/{acc-no}-index.htm`) |

DART/EDGAR 양쪽에서 `df["url"][0]`으로 바로 공시 뷰어 접근 가능.

## 설계 원칙

1. **search는 건드리지 않는다** — stem ID 역인덱스 기반 독립 엔진. 성격이 다름.
2. **레이어 위반 없음** — `gather/listing.py`(KRX 매퍼)는 그대로. 루트 facade가 라우터.
3. **기존 진입점 유지** — `c.filings()`, `c.topicSummaries()`는 deprecated 처리하지 않는다. listing이 그들을 호출하는 얇은 facade.
4. **반환 계약 통일** — 모든 kind가 Polars DataFrame.

## dartlist 데이터 파이프라인

OpenDART CORPCODE.xml → parquet 변환. GitHub Actions에서 kindList와 함께 매일 자동 수집.

### 자동화

- **워크플로**: `.github/workflows/kindlist.yml` — kindList + dartList 동시 수집
- **스크립트**: `.github/scripts/updateDartList.py` — CORPCODE.xml ZIP → parquet (독립 실행)
- **스케줄**: 매일 UTC 00:00 (KST 09:00)
- **저장**: GitHub Release (`kindlist-latest`) + HuggingFace (`metadata/dartList.parquet`)
- **변경 감지**: SHA256 해시 비교, 변경 없으면 업로드 스킵

### 사용자 로드 경로

캐시 우선순위: 메모리 → 파일(`data/dartList/dartList.parquet`, 24h TTL) → HuggingFace 자동 다운로드.
DART API 키 불필요 — HF에서 프리빌드된 parquet을 가져온다.

### dartlist vs corpCode.py

| | dartlist (getDartList) | corpCode.py (loadCorpCodes) |
|---|---|---|
| 데이터 소스 | HuggingFace (프리빌드) | OpenDART API (직접) |
| API 키 | 불필요 | DART_API_KEY 필수 |
| 용도 | 사용자 조회 (`dartlab.listing("dartlist")`) | 내부 API 호출 (8자리 corp_code 변환) |
| 갱신 | GitHub Actions 매일 자동 | 사용자 세션 24h 캐시 |

## 향후 (v2 후보)

- `kind="signals"` — 공시 키워드 트렌드. scan에 signal 축이 구현되면 라우팅.
- `kind="reports"` — review publisher가 발간한 보고서 목록.
- CLI 서브커맨드 `dartlab listing <kind>`.

## 관련 코드

| 파일 | 역할 |
|------|------|
| `src/dartlab/listing.py` | 루트 라우터 facade |
| `src/dartlab/__init__.py` | export (`from dartlab.listing import listing`) |
| `src/dartlab/gather/listing.py` | KRX/KIND 매퍼 + getDartList (companies/dartlist 데이터 소스) |
| `src/dartlab/providers/dart/company.py` | `_filings()` — DART 공시 메타 |
| `src/dartlab/providers/edgar/_docs_accessor.py` | `filings()` — EDGAR 공시 메타 |
| `.github/scripts/updateDartList.py` | CORPCODE.xml → parquet (GitHub Actions 독립 스크립트) |
| `.github/workflows/kindlist.yml` | kindList + dartList 매일 자동 수집 |
| `tests/test_listing_facade.py` | facade 테스트 8건 |
