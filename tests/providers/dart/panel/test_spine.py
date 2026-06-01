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


def test_spine_chapter_rank_nondecreasing_with_order() -> None:
    """spineOrder 증가 시 chapterRank 비감소 (챕터 경계 단조 — 정부 문서순)."""
    from dartlab.providers.dart.panel.spine import SPINE

    if not SPINE:
        pytest.skip("spineData 비어있음")
    byOrder = sorted(SPINE.values(), key=lambda v: v[0])
    chRanks = [v[2] for v in byOrder]
    assert chRanks == sorted(chRanks)


def test_spine_lookup_helpers() -> None:
    """spineOrderOf/chapterRankOf: 등재→값, 미등재→None."""
    from dartlab.providers.dart.panel.spine import SPINE, chapterRankOf, spineOrderOf

    assert spineOrderOf("__nonexistent__") is None
    assert chapterRankOf("__nonexistent__") is None
    if SPINE:
        anyKey = next(iter(SPINE))
        assert spineOrderOf(anyKey) == SPINE[anyKey][0]
        assert chapterRankOf(anyKey) == SPINE[anyKey][2]
