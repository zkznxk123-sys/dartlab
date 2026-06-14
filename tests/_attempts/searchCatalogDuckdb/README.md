# searchCatalogDuckdb — DuckDB 기반 검색 카탈로그 실험

> 상태: 카테고리 신설 + 개념확립 1차. 본진 미투입.

문서량이 계속 증가하는 DartLab 검색 인덱스를 매번 전체 Polars collect 로 다시 만들지 않도록,
DuckDB 를 **검색 런타임 대체재가 아니라 문서 카탈로그·증분 판정·빌드 대상 export 엔진**으로 쓰는
실험이다.

## 가설

현재 공식 검색은 `main.npz + delta.npz + meta.parquet` CSR BM25 런타임을 유지한다.
DuckDB 는 그 앞단에서 다음 책임만 맡는다.

1. 수집 문서의 영속 카탈로그
2. `doc_key + text_hash` 기준 중복 제거와 변경 감지
3. 일간 delta 빌드 대상 export
4. 월간 main compaction 대상 export
5. liveBattery / router gold 평가용 SQL 분석

즉, FTS 품질을 다시 묻는 실험이 아니다. `unifiedSearchRecipe`에서 DuckDB FTS 는 한국어 품질 이점이
없었으므로, 본 실험은 **현재 CSR 빌더에 넘길 입력을 더 안정적으로 만드는가**만 검증한다.

## 실행

```bash
uv run python -X utf8 tests/_attempts/searchCatalogDuckdb/attempt01CatalogDiffTest.py
uv run python -X utf8 tests/_attempts/searchCatalogDuckdb/demo.py
```

## 파일 지도

| 파일 | 역할 |
|---|---|
| `catalogDuckdb.py` | DuckDB schema, staging, diff, commit, CSR export 프로토타입 |
| `attempt01CatalogDiffTest.py` | 합성 문서로 new/changed/unchanged 판정과 기존 CSR builder parity 검증 |
| `demo.py` | 사람이 바로 볼 수 있는 JSON 요약 출력 |
| `ARCHITECTURE.md` | 졸업 방향과 본진 연결점 |

## 1차 판정 기준

- 같은 문서 재수집은 `unchanged` 로 빠진다.
- 본문이 바뀐 문서만 `changed` 로 나온다.
- 신규 문서만 `new` 로 나온다.
- DuckDB export 를 기존 `buildContentSegment()`에 넣었을 때 직접 row 입력과 동일한 CSR 구조가 나온다.

