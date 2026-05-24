"""core/di hypothesis property — T6-1."""

from __future__ import annotations

import pytest
from hypothesis import given
from hypothesis import strategies as st


@pytest.mark.unit
class TestDiProperty:
    """DI getter/setter round-trip property 5."""

    @given(marker=st.text(min_size=1, max_size=10))
    def test_finance_accessor_round_trip(self, marker: str) -> None:
        from dartlab.core.di import getFinanceAccessor, setFinanceAccessor

        prior = getFinanceAccessor()
        try:

            class _Stub:
                pass

            stub = _Stub()
            stub.marker = marker
            setFinanceAccessor(stub)
            assert getFinanceAccessor() is stub
            assert getFinanceAccessor().marker == marker
        finally:
            setFinanceAccessor(prior)

    def test_macro_provider_round_trip(self) -> None:
        from dartlab.core.di import getMacroProvider, setMacroProvider

        prior = getMacroProvider()
        try:

            class _Stub:
                pass

            stub = _Stub()
            setMacroProvider(stub)
            assert getMacroProvider() is stub
        finally:
            setMacroProvider(prior)

    def test_quant_accessor_round_trip(self) -> None:
        from dartlab.core.di import getQuantAccessor, setQuantAccessor

        prior = getQuantAccessor()
        try:

            class _Stub:
                pass

            stub = _Stub()
            setQuantAccessor(stub)
            assert getQuantAccessor() is stub
        finally:
            setQuantAccessor(prior)

    def test_industry_accessor_round_trip(self) -> None:
        from dartlab.core.di import getIndustryAccessor, setIndustryAccessor

        prior = getIndustryAccessor()
        try:

            class _Stub:
                pass

            stub = _Stub()
            setIndustryAccessor(stub)
            assert getIndustryAccessor() is stub
        finally:
            setIndustryAccessor(prior)
