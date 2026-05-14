"""providers/dart/openapi/saver.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.providers.dart.openapi.saver  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")


def test_enrich_finance_callable() -> None:
    """enrichFinance() callable smoke."""
    from dartlab.providers.dart.openapi.saver import enrichFinance

    assert callable(enrichFinance)


def test_enrich_report_callable() -> None:
    """enrichReport() callable smoke."""
    from dartlab.providers.dart.openapi.saver import enrichReport

    assert callable(enrichReport)


def test_kor_columns_callable() -> None:
    """korColumns() callable smoke."""
    from dartlab.providers.dart.openapi.saver import korColumns

    assert callable(korColumns)


def test_save_callable() -> None:
    """save() callable smoke."""
    from dartlab.providers.dart.openapi.saver import save

    assert callable(save)


def test_save_replacing_by_keys_preserves_unmatched_rows(tmp_path) -> None:
    """같은 논리 키만 교체하고 다른 기간/FS 데이터는 보존한다."""
    import polars as pl

    from dartlab.providers.dart.openapi.saver import saveReplacingByKeys

    path = tmp_path / "finance.parquet"
    pl.DataFrame(
        {
            "bsns_year": ["2025", "2025", "2024"],
            "reprt_code": ["11013", "11013", "11011"],
            "fs_div": ["CFS", "OFS", "CFS"],
            "rcept_no": ["old-cfs", "old-ofs", "old-annual"],
            "value": [1, 2, 3],
        }
    ).write_parquet(path)

    newDf = pl.DataFrame(
        {
            "bsns_year": ["2025"],
            "reprt_code": ["11013"],
            "fs_div": ["CFS"],
            "rcept_no": ["new-cfs"],
            "value": [10],
        }
    )

    saveReplacingByKeys(newDf, path, ["bsns_year", "reprt_code", "fs_div"])

    result = pl.read_parquet(path)
    rcepts = set(result["rcept_no"].to_list())
    assert "new-cfs" in rcepts
    assert "old-cfs" not in rcepts
    assert "old-ofs" in rcepts
    assert "old-annual" in rcepts
