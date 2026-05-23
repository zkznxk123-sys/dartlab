"""EDGAR parse — iXBRL viewer page diff + parser (룰 2 mirror).

Implementation status
---------------------
- 구현 상태 (iXbrlViewer): **구현 완료 (v1)** — `iXbrlViewer.py` ~150 줄.
- 구현 상태 (diffEvaluator / tableHorizontalizer): **미구현** — 별 cycle 후속.

대응 dart 모듈: ``providers/dart/parse/`` (4 파일 / 1043 줄) — diffEvaluator,
viewerPageExtractor, tableHorizontalizer, scoreHelper.

SEC EDGAR 측 본질:
- 10-K/10-Q HTML iXBRL 임베디드 fact 추출 (BeautifulSoup 기반).
- dart 와 달리 SEC 는 iXBRL 직접 제공 → 별도 viewer parser 단순.

공개 surface (iXbrlViewer.py):
- ``extractIxbrlFacts(html)`` — iXBRL HTML → fact DataFrame
- ``fetchFactsByConcept(facts, concept)`` — concept 별 필터
- ``iterFactsByConcept(facts, concept)`` — streaming pair (룰 10)
"""

from dartlab.providers.edgar.parse.iXbrlViewer import (
    extractIxbrlFacts,
    fetchFactsByConcept,
    iterFactsByConcept,
)

__all__ = ["extractIxbrlFacts", "fetchFactsByConcept", "iterFactsByConcept"]
