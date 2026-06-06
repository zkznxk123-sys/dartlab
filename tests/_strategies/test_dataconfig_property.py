"""core/dataConfig hypothesis property — T6-1."""

from __future__ import annotations

import pytest
from hypothesis import given
from hypothesis import strategies as st


@pytest.mark.unit
class TestDataConfigProperty:
    """dataConfig.hfBaseUrl + DATA_RELEASES property 4."""

    def test_releases_is_non_empty(self) -> None:
        from dartlab.core.dataConfig import DATA_RELEASES

        assert isinstance(DATA_RELEASES, dict)
        assert len(DATA_RELEASES) > 0

    def test_hf_base_url_default_returns_str(self) -> None:
        from dartlab.core.dataConfig import hfBaseUrl

        url = hfBaseUrl()
        assert isinstance(url, str)
        assert url.startswith("http")

    @given(category=st.sampled_from(["panel"]))
    def test_hf_base_url_known_category(self, category: str) -> None:
        from dartlab.core.dataConfig import hfBaseUrl

        url = hfBaseUrl(category)
        assert isinstance(url, str)
        assert len(url) > 0

    def test_unknown_category_raises(self) -> None:
        from dartlab.core.dataConfig import hfBaseUrl

        with pytest.raises((KeyError, ValueError)):
            hfBaseUrl("NEVER_EXISTS_CATEGORY_XYZ_999")
