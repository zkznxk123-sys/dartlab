"""dartlab.gather.domains.naver mirror 슬롯 — smoke import (P-G7.2).

룰 7 (src↔tests 1:1 mirror) 만족용 placeholder. 본격 단위 테스트는 후속.
"""

from __future__ import annotations

import asyncio
import importlib
from datetime import date, timedelta

import pytest

pytestmark = pytest.mark.unit


def test_smoke_import() -> None:
    """``dartlab.gather.domains.naver`` 모듈 import 가능 — 모듈 구조 회귀 차단."""
    importlib.import_module("dartlab.gather.domains.naver")


def test_fetch_flow_trend_paginates_by_bizdate() -> None:
    """Naver front-api flow 는 end+1 cursor 로 시작해 start 전에서 멈춘다."""
    from dartlab.gather.domains import naver

    class FakeResponse:
        def __init__(self, rows):
            self._rows = rows

        def json(self):
            return {"isSuccess": True, "result": self._rows}

    class FakeClient:
        def __init__(self):
            self.calls = []

        async def get(self, url, **kwargs):
            params = kwargs.get("params") or {}
            self.calls.append((url, params))
            cursor = params.get("bizdate")
            if cursor == "20200201":
                return FakeResponse(
                    [
                        {
                            "bizdate": "20200131",
                            "foreignerPureBuyQuant": "-3,776,715",
                            "foreignerHoldRatio": "57.19%",
                            "organPureBuyQuant": "+1,648,681",
                            "individualPureBuyQuant": "+2,215,461",
                        },
                        {
                            "bizdate": "20200130",
                            "foreignerPureBuyQuant": "+10",
                            "foreignerHoldRatio": "57.10%",
                            "organPureBuyQuant": "-20",
                            "individualPureBuyQuant": "+10",
                        },
                    ]
                )
            if cursor == "20200130":
                return FakeResponse(
                    [
                        {
                            "bizdate": "20200129",
                            "foreignerPureBuyQuant": "+30",
                            "foreignerHoldRatio": "57.00%",
                            "organPureBuyQuant": "-40",
                            "individualPureBuyQuant": "+10",
                        },
                        {
                            "bizdate": "20200128",
                            "foreignerPureBuyQuant": "+50",
                            "foreignerHoldRatio": "56.90%",
                            "organPureBuyQuant": "-60",
                            "individualPureBuyQuant": "+10",
                        },
                    ]
                )
            return FakeResponse([])

    client = FakeClient()
    rows = asyncio.run(
        naver.fetchFlow(
            "005930",
            client,
            start="2020-01-29",
            end="2020-01-31",
            pageSize=2,
        )
    )

    assert [row["date"] for row in rows] == ["20200131", "20200130", "20200129"]
    assert rows[0]["foreignNet"] == -3776715.0
    assert client.calls[0][0] == naver._FLOW_TREND_URL
    assert client.calls[0][1]["bizdate"] == "20200201"
    assert client.calls[0][1]["pageSize"] == 2


def test_fetch_flow_trend_auto_pages_historical_range() -> None:
    """기간 조회는 pageSize 입력 없이 Naver 최대 단위로 자동 조회한다."""
    from dartlab.gather.domains import naver

    class FakeResponse:
        def json(self):
            return {
                "isSuccess": True,
                "result": [
                    {
                        "bizdate": "20200131",
                        "foreignerPureBuyQuant": "1",
                        "foreignerHoldRatio": "57.19%",
                        "organPureBuyQuant": "2",
                        "individualPureBuyQuant": "-3",
                    },
                    {
                        "bizdate": "20200130",
                        "foreignerPureBuyQuant": "4",
                        "foreignerHoldRatio": "57.10%",
                        "organPureBuyQuant": "5",
                        "individualPureBuyQuant": "-9",
                    },
                ],
            }

    class FakeClient:
        def __init__(self):
            self.calls = []

        async def get(self, url, **kwargs):
            self.calls.append((url, kwargs.get("params") or {}))
            return FakeResponse()

    client = FakeClient()
    rows = asyncio.run(
        naver.fetchFlow(
            "005930",
            client,
            start="2020-01-30",
            end="2020-01-31",
        )
    )

    assert [row["date"] for row in rows] == ["20200131", "20200130"]
    assert client.calls[0][1]["bizdate"] == "20200201"
    assert client.calls[0][1]["pageSize"] == 50


def test_fetch_flow_default_latest_stays_small() -> None:
    """기본 최신 조회는 사용자 실수로 장기 백필하지 않도록 5건만 요청한다."""
    from dartlab.gather.domains import naver

    class FakeResponse:
        def json(self):
            return {
                "isSuccess": True,
                "result": [
                    {
                        "bizdate": f"202606{i:02d}",
                        "foreignerPureBuyQuant": "1",
                        "foreignerHoldRatio": "50.00%",
                        "organPureBuyQuant": "0",
                        "individualPureBuyQuant": "0",
                    }
                    for i in range(10, 5, -1)
                ],
            }

    class FakeClient:
        def __init__(self):
            self.calls = []

        async def get(self, url, **kwargs):
            self.calls.append((url, kwargs.get("params") or {}))
            return FakeResponse()

    client = FakeClient()
    rows = asyncio.run(naver.fetchFlow("005930", client))

    assert len(rows) == 5
    assert len(client.calls) == 1
    assert client.calls[0][1]["pageSize"] == 5


def test_fetch_flow_trend_passes_proxy_to_http_client() -> None:
    """proxy 옵션은 Naver trend HTTP 호출로 전달한다."""
    from dartlab.gather.domains import naver

    class FakeResponse:
        def json(self):
            return {
                "isSuccess": True,
                "result": [
                    {
                        "bizdate": "20260611",
                        "foreignerPureBuyQuant": "1",
                        "foreignerHoldRatio": "50.00%",
                        "organPureBuyQuant": "0",
                        "individualPureBuyQuant": "0",
                    }
                ],
            }

    class FakeClient:
        def __init__(self):
            self.calls = []

        async def get(self, url, **kwargs):
            self.calls.append((url, kwargs))
            return FakeResponse()

    client = FakeClient()
    rows = asyncio.run(naver.fetchFlow("005930", client, proxy="http://proxy.example:8080"))

    assert len(rows) == 1
    assert client.calls[0][1]["proxy"] == "http://proxy.example:8080"


def test_fetch_flow_trend_large_page_size_splits_to_server_cap() -> None:
    """큰 pageSize 요청은 서버 한도 50건 단위로 나눠 최신 N건을 채운다."""
    from dartlab.gather.domains import naver

    def make_rows(offset: int, count: int):
        base = date(2026, 6, 10) - timedelta(days=offset)
        return [
            {
                "bizdate": (base - timedelta(days=i)).strftime("%Y%m%d"),
                "foreignerPureBuyQuant": str(offset + i),
                "foreignerHoldRatio": "50.00%",
                "organPureBuyQuant": "0",
                "individualPureBuyQuant": "0",
            }
            for i in range(count)
        ]

    class FakeResponse:
        def __init__(self, rows):
            self._rows = rows

        def json(self):
            return {"isSuccess": True, "result": self._rows}

    class FakeClient:
        def __init__(self):
            self.calls = []

        async def get(self, url, **kwargs):
            params = kwargs.get("params") or {}
            self.calls.append((url, params))
            return FakeResponse(make_rows(0 if len(self.calls) == 1 else 50, 50))

    client = FakeClient()
    rows = asyncio.run(naver.fetchFlow("005930", client, pageSize=75))

    assert len(rows) == 75
    assert len(client.calls) == 2
    assert [call[1]["pageSize"] for call in client.calls] == [50, 50]


def test_fetch_flow_all_history_runs_until_source_exhausted() -> None:
    """all=True 는 limit 없이 서버가 빈 페이지를 줄 때까지 자동 순회한다."""
    from dartlab.gather.domains import naver

    def make_rows(offset: int, count: int):
        base = date(2026, 6, 10) - timedelta(days=offset)
        return [
            {
                "bizdate": (base - timedelta(days=i)).strftime("%Y%m%d"),
                "foreignerPureBuyQuant": str(offset + i),
                "foreignerHoldRatio": "50.00%",
                "organPureBuyQuant": "0",
                "individualPureBuyQuant": "0",
            }
            for i in range(count)
        ]

    class FakeResponse:
        def __init__(self, rows):
            self._rows = rows

        def json(self):
            return {"isSuccess": True, "result": self._rows}

    class FakeClient:
        def __init__(self):
            self.calls = []

        async def get(self, url, **kwargs):
            params = kwargs.get("params") or {}
            self.calls.append((url, params))
            idx = len(self.calls)
            if idx == 1:
                return FakeResponse(make_rows(0, 50))
            if idx == 2:
                return FakeResponse(make_rows(50, 50))
            return FakeResponse(make_rows(100, 10))

    client = FakeClient()
    rows = asyncio.run(naver.fetchFlow("005930", client, full=True))

    assert len(rows) == 110
    assert len(client.calls) == 3
    assert [call[1]["pageSize"] for call in client.calls] == [50, 50, 50]
