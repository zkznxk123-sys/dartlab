from __future__ import annotations

import types

import polars as pl
import pytest

pytestmark = pytest.mark.unit


def test_profile_sections_returns_none_for_empty_docs_sections():
    from dartlab.providers.edgar.accessor.profileAccessor import _ProfileAccessor

    company = types.SimpleNamespace(
        _cache={},
        _docs=types.SimpleNamespace(sections=pl.DataFrame()),
    )

    accessor = _ProfileAccessor(company)
    assert accessor.sections is None
    assert company._cache["_sections"] is None
