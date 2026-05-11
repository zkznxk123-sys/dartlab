"""scan fields catalog and spec screening contract."""

from __future__ import annotations

import polars as pl
import pytest

pytestmark = pytest.mark.unit


def test_scan_fields_lists_all_sources():
    """scan("fields") exposes every planned source family."""
    import dartlab

    df = dartlab.scan("fields")

    assert {"field", "label", "source", "kind", "unit", "operatorSet", "coverage", "example", "notes"} <= set(
        df.columns
    )
    assert {"finance", "report", "docs", "krx", "krxIndex"} <= set(df["source"].to_list())


def test_scan_fields_searches_korean_and_english():
    """Field discovery supports both Korean labels and English field keys."""
    import dartlab

    roe = dartlab.scan("fields", "roe")
    sales = dartlab.scan("fields", "매출")

    assert "finance.ratio.roe" in roe["field"].to_list()
    assert any("sales" in field or "revenue" in field for field in sales["field"].to_list())


def test_screen_spec_filters_selects_and_sorts(monkeypatch):
    """screen(spec=...) applies where/select/sort using field value frames."""
    from dartlab.scan.builder import fields as scan_fields
    from dartlab.scan.screen import scanScreen

    values = {
        "finance.ratio.roe": pl.DataFrame({"stockCode": ["000001", "000002"], "finance.ratio.roe": [12.0, 4.0]}),
        "valuation.pbr": pl.DataFrame({"stockCode": ["000001", "000002"], "valuation.pbr": [0.8, 1.5]}),
        "krx.marketCap": pl.DataFrame({"stockCode": ["000001", "000002"], "krx.marketCap": [1000, 2000]}),
    }

    monkeypatch.setattr(scan_fields, "_loadFieldValues", lambda field, spec: values[field])

    df = scanScreen(
        spec={
            "where": [{"field": "finance.ratio.roe", "op": ">", "value": 10}],
            "select": ["valuation.pbr", "krx.marketCap"],
            "sort": {"field": "valuation.pbr", "desc": False},
            "limit": 10,
        },
        verbose=False,
    )

    assert df.to_dicts() == [
        {
            "stockCode": "000001",
            "finance.ratio.roe": 12.0,
            "valuation.pbr": 0.8,
            "krx.marketCap": 1000,
        }
    ]


def test_screen_spec_rejects_unknown_op(monkeypatch):
    """Unsupported operators fail with a field-specific message."""
    from dartlab.scan.builder import fields as scan_fields
    from dartlab.scan.screen import scanScreen

    monkeypatch.setattr(
        scan_fields,
        "_loadFieldValues",
        lambda field, spec: pl.DataFrame({"stockCode": ["000001"], field: [12.0]}),
    )

    with pytest.raises(ValueError, match="지원하지 않습니다"):
        scanScreen(
            spec={"where": [{"field": "finance.ratio.roe", "op": "startswith", "value": 10}]},
            verbose=False,
        )


def test_screen_spec_rejects_unit_mismatch():
    """Condition unit must match the catalog unit."""
    from dartlab.scan.screen import scanScreen

    with pytest.raises(ValueError, match="단위"):
        scanScreen(
            spec={"where": [{"field": "finance.ratio.roe", "op": ">", "value": 10, "unit": "원"}]},
            verbose=False,
        )


def test_screen_spec_rejects_missing_field():
    """Unknown fields point users back to scan('fields')."""
    from dartlab.scan.screen import scanScreen

    with pytest.raises(ValueError, match="scan\\('fields'\\)"):
        scanScreen(spec={"where": [{"field": "missing.field", "op": ">", "value": 1}]}, verbose=False)


def test_docs_condition_uses_search_hits(monkeypatch):
    """docs conditions summarize search index hits by stockCode."""
    import importlib

    search_mod = importlib.import_module("dartlab.providers.dart.search")
    from dartlab.scan.screen import scanScreen

    def fake_search(query, *, topK=10, scope="auto", **kwargs):
        return pl.DataFrame(
            {
                "stock_code": ["000001", "000001", "000002"],
                "score": [2.0, 1.0, 0.5],
                "text": ["HBM 투자", "HBM 증설", "기타"],
                "dartUrl": ["u1", "u2", "u3"],
            }
        )

    monkeypatch.setattr(search_mod, "search", fake_search)

    df = scanScreen(
        spec={"where": [{"field": "docs.content", "op": "contains", "value": "HBM"}], "limit": 5},
        verbose=False,
    )

    rows = sorted(df.to_dicts(), key=lambda row: row["stockCode"])
    assert rows[0]["stockCode"] == "000001"
    assert rows[0]["docsHitCount"] == 2
    assert rows[0]["docsBestScore"] == 2.0


def test_krx_index_is_select_context(monkeypatch):
    """krxIndex fields attach scalar market context and cannot filter stocks."""
    from dartlab.scan.builder import fields as scan_fields
    from dartlab.scan.screen import scanScreen

    monkeypatch.setattr(
        scan_fields,
        "_loadFieldValues",
        lambda field, spec: pl.DataFrame({"stockCode": ["000001"], field: [12.0]}),
    )
    monkeypatch.setattr(scan_fields, "_loadKrxIndexScalar", lambda field, spec: 3000.0)

    df = scanScreen(
        spec={
            "where": [{"field": "finance.ratio.roe", "op": ">", "value": 10}],
            "select": ["krxIndex.KOSPI.close"],
        },
        verbose=False,
    )

    assert df["krxIndex.KOSPI.close"].to_list() == [3000.0]

    with pytest.raises(ValueError, match="시장 컨텍스트"):
        scanScreen(
            spec={"where": [{"field": "krxIndex.KOSPI.close", "op": ">", "value": 3000}]},
            verbose=False,
        )
