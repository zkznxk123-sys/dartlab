# DuckDB 검색 카탈로그 아키텍처 초안

## 문제

현재 검색 빌드는 이미 월간 `main` + 일간 `delta` 구조다. 병목은 검색 런타임 자체보다
문서 수집량이 커질수록 "무엇이 바뀌었는지"를 안정적으로 판단하고, 빌드 대상만 뽑는 단계다.

DuckDB 를 쓰는 이유는 다음이다.

- Parquet/Arrow 를 SQL 로 직접 다룰 수 있다.
- anti-join, hash 비교, compaction manifest 관리가 쉽다.
- Polars 대형 eager collect 를 피하고, staging/export 단위로 쪼갤 수 있다.
- 기존 CSR BM25 런타임과 충돌하지 않는다.

## 책임 분리

```text
Polars
  원천 parquet/html/text 정규화

DuckDB
  documents 카탈로그
  stagingDocs 비교
  new/changed/unchanged 판정
  main/delta export manifest

fieldIndex.py
  기존 CSR BM25 빌드/저장/검색

RAG/Embedding sidecar
  후보 검색 이후 선택적 chunk/rerank/answer
```

## 테이블 초안

```sql
documents(
  doc_key,
  source,
  rcept_no,
  section_order,
  corp_code,
  corp_name,
  stock_code,
  rcept_dt,
  report_nm,
  section_title,
  section_content,
  text_hash,
  content_len,
  deleted,
  updated_at
)

segments(
  segment_id,
  kind,
  schema_version,
  tokenizer_version,
  built_at,
  min_date,
  max_date,
  doc_count,
  artifact_path
)

segment_docs(
  segment_id,
  doc_key,
  local_doc_id,
  text_hash
)
```

## 졸업 방향

1. 합성 문서로 diff/commit/export parity 확인.
2. bounded allFilings parquet 를 staging 해서 현재 `rebuildDelta()` 입력과 동일 row 를 만들기.
3. panel rollup 문서도 `doc_key` 체계에 흡수.
4. DuckDB export 로 만든 CSR segment 와 기존 direct builder 의 검색 결과 parity 측정.
5. `unifiedSearchRecipe/eval/liveBattery.py`로 품질 회귀 0 확인.

## 기각선

- DuckDB FTS 를 기본 검색 엔진으로 승격하지 않는다.
- 전체 문서 임베딩을 기본 경로로 넣지 않는다.
- `src/dartlab/**` 본진 변경은 본 실험이 parity 와 증분성 실측을 끝내기 전까지 하지 않는다.

