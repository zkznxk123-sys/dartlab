"""core/dualAccess hypothesis property — T6-1."""

from __future__ import annotations

import pytest
from hypothesis import given
from hypothesis import strategies as st


@pytest.mark.unit
class TestDualAccessProperty:
    """CallableAccessor call/attr form 동치성 property 5."""

    @given(arg=st.text(min_size=1, max_size=10))
    def test_call_and_attr_form_equivalent(self, arg: str) -> None:
        from dartlab.core.dualAccess import CallableAccessor

        def fn(topic: str, suffix: str = "X") -> str:
            return f"{topic}/{suffix}"

        accessor = CallableAccessor(fn)
        assert accessor(arg) == getattr(accessor, arg)()

    @given(arg=st.text(min_size=1, max_size=10), suffix=st.text(min_size=1, max_size=10))
    def test_kwargs_passthrough(self, arg: str, suffix: str) -> None:
        from dartlab.core.dualAccess import CallableAccessor

        def fn(topic: str, suffix: str = "default") -> str:
            return f"{topic}:{suffix}"

        accessor = CallableAccessor(fn)
        assert accessor(arg, suffix=suffix) == getattr(accessor, arg)(suffix=suffix)

    def test_dunder_attr_falls_through(self) -> None:
        from dartlab.core.dualAccess import CallableAccessor

        def fn(topic: str) -> str:
            return topic

        accessor = CallableAccessor(fn)
        assert hasattr(accessor, "__class__")

    def test_private_attr_falls_through(self) -> None:
        from dartlab.core.dualAccess import CallableAccessor

        def fn(topic: str) -> str:
            return topic

        accessor = CallableAccessor(fn)
        assert accessor._fn is fn

    @given(values=st.lists(st.text(min_size=1, max_size=8), min_size=1, max_size=5))
    def test_multiple_attrs_independent(self, values: list[str]) -> None:
        from dartlab.core.dualAccess import CallableAccessor

        def fn(topic: str) -> str:
            return topic.upper()

        accessor = CallableAccessor(fn)
        for v in values:
            assert getattr(accessor, v)() == v.upper()
