"""panel 전역 정부-택소노미 뼈대(spine) read 표면 — 행 순서·계층 lookup (순수 dict, lxml 0).

``spineData.py``(spineBuilder 생성물, git 추적)를 module-level dict 로 1회 변환. ``read.readWide``
가 wide 각 행의 ``rowIdentity`` 로 ``SPINE`` 을 조회해 정부 문서순서(chapterRank, spineOrder)로
정렬한다. 데이터 파일 read 0(코드 import), 누적 0(module-level 상수).

LLM Specifications:
    AntiPatterns:
        - parquet/외부 파일 read 금지 — spineData.py import (순수 코드, R2 read 표면).
        - 매 read dict 재구성 금지 — module-level 1회.
    OutputSchema:
        - ``SPINE: dict[str, tuple[int, str | None, int]]`` (identity → (spineOrder, parentKey, chapterRank)).
        - ``spineOrderOf(identity) -> int | None`` / ``chapterRankOf(identity) -> int | None``.
    Prerequisites:
        - spineData.py (spineBuilder 생성). 없으면 빈 SPINE.
    Freshness:
        - spineData.py 재생성 시 다음 import 반영.
    Dataflow:
        - spineData.SPINE_ROWS → SPINE dict.
    TargetMarkets:
        - KR (DART). EDGAR 후속.
"""

from __future__ import annotations

from .spineData import SPINE_ROWS

# identity → (spineOrder, parentKey, chapterRank). module-level 1회 (누적 0).
SPINE: dict[str, tuple[int, str | None, int]] = {
    ident: (spineOrder, parentKey, chapterRank) for ident, spineOrder, parentKey, chapterRank in SPINE_ROWS
}


def spineOrderOf(identity: str) -> int | None:
    """identity → 정부 문서 표시순서 (미등재 None).

    Args:
        identity: rowIdentity 결과 (canonicalKey 또는 NARR::chapter␟section).

    Returns:
        spineOrder(int) 또는 None (spine 미등재).

    Raises:
        없음.

    Example:
        >>> spineOrderOf("__nonexistent__") is None
        True

    SeeAlso:
        - ``chapterRankOf`` — 챕터 대순서.
        - ``read.readWide`` — 본 lookup 으로 wide 정렬.

    Requires:
        - 없음 (module-level dict).

    Capabilities:
        - 한 행 identity 의 전역 정부 순서를 O(1) 조회.

    Guide:
        - readWide 가 일괄 map. 직접 호출 가능.

    AIContext:
        - 순수 dict get — 부작용 0.

    LLM Specifications:
        AntiPatterns:
            - 미등재에 임의 order 부여 금지 — None(read 가 말미 처리).
        OutputSchema:
            - ``int | None``.
        Prerequisites:
            - SPINE dict.
        Freshness:
            - spineData 재생성 반영.
        Dataflow:
            - identity → SPINE → spineOrder.
        TargetMarkets:
            - KR + US 공통.
    """
    entry = SPINE.get(identity)
    return entry[0] if entry else None


def chapterRankOf(identity: str) -> int | None:
    """identity → 챕터 대순서 rank (미등재 None).

    Args:
        identity: rowIdentity 결과.

    Returns:
        chapterRank(int) 또는 None (spine 미등재).

    Raises:
        없음.

    Example:
        >>> chapterRankOf("__nonexistent__") is None
        True

    SeeAlso:
        - ``spineOrderOf`` — 문서 표시순서.
        - ``read.readWide`` — (chapterRank, spineOrder) 정렬.

    Requires:
        - 없음.

    Capabilities:
        - 챕터(I~XII) 대순서를 O(1) 조회 — 같은 챕터 내 spineOrder 세부 정렬.

    Guide:
        - readWide 가 1차 정렬키로 사용. 직접 호출 가능.

    AIContext:
        - 순수 dict get.

    LLM Specifications:
        AntiPatterns:
            - 미등재에 임의 rank 부여 금지 — None.
        OutputSchema:
            - ``int | None``.
        Prerequisites:
            - SPINE dict.
        Freshness:
            - spineData 재생성 반영.
        Dataflow:
            - identity → SPINE → chapterRank.
        TargetMarkets:
            - KR + US 공통.
    """
    entry = SPINE.get(identity)
    return entry[2] if entry else None


__all__ = ["SPINE", "chapterRankOf", "spineOrderOf"]
