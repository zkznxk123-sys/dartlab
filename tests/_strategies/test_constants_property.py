"""core/constants hypothesis property — T6-1."""

from __future__ import annotations

import pytest
from hypothesis import given
from hypothesis import strategies as st


@pytest.mark.unit
class TestConstantsProperty:
    """UNIT_SCALE / ASSET_TOTAL_KEYWORDS 정합 property 4."""

    def test_unit_scale_contains_default_key(self) -> None:
        from dartlab.core.constants import DEFAULT_UNIT_SCALE, UNIT_SCALE

        assert any(v == DEFAULT_UNIT_SCALE for v in UNIT_SCALE.values())

    def test_unit_scale_positive(self) -> None:
        from dartlab.core.constants import UNIT_SCALE

        for k, v in UNIT_SCALE.items():
            assert v > 0, k

    def test_unit_scale_monotone(self) -> None:
        from dartlab.core.constants import UNIT_SCALE

        million = UNIT_SCALE.get("백만원", 1.0)
        thousand = UNIT_SCALE.get("천원", 0.001)
        won = UNIT_SCALE.get("원", 1e-6)
        assert million > thousand > won

    @given(idx=st.integers(min_value=0, max_value=2))
    def test_asset_total_keywords_korean(self, idx: int) -> None:
        from dartlab.core.constants import ASSET_TOTAL_KEYWORDS

        if idx < len(ASSET_TOTAL_KEYWORDS):
            assert isinstance(ASSET_TOTAL_KEYWORDS[idx], str)
            assert len(ASSET_TOTAL_KEYWORDS[idx]) > 0
