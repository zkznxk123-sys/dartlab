"""titleNormalizer mirror — NFKC+prefix strip+tokenize+Jaccard 순수 단위 (데이터 0).

``gather/dart/panel/build/refScan/titleNormalizer.py`` 의 1:1 mirror. stdlib 만 쓰는 순수
변환이라 합성 입력으로 완전 검증 (5 baseline 실측 케이스 + Jaccard 경계).
"""

from __future__ import annotations

import pytest

from dartlab.gather.dart.panel.build.refScan.titleNormalizer import (
    jaccardSimilarity,
    normalizeTitle,
    tokenize,
)

pytestmark = pytest.mark.unit


def test_normalize_title_prefix_and_suffix_strip() -> None:
    """숫자/Roman/괄호 prefix + 한글 어미 strip → canonical form."""
    # "의 개요"/"의 구성" 등 어미는 canonical 통일 위해 strip (회사의 개요 → 회사).
    assert normalizeTitle("1. 회사의 개요") == "회사"
    assert normalizeTitle("1. (제조서비스업)사업의 개요") == "사업"
    assert normalizeTitle("3-1. 매출원가의 구성") == "매출원가"
    assert normalizeTitle("Ⅲ. 재무에 관한 사항") == "재무"
    assert normalizeTitle("") == ""


def test_tokenize_korean_and_english_min2() -> None:
    """한글 2자+ / 영문 2자+ token set, 1글자 노이즈 제외."""
    assert tokenize("매출원가의 구성") == {"매출원가의", "구성"}
    assert tokenize("Revenue Recognition Policy") == {"Revenue", "Recognition", "Policy"}
    assert tokenize("") == set()


def test_jaccard_similarity_bounds() -> None:
    """Jaccard: 교/합, 동일=1.0, 빈셋=0.0."""
    assert jaccardSimilarity({"매출원가", "구성"}, {"매출원가", "정책"}) == pytest.approx(1 / 3)
    assert jaccardSimilarity({"a"}, {"a"}) == 1.0
    assert jaccardSimilarity(set(), set()) == 0.0
