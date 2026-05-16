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


def test_save_replacing_by_keys_materializes_legacy_finance_keys(tmp_path) -> None:
    """과거 finance 포맷의 reprt_nm/fs_nm 컬럼명도 키로 복원해 교체한다."""
    import polars as pl

    from dartlab.providers.dart.openapi.saver import saveReplacingByKeys

    path = tmp_path / "legacy-finance.parquet"
    pl.DataFrame(
        {
            "bsns_year": ["2025", "2025", "2024"],
            "reprt_nm": ["1분기", "1분기", "4분기"],
            "fs_nm": ["연결재무제표", "재무제표", "연결재무제표"],
            "collect_status": ["no_data", "no_data", "no_data"],
        }
    ).write_parquet(path)

    newDf = pl.DataFrame(
        {
            "bsns_year": ["2025"],
            "reprt_code": ["11013"],
            "fs_div": ["CFS"],
            "rcept_no": ["new-cfs"],
            "collect_status": ["collected"],
        }
    )

    saveReplacingByKeys(newDf, path, ["bsns_year", "reprt_code", "fs_div"])

    result = pl.read_parquet(path)
    rows = result.select("bsns_year", "reprt_code", "fs_div", "collect_status").to_dicts()
    assert {
        "bsns_year": "2025",
        "reprt_code": "11013",
        "fs_div": "CFS",
        "collect_status": "no_data",
    } not in rows
    assert {
        "bsns_year": "2025",
        "reprt_code": "11013",
        "fs_div": "OFS",
        "collect_status": "no_data",
    } in rows
    assert "new-cfs" in set(result["rcept_no"].drop_nulls().to_list())


def test_save_replacing_by_keys_preserves_existing_null_key_rows(tmp_path) -> None:
    """기존 parquet 에 키 컬럼이 null 인 legacy row 가 있어도 raise 없이 보존한다.

    근본 회귀 (2026-05-14 Data Sync 실패): existing-side validation 이 null row
    1 개만 있어도 fatal 로 격상돼 한국 종목 전수 sync 가 차단됐다.
    """
    import polars as pl

    from dartlab.providers.dart.openapi.saver import saveReplacingByKeys

    path = tmp_path / "finance.parquet"
    pl.DataFrame(
        {
            "bsns_year": ["2025", "2024", None],
            "reprt_code": ["11013", "11011", "11011"],
            "fs_div": ["CFS", None, "CFS"],
            "rcept_no": ["old-q1", "old-annual-null-fs", "old-null-year"],
            "value": [1, 2, 3],
        }
    ).write_parquet(path)

    newDf = pl.DataFrame(
        {
            "bsns_year": ["2025"],
            "reprt_code": ["11013"],
            "fs_div": ["CFS"],
            "rcept_no": ["new-q1"],
            "value": [10],
        }
    )

    saveReplacingByKeys(newDf, path, ["bsns_year", "reprt_code", "fs_div"])

    result = pl.read_parquet(path)
    rcepts = set(result["rcept_no"].to_list())
    assert "new-q1" in rcepts
    assert "old-q1" not in rcepts
    assert "old-annual-null-fs" in rcepts
    assert "old-null-year" in rcepts


def test_save_replacing_by_keys_rejects_new_null_key_rows(tmp_path) -> None:
    """새로 들어오는 row 의 키가 null 이면 여전히 raise — 데이터 오염 차단."""
    import polars as pl
    import pytest

    from dartlab.providers.dart.openapi.saver import saveReplacingByKeys

    path = tmp_path / "finance.parquet"
    pl.DataFrame(
        {
            "bsns_year": ["2025"],
            "reprt_code": ["11013"],
            "fs_div": ["CFS"],
            "rcept_no": ["old"],
        }
    ).write_parquet(path)

    newDf = pl.DataFrame(
        {
            "bsns_year": ["2025", None],
            "reprt_code": ["11013", "11013"],
            "fs_div": ["CFS", "CFS"],
            "rcept_no": ["new-ok", "new-bad"],
        }
    )

    with pytest.raises(ValueError, match="null new key values"):
        saveReplacingByKeys(newDf, path, ["bsns_year", "reprt_code", "fs_div"])


def test_save_replacing_by_keys_rejects_unknown_existing_key_columns(tmp_path) -> None:
    """복원 불가능한 키 컬럼이면 append fallback 없이 실패해야 한다."""
    import polars as pl
    import pytest

    from dartlab.providers.dart.openapi.saver import saveReplacingByKeys

    path = tmp_path / "bad-legacy.parquet"
    pl.DataFrame({"bsns_year": ["2025"], "collect_status": ["no_data"]}).write_parquet(path)

    newDf = pl.DataFrame(
        {
            "bsns_year": ["2025"],
            "reprt_code": ["11013"],
            "fs_div": ["CFS"],
            "rcept_no": ["new-cfs"],
        }
    )

    with pytest.raises(ValueError, match="existing key columns"):
        saveReplacingByKeys(newDf, path, ["bsns_year", "reprt_code", "fs_div"])
