"""DART build — raw(zip/xml) → parquet 변환·저장 (network 0).

수집 일원화(ETL 분할): fetch 는 gather/dart 전담, 본 패키지는 Transform 전담.

- ``sections`` — zip document.xml → ``<TITLE>`` 단위 sections rows (parseSectionsByTitle).
- ``saver`` — enrich(재무/보고서 컬럼) + 정렬 + atomic parquet write.
"""
