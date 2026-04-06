"""R33 audit 회귀 — search/searchName/listing.

R33-1: search('') silent → ValueError
R33-2: searchName('') silent → ValueError
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


def test_search_empty_query_raises():
    """R33-1: 빈 query → ValueError."""
    import dartlab
    with pytest.raises(ValueError, match="비어"):
        dartlab.search('')


def test_search_whitespace_only_raises():
    """공백만 있는 query → ValueError."""
    import dartlab
    with pytest.raises(ValueError, match="비어"):
        dartlab.search('   ')


def test_search_name_empty_raises():
    """R33-2: 빈 keyword → ValueError."""
    import dartlab
    with pytest.raises(ValueError, match="비어"):
        dartlab.searchName('')


def test_search_function_validates_query_source():
    """source check — search 함수에 빈 query 검증 코드 있는지."""
    from dartlab import search
    import inspect
    src = inspect.getsource(search)
    assert "비어" in src
    assert "ValueError" in src


def test_search_function_exists():
    """공개 API 보호 — dartlab.listing 함수 존재 확인 (실제 호출은 메모리 무거움)."""
    import dartlab
    assert hasattr(dartlab, 'listing')
    assert callable(dartlab.listing)
    assert hasattr(dartlab, 'search')
    assert callable(dartlab.search)
    assert hasattr(dartlab, 'searchName')
    assert callable(dartlab.searchName)
