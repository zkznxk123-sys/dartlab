"""core/memory hypothesis property — T6-1 (7/10)."""

from __future__ import annotations

import pytest
from hypothesis import given
from hypothesis import strategies as st


@pytest.mark.unit
class TestMemoryProperty:
    """core/memory.profileCall 의 property 4."""

    @given(
        label=st.text(alphabet=st.characters(min_codepoint=ord("a"), max_codepoint=ord("z")), min_size=1, max_size=30)
    )
    def test_profile_call_label_accepts_any_string(self, label: str) -> None:
        """임의 label → 정상 wrap."""
        from dartlab.core.memory import profileCall

        @profileCall(label)
        def noop() -> int:
            return 42

        assert noop() == 42

    def test_profile_call_preserves_args(self) -> None:
        """wrap 후에도 args 전달."""
        from dartlab.core.memory import profileCall

        @profileCall("test")
        def add(a: int, b: int) -> int:
            return a + b

        assert add(2, 3) == 5

    def test_profile_call_preserves_exception(self) -> None:
        """wrap 안 raise → 호출자에 전파."""
        from dartlab.core.memory import profileCall

        @profileCall("test")
        def fails() -> None:
            raise ValueError("expected")

        with pytest.raises(ValueError, match="expected"):
            fails()

    @given(returnVal=st.integers())
    def test_profile_call_preserves_return(self, returnVal: int) -> None:
        from dartlab.core.memory import profileCall

        @profileCall("test")
        def identity() -> int:
            return returnVal

        assert identity() == returnVal
