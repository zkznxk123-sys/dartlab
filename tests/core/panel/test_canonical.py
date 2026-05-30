"""core/panel canonical mirror — rawId→disclosureKey resolve (데이터 경량).

``core/panel/canonical.py`` 의 ``resolveDisclosureKey``(단건)/``resolveBatch``(컬럼 부착).
bridge lookup 기반 — 미등록 rawId 는 None, empty df 는 passthrough.
"""

from __future__ import annotations

import polars as pl
import pytest

from dartlab.core.panel import resolveBatch, resolveDisclosureKey

pytestmark = pytest.mark.unit


def test_resolve_disclosure_key_unknown_none() -> None:
    """미등록 rawId → None (bridge 비어도 안전)."""
    assert resolveDisclosureKey("__nonexistent_rawid__", "kr") is None


def test_resolve_batch_adds_disclosure_key_column() -> None:
    """xbrlClass 컬럼 df → disclosureKey 컬럼 부착."""
    df = pl.DataFrame({"xbrlClass": ["BS_C", None]})
    out = resolveBatch(df, marketNs="kr")
    assert "disclosureKey" in out.columns
    assert out.height == 2


def test_resolve_batch_empty_passthrough() -> None:
    """빈 df 는 그대로 (lookup 0)."""
    empty = pl.DataFrame({"xbrlClass": []}, schema={"xbrlClass": pl.Utf8})
    assert resolveBatch(empty, marketNs="kr").height == 0
