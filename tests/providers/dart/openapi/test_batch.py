"""providers/dart/openapi/batch.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.providers.dart.openapi.batch  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")


def test_close_callable() -> None:
    """close() callable smoke."""
    from dartlab.providers.dart.openapi.batch import AsyncDartClient

    assert hasattr(AsyncDartClient, "close")


def test_get_bytes_callable() -> None:
    """getBytes() callable smoke."""
    from dartlab.providers.dart.openapi.batch import AsyncDartClient

    assert hasattr(AsyncDartClient, "getBytes")


def test_get_df_callable() -> None:
    """getDf() callable smoke."""
    from dartlab.providers.dart.openapi.batch import AsyncDartClient

    assert hasattr(AsyncDartClient, "getDf")


def test_get_json_callable() -> None:
    """getJson() callable smoke."""
    from dartlab.providers.dart.openapi.batch import AsyncDartClient

    assert hasattr(AsyncDartClient, "getJson")


def test_batch_collect_callable() -> None:
    """batchCollect() callable smoke."""
    from dartlab.providers.dart.openapi.batch import batchCollect

    assert callable(batchCollect)


def test_batch_collect_all_callable() -> None:
    """batchCollectAll() callable smoke."""
    from dartlab.providers.dart.openapi.batch import batchCollectAll

    assert callable(batchCollectAll)


def test_collect_finance_target_period_refreshes_existing_period(tmp_path, monkeypatch) -> None:
    """targetPeriods는 정정 공시 반영을 위해 기존 period도 다시 수집한다."""
    import asyncio

    import polars as pl

    import dartlab
    from dartlab.providers.dart.openapi.batch import _collectFinance

    monkeypatch.setattr(dartlab.config, "dataDir", str(tmp_path))
    financePath = tmp_path / "dart" / "finance" / "005930.parquet"
    financePath.parent.mkdir(parents=True)
    pl.DataFrame(
        {
            "bsns_year": ["2025", "2025", "2024"],
            "reprt_code": ["11013", "11013", "11011"],
            "fs_div": ["CFS", "OFS", "CFS"],
            "rcept_no": ["old-cfs", "old-ofs", "old-annual"],
            "account_nm": ["매출액", "매출액", "매출액"],
        }
    ).write_parquet(financePath)

    class FakeClient:
        exhausted = False

        async def getDf(self, endpoint, params, listKey="list"):
            if params["fs_div"] != "CFS":
                return pl.DataFrame()
            return pl.DataFrame(
                {
                    "corp_code": [params["corp_code"]],
                    "bsns_year": [params["bsns_year"]],
                    "reprt_code": [params["reprt_code"]],
                    "fs_div": [params["fs_div"]],
                    "rcept_no": ["new-cfs"],
                    "account_nm": ["매출액"],
                }
            )

    count = asyncio.run(
        _collectFinance(
            "005930",
            "00126380",
            "삼성전자",
            FakeClient(),
            incremental=True,
            targetPeriods=[("2025", "11013")],
        )
    )

    assert count == 1
    result = pl.read_parquet(financePath)
    rcepts = set(result["rcept_no"].to_list())
    assert "new-cfs" in rcepts
    assert "old-cfs" not in rcepts
    assert "old-ofs" in rcepts
    assert "old-annual" in rcepts


def test_collect_report_target_period_refreshes_existing_api_type(tmp_path, monkeypatch) -> None:
    """report 정정 재수집은 같은 apiType/기간만 교체한다."""
    import asyncio

    import polars as pl

    import dartlab
    from dartlab.providers.dart.openapi.batch import _collectReport

    monkeypatch.setattr(dartlab.config, "dataDir", str(tmp_path))
    reportPath = tmp_path / "dart" / "report" / "005930.parquet"
    reportPath.parent.mkdir(parents=True)
    pl.DataFrame(
        {
            "year": ["2025", "2025", "2024"],
            "quarter": ["1분기", "1분기", "4분기"],
            "apiType": ["dividend", "employee", "dividend"],
            "rcept_no": ["old-dividend", "old-employee", "old-annual"],
            "stockCode": ["005930", "005930", "005930"],
        }
    ).write_parquet(reportPath)

    class FakeClient:
        exhausted = False

        async def getDf(self, endpoint, params, listKey="list"):
            if endpoint != "alotMatter.json":
                return pl.DataFrame()
            return pl.DataFrame(
                {
                    "corp_code": [params["corp_code"]],
                    "bsns_year": [params["bsns_year"]],
                    "reprt_code": [params["reprt_code"]],
                    "rcept_no": ["new-dividend"],
                }
            )

    count = asyncio.run(
        _collectReport(
            "005930",
            "00126380",
            "삼성전자",
            FakeClient(),
            incremental=True,
            targetPeriods=[("2025", "11013")],
        )
    )

    assert count == 1
    result = pl.read_parquet(reportPath)
    rcepts = set(result["rcept_no"].to_list())
    assert "new-dividend" in rcepts
    assert "old-dividend" not in rcepts
    assert "old-employee" in rcepts
    assert "old-annual" in rcepts
