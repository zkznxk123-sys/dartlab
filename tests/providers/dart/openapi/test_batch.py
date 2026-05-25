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


def test_get_json_retries_transient_read_error(monkeypatch) -> None:
    """DART ReadError는 같은 요청 단위에서 재시도한다."""
    import asyncio

    import httpx

    from dartlab.providers.dart.openapi import batch
    from dartlab.providers.dart.openapi.batch import AsyncDartClient

    class FakeResponse:
        status_code = 200

        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return {"status": "000", "list": [{"ok": True}]}

    class FakeAsyncClient:
        def __init__(self, *args, **kwargs) -> None:
            self.calls = 0

        async def get(self, *args, **kwargs):
            self.calls += 1
            if self.calls == 1:
                raise httpx.ReadError("server closed connection")
            return FakeResponse()

        async def aclose(self) -> None:
            return None

    fakeClient = FakeAsyncClient()
    monkeypatch.setattr(batch.httpx, "AsyncClient", lambda *args, **kwargs: fakeClient)

    client = AsyncDartClient("key", maxRetries=1, retryBaseDelay=0)
    result = asyncio.run(client.getJson("list.json", {"corp_code": "00126380"}))

    assert result == {"status": "000", "list": [{"ok": True}]}
    assert fakeClient.calls == 2


def test_batch_collect_callable() -> None:
    """batchCollect() callable smoke."""
    from dartlab.providers.dart.openapi.batch import batchCollect

    assert callable(batchCollect)


def test_batch_collect_all_callable() -> None:
    """batchCollectAll() callable smoke."""
    from dartlab.providers.dart.openapi.batch import batchCollectAll

    assert callable(batchCollectAll)


def test_batch_collect_invokes_on_checkpoint_per_n_stocks(monkeypatch) -> None:
    """batchCollect 가 N 종목마다 onCheckpoint 콜백 호출 + 종료 직전 final flush.

    cancel/timeout 안전망 검증 — 90 분 timeout 사고 (2026-05-16) 의 root cause fix.
    """
    from dartlab.providers.dart.openapi import batch

    monkeypatch.setattr(batch, "_resolveCorpMap", lambda codes: {c: ("", c) for c in codes})
    monkeypatch.setattr(batch, "resolveDartKeys", lambda: ["fake-key"])

    class _FakeClient:
        exhausted = False

        def __init__(self, *args, **kwargs) -> None:
            pass

        async def close(self) -> None:
            return None

        async def getDf(self, *args, **kwargs):
            return None

    monkeypatch.setattr(batch, "AsyncDartClient", _FakeClient)

    async def _zero(*args, **kwargs):
        return 0

    monkeypatch.setattr(batch, "_collectFinance", _zero)
    monkeypatch.setattr(batch, "_collectReport", _zero)
    monkeypatch.setattr(batch, "_collectDocs", _zero)

    calls: list[list[str]] = []

    def _cb(codes: list[str]) -> None:
        calls.append(list(codes))

    batch.batchCollect(
        ["A", "B", "C", "D", "E", "F", "G"],
        categories=["finance"],
        showProgress=False,
        onCheckpoint=_cb,
        checkpointEvery=3,
    )

    flat = [code for chunk in calls for code in chunk]
    # 7 종목 / every 3 → drain at 3, drain at 6, final flush 1 종목.
    assert set(flat) == {"A", "B", "C", "D", "E", "F", "G"}
    # final flush 가 비어있지 않은 잔여를 호출 — 최소 1 회 호출.
    assert len(calls) >= 1
    # 어떤 chunk 도 checkpointEvery 초과하지 않음.
    assert all(len(chunk) <= 3 for chunk in calls)


def test_batch_collect_skips_checkpoint_when_disabled(monkeypatch) -> None:
    """checkpointEvery=0 (default) 면 콜백 자체가 호출되지 않는다 — 기존 호출자 호환."""
    from dartlab.providers.dart.openapi import batch

    monkeypatch.setattr(batch, "_resolveCorpMap", lambda codes: {c: ("", c) for c in codes})
    monkeypatch.setattr(batch, "resolveDartKeys", lambda: ["fake-key"])

    class _FakeClient:
        exhausted = False

        def __init__(self, *args, **kwargs) -> None:
            pass

        async def close(self) -> None:
            return None

        async def getDf(self, *args, **kwargs):
            return None

    monkeypatch.setattr(batch, "AsyncDartClient", _FakeClient)

    async def _zero(*args, **kwargs):
        return 0

    monkeypatch.setattr(batch, "_collectFinance", _zero)
    monkeypatch.setattr(batch, "_collectReport", _zero)
    monkeypatch.setattr(batch, "_collectDocs", _zero)

    invoked = {"n": 0}

    def _cb(_codes):
        invoked["n"] += 1

    batch.batchCollect(
        ["A", "B"],
        categories=["finance"],
        showProgress=False,
        onCheckpoint=_cb,  # callback 줘도
        checkpointEvery=0,  # every=0 이면 비활성
    )

    assert invoked["n"] == 0


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
