"""panel spine read 표면 — SPINE dict 무결성 + lookup 헬퍼 (순수, 데이터 0).

``spine/__init__.py`` 의 ``SPINE``(생성 spineData→dict) + ``spineOrderOf``/``chapterRankOf``.
spineData.py 는 buildSpine 생성물 — 본 테스트는 그 dict 구조·단조성·lookup 만 검증(빌드 미실행).
"""

from __future__ import annotations

import sys

import pytest

pytestmark = pytest.mark.unit


def test_spine_import_no_lxml() -> None:
    """spine read 표면 import 은 lxml 을 끌어오지 않는다 (R2 read 격리, 순수 dict)."""
    # 이미 다른 테스트가 lxml 을 로드했을 수 있어 spineData 소스에 lxml 부재만 정적 확인.
    import dartlab.providers.dart.panel.spine.spineData as sd

    src = sys.modules[sd.__name__].__file__
    assert src is not None
    text = open(src, encoding="utf-8").read()
    assert "import lxml" not in text and "from lxml" not in text


def test_spine_dict_structure() -> None:
    """SPINE: identity → (spineOrder, parentKey, chapterRank). 값 3-tuple 타입."""
    from dartlab.providers.dart.panel.spine import SPINE

    if not SPINE:
        pytest.skip("spineData 비어있음 (buildSpine 미실행)")
    for ident, entry in list(SPINE.items())[:5]:
        assert isinstance(ident, str)
        assert len(entry) == 3
        spineOrder, parentKey, chapterRank = entry
        assert isinstance(spineOrder, int)
        assert parentKey is None or isinstance(parentKey, str)
        assert isinstance(chapterRank, int)


def test_spine_order_monotonic_unique() -> None:
    """spineOrder 는 0..N 단조·중복0 (생성물 정합)."""
    from dartlab.providers.dart.panel.spine import SPINE

    if not SPINE:
        pytest.skip("spineData 비어있음")
    orders = sorted(v[0] for v in SPINE.values())
    assert orders == list(range(len(orders)))


def test_spine_chapter_rank_valid_range() -> None:
    """chapterRank 는 유효 범위 정수 (0~N). 단, native 문서순서라 단조는 아니다 — 정부 사업보고서는
    '(첨부)재무제표' 블록이 본문 중간에 삽입돼 chapterRank 가 spineOrder 순으로 단조 증가하지 않음.
    """
    from dartlab.providers.dart.panel.spine import SPINE

    if not SPINE:
        pytest.skip("spineData 비어있음")
    chRanks = [v[2] for v in SPINE.values()]
    maxRank = max(chRanks)
    assert all(0 <= r <= maxRank for r in chRanks)  # 유효 범위
    assert set(chRanks) == set(range(maxRank + 1))  # 0..maxRank 빈틈 0 (dense rank)


def test_spine_lookup_helpers() -> None:
    """spineOrderOf/chapterRankOf: 등재→값, 미등재→None."""
    from dartlab.providers.dart.panel.spine import SPINE, chapterRankOf, spineOrderOf

    assert spineOrderOf("__nonexistent__") is None
    assert chapterRankOf("__nonexistent__") is None
    if SPINE:
        anyKey = next(iter(SPINE))
        assert spineOrderOf(anyKey) == SPINE[anyKey][0]
        assert chapterRankOf(anyKey) == SPINE[anyKey][2]
