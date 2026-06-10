"""curatedSyn 모듈 mirror smoke — 큐레이션 동의어 사전 구조 + 경계 매칭."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


def test_imports() -> None:
    """모듈 import smoke."""
    from dartlab.providers.dart.search import curatedSyn

    assert curatedSyn is not None


def test_curated_structure() -> None:
    """CURATED 사전 — 키·값 비어있지 않고 값은 리스트."""
    from dartlab.providers.dart.search.curatedSyn import CURATED

    assert len(CURATED) >= 30
    for k, v in CURATED.items():
        assert k and isinstance(v, list) and v


def test_expand_query_boundary() -> None:
    """어절 경계 매칭 — substring 오발화 차단."""
    from dartlab.providers.dart.search.curatedSyn import expandQuery

    assert "자기주식" in expandQuery("자사주 샀어?")
    # '대표' 키가 '대표적' 어절에는 startswith 로 발화하지만, 무관 어절('표준')엔 발화 0
    assert expandQuery("표준 절차") == []
    assert expandQuery("") == []
