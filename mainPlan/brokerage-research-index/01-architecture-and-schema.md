# 01 — 아키텍처 · 스키마 · 관리 SSOT

> 본 문서 = 네가 요구한 "관리 SSOT 구조화 · 폴더 구조화 · 클린코드 구조화" 정본.

## 1. 데이터 스키마 (parquet · = 관리 SSOT 의 심장)

리포트 1건 = 한 행. 세 호출(날짜순·종목별·검색)이 *전부 이 스키마에서 파생*된다.

| 컬럼 | 타입 | 역할 |
|---|---|---|
| `report_id` | str | **PK = url 해시** (중복제거 SSOT — "url SSOT") |
| `broker` | str | 증권사 (미래에셋·한투·NH…) |
| `title` | str | 리포트 제목 |
| `report_type` | enum | 종목분석 / 산업분석 / 시황 / 경제 / 채권 / 기타 |
| `ticker` | str? | **종목코드** — 종목별 호출 열쇠 (산업·시황 = `null`) |
| `corp_name` | str? | 회사명 (파싱 원문) |
| `pub_date` | date | 발간일 — **날짜순 정렬 · 월별 파티션 키** |
| `url` | str | 원본 링크 (SSOT · 링크아웃 대상) |
| `snippet` | str? | 최소 사실 / 우리 생성 태그 (verbatim 장문 ❌) |
| `fetched_at` | date | 수집일 |

- **파생**: 날짜순 = `pub_date` 파티션 / 종목별 = `ticker` 필터 / 검색 = `title` contains.
- **파티션**: `pub_date` 월별 parquet — dartlab `allFilings` 월별 패턴과 동형(range-fetch 친화).
- **ticker 해소가 진짜 일** — 제목 "삼성전자 목표가 상향" → `005930`. **기존 `gather/dart/corpCode.py` 회사명↔종목 매퍼 재사용**(신설 금지). v1 = best-effort, 실패 시 `null`(날짜·검색은 영향 0). _attempts 에서 커버리지 실측이 1순위.

## 2. 폴더 구조 (졸업 후 gather 본진)

```
src/dartlab/gather/sources/brokerage/
  __init__.py    # 공개 facade: fetch(), toDataFrame()
  config.py      # ⭐관리 SSOT: BROKERS{broker → list_url, selectors, report_type, enabled}
  fetch.py       # async 수집 (GatherHttpClient + DOMAIN_POLICY)
  parse.py       # HTML → ReportMeta (config selector 적용, 범용 파서 1개)
  resolve.py     # 제목 → ticker (corpCode 매퍼 재사용)
  schema.py      # ReportMeta dataclass + polars 스키마 (§1 표 = SSOT)
  io.py          # parquet read/write (pub_date 월별 파티션)
```
```
src/dartlab/gather/mixins/research.py          # g.brokerageReports(...) 쿼리 메서드
.github/scripts/sync/syncBrokerageReports.py   # 백필 — gather 호출만(별도빌드 금지)
src/dartlab/core/dataConfig.py                 # DATA_RELEASES["brokerageReports"] 한 줄
```

**재사용(신설 아님 — 기존 자산):**

| 필요 | 재사용 자산 |
|---|---|
| HTTP·rate-limit·재시도 | `gather/infra/http.py` (GatherHttpClient · DOMAIN_POLICY 한 줄 추가) |
| 캐시·circuit breaker | `gather/infra/cache.py` · `resilience.py` (자동 연동) |
| 제목→ticker | `gather/dart/corpCode.py` (회사명↔종목) |
| HF 업로드 | `pipeline/hfUpload.py::uploadCategoryToHf("brokerageReports")` |
| HF 카테고리 레지스트리 | `core/dataConfig.py::DATA_RELEASES` |
| HF 직독(offline) | `gather/bulkData/hfBulk.py::loadFiltered(...)` |
| 외부 콘텐츠 wrap | `ai/tools/formatting.py::wrapExternal()` (snippet) |

선례 스크래핑 source(패턴 복제 대상): `gather/sources/naverNews.py` · `gather/domains/naverGlobal.py` · `gather/dart/viewer.py`.

## 3. 관리 SSOT — `config.py` 의 `BROKERS`

```python
BROKERS = {
    "미래에셋": {
        "list_url": "https://securities.miraeasset.com/bbs/board/message/list.do?categoryId=1521",
        "selectors": {"row": "...", "title": "...", "date": "...", "link": "..."},
        "report_type_map": {...},      # 게시판 카테고리 → report_type
        "enabled": True,
    },
    # 한투 · NH · 삼성 · KB · 키움 …
}
```

**증권사 추가·수정·중단 = 이 dict 한 항목만 건든다**(url + selector + type + enabled). 유지보수 단일점 = 네가 원한 "URL만 관리"의 정직한 버전(= URL + selector). 파서·수집 로직은 `parse.py`/`fetch.py` 가 범용 1벌로 흡수.

## 4. Query API (한 메서드 · 세 패턴)

```python
g.brokerageReports(
    start=None, end=None,      # 날짜 범위
    ticker=None,               # 종목별
    query=None,                # 검색 (title contains, v1)
    broker=None, report_type=None,
    source="auto",             # "hf"(기본·직독) | "live"(실시간 스크랩) | "auto"
) -> pl.DataFrame

#  날짜순 전체 →  g.brokerageReports(start="20240101", end="20240131")
#  종목별      →  g.brokerageReports(ticker="005930")
#  검색        →  g.brokerageReports(query="2차전지")
```

- `source` 는 **직교축**: 세 패턴 × 두 소스모드 전부 동작.
- 검색 v1 = `title` substring(polars 필터)로 충분. **BM25 sidecar 는 필요해질 때 phase 3**(지금 붙이면 덕지덕지 — [[feedback_always_check_clutter]]).

## 5. 3모드 → 기존 레일 매핑

| 모드 | 실제 컴포넌트 |
|---|---|
| ① 실시간 호출 | `g.brokerageReports(source="live")` → `sources/brokerage/fetch.py` |
| ② HF 직독 | `source="hf"` → `bulkData/hfBulk.py::loadFiltered` (range-fetch) |
| ③ 자동채우기 | `sync/syncBrokerageReports.py`(CI) → `uploadCategoryToHf()` → HF |

= dartlab sync(online)/prebuild(offline) SSOT 구조와 정확히 동형.

## 6. _attempts 시작 모양 (졸업 전 · 더 가볍게)

```
tests/_attempts/brokerageIndex/
  config.py    # 5~6개사 registry (미래·한투·NH·삼성·KB·키움)
  fetch.py     # 수집+파싱 (개념확립은 한 파일 OK)
  resolve.py   # 제목→ticker 실측 (커버리지 몇 %?)
  demo.py      # "제목·url·날짜·ticker 안정 추출되나" 실측
  README.md    # 결과 박제 (커버리지·실패 패턴)
```

졸업 게이트(→ §2 gather 구조 이동): ①5~6개사 안정 스크랩 ②ticker 커버리지 실측 ③모듈화 ④덕지덕지 제거 ⑤클린 ⑥9섹션 docstring.
