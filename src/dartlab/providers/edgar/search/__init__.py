"""EDGAR search — SEC Full-Text Search wrapper placeholder (룰 2 mirror).

Implementation status
---------------------
- 구현 상태: **미구현 (reserved) — 본질적 비대칭**
- 대응 dart 모듈: ``providers/dart/search/`` (5 파일 / 4266 줄) — ngram + BM25
  자체 인덱스 빌드 + searchScope.
- SEC EDGAR 측 본질:
  - SEC 가 **EDGAR Full-Text Search API** 공식 제공 (``https://efts.sec.gov/LATEST/
    search-index``). dart 측처럼 자체 인덱스 빌드 불필요.
  - 따라서 EDGAR search 는 *thin wrapper* 만 필요 — SEC API 호출 + 응답 정규화.
    dart/search 의 4266 줄과 LOC 평형 불가능 (본질 차이, 비대칭 정당).

언제 채울 것인가
----------------
- 사용자가 "edgar 본문 검색" 시나리오 요구 시 — Company.search 가 provider 별
  분기. dart 는 자체 인덱스, edgar 는 SEC API 호출.
- 추가 시 1 파일 (~150 줄) 권장 — wrapper + 응답 dataframe 정규화.

본 폴더는 mirror 만족 placeholder. ``__all__ = []``.
"""

__all__: list[str] = []
