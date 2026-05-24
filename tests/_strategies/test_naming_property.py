"""core/naming hypothesis property — T6-1 (snake_case 식별 표면 audit)."""

from __future__ import annotations

import re

import pytest
from hypothesis import given
from hypothesis import strategies as st


@pytest.mark.unit
class TestNamingProperty:
    """dartlab __all__ 안 camelCase 강행 property 4."""

    def test_dartlab_public_api_camel_case(self) -> None:
        import dartlab

        snake = [n for n in dartlab.__all__ if "_" in n and not n.startswith("_")]
        whitelist = {"DartlabDeprecationWarning"}
        unexpected = [n for n in snake if n not in whitelist]
        assert unexpected == [], f"snake_case in __all__: {unexpected}"

    def test_no_camel_word_collision(self) -> None:
        import dartlab

        seen = set()
        for n in dartlab.__all__:
            if n.startswith("_"):
                continue
            key = n.lower()
            assert key not in seen or n == n.lower(), n
            seen.add(key)

    @given(
        text=st.text(
            alphabet="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ",
            min_size=2,
            max_size=20,
        )
    )
    def test_camel_case_regex_accepts_alpha(self, text: str) -> None:
        camelRe = re.compile(r"^[a-zA-Z][a-zA-Z0-9]*$")
        assert camelRe.match(text) is not None

    def test_module_level_names(self) -> None:
        from dartlab.core import market

        public = [n for n in dir(market) if not n.startswith("_")]
        for n in public:
            if n in {"annotations", "re"}:
                continue
            assert "_" not in n or n.isupper(), n
