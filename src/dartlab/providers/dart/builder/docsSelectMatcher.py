"""DART Company 의 select 보조 helper.

Company.select / _selectImpl 가 호출하는 docs item 역인덱스 + cascade 매칭 로직.

Module-level helpers:
    buildDocsItemIndex   — topic 의 모든 테이블 블록 수평화 + 항목명 역인덱스
    selectFromDocsTopic  — indList cascade 매칭 (exact → contains → fuzzy)
    selectFromDocsTopicAll — multi-block docs topic 전체 처리
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import polars as pl

from dartlab.core.polarsUtil import isEmptyDf
from dartlab.providers.dart.checks import _isPeriodColumn

if TYPE_CHECKING:
    from dartlab.providers.dart.company import Company


def buildDocsItemIndex(company: Company, topic: str) -> dict[str, list[tuple[int, pl.DataFrame]]]:
    """topic 의 모든 테이블 블록을 수평화하고 항목명 역인덱스를 빌드.

    Args:
        company: ``Company`` 인스턴스 (캐시 사용).
        topic: topic 이름 (예: ``"BS"``).

    Returns:
        ``{normalizedItemKey: [(blockOrder, horizontalDF), ...]}`` 역인덱스 dict.

    Raises:
        없음.

    Example:
        >>> idx = buildDocsItemIndex(c, "BS")

    SeeAlso:
        - <TODO: 관련 함수/엔진>

    Requires:
        - dartlab
        - polars
    """
    from dartlab.core.show import normalizeItemKey

    cacheKey = f"_docsItemIdx_{topic}"
    cached = company._cache.get(cacheKey)
    if cached is not None:
        return cached

    # 전체 sections 캐시가 있으면 재사용, 없으면 해당 topic 만 부분 빌드
    if "_sections" in company._cache:
        sec = company._cache["_sections"]
    else:
        docsSections = company._docs.sections
        sec = docsSections.forTopics({topic}) if docsSections is not None else None
    if sec is None:
        company._cache[cacheKey] = {}
        return {}

    topicRows = sec.filter(pl.col("topic") == topic)
    if topicRows.is_empty():
        company._cache[cacheKey] = {}
        return {}

    blockIndex = company._buildBlockIndex(topicRows)
    periodCols = [c for c in topicRows.columns if _isPeriodColumn(c)]

    idx: dict[str, list[tuple[int, pl.DataFrame]]] = {}

    for row in blockIndex.iter_rows(named=True):
        bo = row["block"]
        bt = row.get("type", "text")
        src = row.get("source", "docs")
        if bt != "table" or src != "docs":
            continue

        from dartlab.providers.dart.parse.tableHorizontalizer import (
            horizontalizeTableBlock,
        )

        hDf = horizontalizeTableBlock(topicRows, bo, periodCols)
        if isEmptyDf(hDf):
            continue

        itemCol = "항목" if "항목" in hDf.columns else None
        if itemCol is None:
            for c in hDf.columns:
                if not _isPeriodColumn(c):
                    itemCol = c
                    break
        if itemCol is None:
            continue

        for val in hDf[itemCol].to_list():
            if val is None:
                continue
            nk = normalizeItemKey(str(val))
            idx.setdefault(nk, []).append((bo, hDf))

    company._cache[cacheKey] = idx
    return idx


def selectFromDocsTopic(
    company: Company,
    topic: str,
    indList: list[str],
    colList: list[str] | None,
) -> pl.DataFrame | None:
    """역인덱스에서 ``indList`` 항목을 cascade 매칭 (exact → contains → fuzzy).

    Args:
        company: Company 인스턴스.
        topic: topic 이름.
        indList: 검색 항목명 리스트.
        colList: period 컬럼 필터 (None 이면 전체).

    Returns:
        매칭된 행 + 필터된 컬럼 DataFrame 또는 None.

    Raises:
        없음.

    Example:
        >>> selectFromDocsTopic(c, "BS", ["총자산"], colList=["2024", "2023"])

    SeeAlso:
        - <TODO: 관련 함수/엔진>

    Requires:
        - dartlab
        - polars
    """
    from dartlab.core.show import normalizeItemKey, selectFromShow

    idx = buildDocsItemIndex(company, topic)
    if not idx:
        return None

    normQueries = [normalizeItemKey(q) for q in indList]
    allNormKeys = list(idx.keys())

    matched: list[tuple[int, pl.DataFrame]] = []
    matchedKeys: set[str] = set()

    # 1) exact
    for nq in normQueries:
        if nq in idx and nq not in matchedKeys:
            matched.extend(idx[nq])
            matchedKeys.add(nq)

    # 2) contains
    if not matched:
        for nq in normQueries:
            for nk in allNormKeys:
                if (nq in nk or nk in nq) and nk not in matchedKeys:
                    matched.extend(idx[nk])
                    matchedKeys.add(nk)

    # 3) fuzzy
    if not matched:
        import difflib

        for nq in normQueries:
            close = difflib.get_close_matches(nq, allNormKeys, n=3, cutoff=0.7)
            for ck in close:
                if ck not in matchedKeys:
                    matched.extend(idx[ck])
                    matchedKeys.add(ck)

    if not matched:
        return None

    # 블록별 DataFrame 에서 selectFromShow 로 행/열 필터
    parts: list[pl.DataFrame] = []
    seenBo: set[int] = set()
    for bo, hDf in matched:
        if bo in seenBo:
            continue
        seenBo.add(bo)
        filtered = selectFromShow(hDf, indList, colList)
        if filtered is not None:
            parts.append(filtered)

    if not parts:
        return None
    if len(parts) == 1:
        return parts[0]
    return pl.concat(parts, how="diagonal_relaxed")


def selectFromDocsTopicAll(
    company: Company,
    topic: str,
    indList: list[str] | None,
    colList: list[str] | None,
) -> pl.DataFrame | None:
    """multi-block docs topic: ``indList``/``colList`` 조합 처리.

    indList 가 있으면 cascade 매칭, None 이면 전체 항목. colList 는 기간 필터.

    Args:
        company: Company 인스턴스.
        topic: topic 이름.
        indList: 검색 항목명 리스트 (None 이면 전체).
        colList: period 컬럼 필터 (None 이면 전체).

    Returns:
        통합 DataFrame 또는 None.

    Raises:
        없음.

    Example:
        >>> selectFromDocsTopicAll(c, "executive", indList=None, colList=["2024"])

    SeeAlso:
        - <TODO: 관련 함수/엔진>

    Requires:
        - dartlab
        - polars
    """
    from dartlab.core.show import selectFromShow

    if indList is not None:
        return selectFromDocsTopic(company, topic, indList, colList)

    # indList=None → 전체 테이블 블록 수평화 결과 concat + colList 필터
    idx = buildDocsItemIndex(company, topic)
    if not idx:
        return None

    seenBo: set[int] = set()
    parts: list[pl.DataFrame] = []
    for entries in idx.values():
        for bo, hDf in entries:
            if bo in seenBo:
                continue
            seenBo.add(bo)
            filtered = selectFromShow(hDf, None, colList)
            if filtered is not None:
                parts.append(filtered)

    if not parts:
        return None
    if len(parts) == 1:
        return parts[0]
    return pl.concat(parts, how="diagonal_relaxed")
