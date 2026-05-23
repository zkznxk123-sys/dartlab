"""SEC iXBRL viewer page 추출 + 정규화.

10-K / 10-Q HTML 본문에서 inline XBRL fact 를 추출. dart/parse/
viewerPageExtractor 의 SEC 등가. SEC 의 iXBRL 은 HTML 안 ``<ix:nonFraction>``
/ ``<ix:nonNumeric>`` 태그로 fact 마크업 → 본 wrapper 가 BeautifulSoup 으로
파싱 → polars DataFrame 정규화.

본 wrapper 는 thin (~150 줄). 본격 iXBRL 분석은 ``providers/edgar/finance/
xbrlConcepts`` 가 cik facts API 기반으로 별도 처리.
"""

from __future__ import annotations

import polars as pl


def extractIxbrlFacts(html: str) -> pl.DataFrame:
    """iXBRL HTML 에서 fact (concept + value + period + unit) 추출.

    SEC iXBRL 마크업:
    - ``<ix:nonFraction name="us-gaap:Revenue" contextRef="C1" unitRef="USD">100</ix:nonFraction>``
    - ``<ix:nonNumeric name="dei:EntityRegistrantName" contextRef="C1">Apple Inc.</ix:nonNumeric>``

    Args:
        html: iXBRL 임베디드 HTML 본문 (10-K/10-Q viewer page).

    Returns:
        pl.DataFrame — schema: ``concept`` / ``value`` / ``contextRef`` /
        ``unitRef`` / ``decimals`` / ``factType`` (``"numeric"`` / ``"text"``).
        파싱 결과 0 → 빈 DataFrame.

    Raises:
        없음.

    Example:
        >>> df = extractIxbrlFacts(html)  # doctest: +SKIP
        >>> df.columns
        ['concept', 'value', 'contextRef', 'unitRef', 'decimals', 'factType']
    """
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        return pl.DataFrame(
            schema={
                "concept": pl.Utf8,
                "value": pl.Utf8,
                "contextRef": pl.Utf8,
                "unitRef": pl.Utf8,
                "decimals": pl.Utf8,
                "factType": pl.Utf8,
            }
        )

    soup = BeautifulSoup(html, "html.parser")
    rows: list[dict[str, str]] = []
    for tag in soup.find_all(["ix:nonfraction", "ix:nonnumeric"]):
        attrs = tag.attrs
        rows.append(
            {
                "concept": str(attrs.get("name", "")),
                "value": tag.get_text(strip=True),
                "contextRef": str(attrs.get("contextref", "")),
                "unitRef": str(attrs.get("unitref", "")),
                "decimals": str(attrs.get("decimals", "")),
                "factType": "numeric" if tag.name == "ix:nonfraction" else "text",
            }
        )
    if not rows:
        return pl.DataFrame(
            schema={
                "concept": pl.Utf8,
                "value": pl.Utf8,
                "contextRef": pl.Utf8,
                "unitRef": pl.Utf8,
                "decimals": pl.Utf8,
                "factType": pl.Utf8,
            }
        )
    return pl.DataFrame(rows)


def fetchFactsByConcept(facts: pl.DataFrame, concept: str, *, limit: int = 100) -> pl.DataFrame:
    """추출된 facts DataFrame 에서 특정 concept 의 fact 만 필터.

    Args:
        facts: ``extractIxbrlFacts`` 결과.
        concept: 검색 concept (예 ``"us-gaap:Revenue"``).
        limit: 결과 최대 row 수.

    Returns:
        해당 concept 의 facts (없으면 빈 DataFrame).

    Raises:
        없음.

    Example:
        >>> revenue = fetchFactsByConcept(facts, "us-gaap:Revenue")  # doctest: +SKIP
    """
    if facts.is_empty() or "concept" not in facts.columns:
        return facts.head(0)
    filtered = facts.filter(pl.col("concept") == concept)
    if limit > 0:
        filtered = filtered.head(limit)
    return filtered


def iterFactsByConcept(facts: pl.DataFrame, concept: str, *, batchSize: int = 50):
    """``fetchFactsByConcept`` 의 streaming pair — batchSize 단위 yield.

    Args:
        facts: ``extractIxbrlFacts`` 결과.
        concept: 검색 concept.
        batchSize: 한 batch 당 row 수.

    Yields:
        pl.DataFrame — batch 단위.

    Raises:
        없음.

    Example:
        >>> for batch in iterFactsByConcept(facts, "us-gaap:Revenue"):
        ...     pass  # doctest: +SKIP
    """
    if facts.is_empty() or "concept" not in facts.columns:
        return
    filtered = facts.filter(pl.col("concept") == concept)
    n = filtered.height
    for start in range(0, n, batchSize):
        yield filtered.slice(start, batchSize)
