"""Sentinel — `core/finance/unitNormalize.py` 동작 회귀 차단 (Layer 1)."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


def test_normalize_finance_amount_won_unit():
    from dartlab.core.utils.unitNormalize import normalizeFinanceAmount

    # 백만원 → 원
    assert normalizeFinanceAmount(12_097_207, "백만원") == 12_097_207_000_000.0
    assert normalizeFinanceAmount(1, "백만원") == 1_000_000.0

    # 천원 → 원
    assert normalizeFinanceAmount(1234, "천원") == 1_234_000.0

    # 원 → 원 (1배)
    assert normalizeFinanceAmount(12_000_000, "원") == 12_000_000.0


def test_normalize_finance_amount_string_input():
    from dartlab.core.utils.unitNormalize import normalizeFinanceAmount

    # 콤마 포함 문자열
    assert normalizeFinanceAmount("12,097,207", "백만원") == 12_097_207_000_000.0


def test_normalize_finance_amount_none_safe():
    from dartlab.core.utils.unitNormalize import normalizeFinanceAmount

    assert normalizeFinanceAmount(None, "백만원") is None
    assert normalizeFinanceAmount("", "백만원") is None
    assert normalizeFinanceAmount("-", "백만원") is None
    assert normalizeFinanceAmount("abc", "백만원") is None


def test_normalize_finance_amount_zero_preserved():
    from dartlab.core.utils.unitNormalize import normalizeFinanceAmount

    assert normalizeFinanceAmount(0, "원") == 0.0
    assert normalizeFinanceAmount(0, "백만원") == 0.0


def test_normalize_from_unit_scale():
    from dartlab.core.constants import UNIT_SCALE
    from dartlab.core.utils.unitNormalize import normalizeFromUnitScale

    # UNIT_SCALE 백만원=1.0, 천원=0.001, 원=0.000001
    assert normalizeFromUnitScale(12_097_207, UNIT_SCALE["백만원"]) == 12_097_207_000_000.0
    assert normalizeFromUnitScale(12_097_207_000_000, UNIT_SCALE["원"]) == 12_097_207_000_000.0
    assert normalizeFromUnitScale(12_097_207_000, UNIT_SCALE["천원"]) == 12_097_207_000_000.0
    assert normalizeFromUnitScale(None, UNIT_SCALE["백만원"]) is None
