"""EDGAR search — SEC Full-Text Search wrapper.

Implementation status
---------------------
- 구현 상태: **구현 완료 (v1, thin wrapper)**
- 대응 dart 모듈: ``providers/dart/search/`` (5 파일 / 4266 줄) — ngram + BM25
  자체 인덱스 빌드 + searchScope.
- SEC EDGAR 측 본질:
  - SEC 가 **EDGAR Full-Text Search API** 공식 제공 (``https://efts.sec.gov/
    LATEST/search-index``). dart 측처럼 자체 인덱스 빌드 불필요.
  - thin wrapper — SEC API 호출 + 응답 dataframe 정규화. dart 와 LOC 평형 X.

공개 surface (api.py)
---------------------
- ``search(query, ...)`` — 단발 검색 (limit ≤ pageSize 결과 반환).
- ``fetchHits(query, ...)`` — fetch-prefix alias (룰 8 limit + 룰 10 iter pair).
- ``iterHits(query, ..., pageSize, maxPages)`` — streaming page generator.
"""

from dartlab.providers.edgar.search.api import fetchHits, iterHits, search

__all__ = ["search", "fetchHits", "iterHits"]
