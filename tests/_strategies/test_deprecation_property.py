"""core/deprecation hypothesis property — T6-1."""

from __future__ import annotations

import warnings

import pytest
from hypothesis import given
from hypothesis import strategies as st


@pytest.mark.unit
class TestDeprecationProperty:
    """deprecation warnDeprecated / deprecated 데코레이터 property 4."""

    @given(
        name=st.text(min_size=1, max_size=20),
        version=st.text(alphabet="0123456789.", min_size=3, max_size=8),
    )
    def test_warn_emits_dartlab_warning(self, name: str, version: str) -> None:
        from dartlab.core.deprecation import DartlabDeprecationWarning, warnDeprecated

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            warnDeprecated(name, version)
        assert any(issubclass(rec.category, DartlabDeprecationWarning) for rec in w)

    @given(alternative=st.text(min_size=1, max_size=20))
    def test_warn_includes_alternative(self, alternative: str) -> None:
        from dartlab.core.deprecation import warnDeprecated

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            warnDeprecated("foo", "1.0.0", alternative=alternative)
        assert any(alternative in str(rec.message) for rec in w)

    def test_deprecated_decorator_returns_callable(self) -> None:
        from dartlab.core.deprecation import deprecated

        @deprecated("1.0.0")
        def myFunc() -> int:
            return 42

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            assert myFunc() == 42

    def test_deprecated_decorator_emits_warning(self) -> None:
        from dartlab.core.deprecation import DartlabDeprecationWarning, deprecated

        @deprecated("1.0.0")
        def myFunc() -> int:
            return 1

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            myFunc()
        assert any(issubclass(rec.category, DartlabDeprecationWarning) for rec in w)
