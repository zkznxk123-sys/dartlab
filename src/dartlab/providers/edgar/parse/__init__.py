"""EDGAR parse — viewer/diff 파서 placeholder (룰 2 mirror).

Implementation status
---------------------
- 구현 상태: **미구현 (reserved)**
- 대응 dart 모듈: ``providers/dart/parse/`` (4 파일 / 1043 줄) — diffEvaluator,
  viewerPageExtractor, tableHorizontalizer, scoreHelper.
- SEC EDGAR 측 본질: 10-K/10-Q 의 HTML viewer 페이지 차이 비교 / 표 horizontalization
  / score helper. DART 와 같은 viewer page 단위 분석 흐름은 동일하나, SEC 의
  iXBRL 직접 제공으로 일부 책임이 ``providers/edgar/finance/xbrlConcepts`` 와 중복 가능.

언제 채울 것인가
----------------
- 사용자 시나리오 검증 후 — "edgar 측 viewer page diff 가 필요한 사용 사례가 등장"
  하는 시점. 현재는 dart 측만 정착 후 분석 패턴 학습 단계.
- 추가 시 dart/parse 의 파일 구조 미러 권장 (diffEvaluator/viewerPageExtractor/
  tableHorizontalizer/scoreHelper 4 파일) — 호출자 (Company.show / story) 가
  provider 분기 단순화 가능.

본 폴더는 mirror 만족 placeholder. 실제 호출 시 ``ModuleNotFoundError`` 가 아닌
빈 namespace 노출 (``__all__ = []``).
"""

__all__: list[str] = []
