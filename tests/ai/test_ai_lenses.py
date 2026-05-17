"""Analysis lenses — system prompt 패치 + capability 힌트."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


def test_lens_catalog_has_four_perspectives():
    from dartlab.ai.lenses import LENSES

    assert set(LENSES) == {"fundamental", "macro", "technical", "sentiment"}


def test_each_lens_has_prompt_patch_and_hints():
    from dartlab.ai.lenses import LENSES

    for name, lens in LENSES.items():
        assert lens.name == name
        assert lens.promptPatch
        assert lens.capabilityHints
        assert all(isinstance(hint, str) and hint for hint in lens.capabilityHints)


def test_fundamental_lens_includes_company_show_hint():
    from dartlab.ai.lenses import FUNDAMENTAL_LENS

    assert "Company.show" in FUNDAMENTAL_LENS.capabilityHints


def test_macro_lens_includes_macro_capability_hints():
    from dartlab.ai.lenses import MACRO_LENS

    assert any(hint.startswith("macro.") for hint in MACRO_LENS.capabilityHints)
