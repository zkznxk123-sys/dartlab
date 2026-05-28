"""dartlab.gather.infra.sdmxClient 단위 테스트.

SDMX-JSON 파싱 + 미등록 provider 에러 + period 포맷 4 종.
실제 네트워크 호출 없음 (mock payload).
"""

from __future__ import annotations

import importlib

import polars as pl
import pytest

from dartlab.gather.infra.sdmxClient import (
    PROVIDER_ENDPOINTS,
    SdmxClient,
    SdmxClientError,
    _parseSdmxJson,
)

pytestmark = pytest.mark.unit


def test_smoke_import() -> None:
    """모듈 import 회귀 차단."""
    importlib.import_module("dartlab.gather.infra.sdmxClient")


def test_PROVIDER_ENDPOINTS_4_providers() -> None:
    """4 provider 모두 등록."""
    assert set(PROVIDER_ENDPOINTS) == {"ECB", "BIS", "OECD", "IMF"}
    for ep in PROVIDER_ENDPOINTS.values():
        assert ep.base_url.startswith("https://")
        assert "sdmx" in ep.accept_header.lower()


def test_fetch_unregistered_provider_raises() -> None:
    """미등록 provider → SdmxClientError."""
    client = SdmxClient()
    try:
        with pytest.raises(SdmxClientError, match="미등록"):
            client.fetch("BLOOMBERG", "BSI", "key")
    finally:
        client.close()


def test_parseSdmxJson_empty_series() -> None:
    """빈 series → 빈 DataFrame (schema 보존)."""
    payload = {"dataSets": [{"series": {}}], "structure": {"dimensions": {"observation": []}}}
    df = _parseSdmxJson(payload)
    assert df.is_empty()
    assert df.schema == {"date": pl.Date, "value": pl.Float64}


def test_parseSdmxJson_missing_dataSets_raises() -> None:
    """dataSets 누락 → SdmxClientError."""
    with pytest.raises(SdmxClientError, match="dataSets"):
        _parseSdmxJson({"structure": {}})


def test_parseSdmxJson_missing_structure_raises() -> None:
    """structure 누락 → SdmxClientError."""
    with pytest.raises(SdmxClientError, match="structure"):
        _parseSdmxJson({"dataSets": [{"series": {"0:0": {"observations": {}}}}]})


def test_parseSdmxJson_monthly_observations() -> None:
    """월간 시계열 (YYYY-MM) 정상 파싱."""
    payload = {
        "dataSets": [
            {
                "series": {
                    "0:0:0": {
                        "observations": {
                            "0": [100.5],
                            "1": [101.2],
                            "2": [99.8],
                        }
                    }
                }
            }
        ],
        "structure": {
            "dimensions": {
                "observation": [
                    {
                        "id": "TIME_PERIOD",
                        "values": [
                            {"id": "2024-01"},
                            {"id": "2024-02"},
                            {"id": "2024-03"},
                        ],
                    }
                ]
            }
        },
    }
    df = _parseSdmxJson(payload)
    assert df.height == 3
    assert df["value"].to_list() == [100.5, 101.2, 99.8]
    assert df["date"].to_list()[0].isoformat() == "2024-01-01"
    assert df["date"].to_list()[2].isoformat() == "2024-03-01"


def test_parseSdmxJson_annual_observations() -> None:
    """연간 시계열 (YYYY) → YYYY-01-01."""
    payload = {
        "dataSets": [
            {
                "series": {
                    "0:0": {
                        "observations": {
                            "0": [50.0],
                            "1": [55.0],
                        }
                    }
                }
            }
        ],
        "structure": {"dimensions": {"observation": [{"values": [{"id": "2020"}, {"id": "2021"}]}]}},
    }
    df = _parseSdmxJson(payload)
    assert df.height == 2
    assert df["date"].to_list()[0].isoformat() == "2020-01-01"
    assert df["date"].to_list()[1].isoformat() == "2021-01-01"


def test_parseSdmxJson_quarterly_observations() -> None:
    """분기 시계열 (YYYY-Q1) → 분기 시작월."""
    payload = {
        "dataSets": [
            {
                "series": {
                    "0:0": {
                        "observations": {
                            "0": [10.0],
                            "1": [20.0],
                            "2": [30.0],
                            "3": [40.0],
                        }
                    }
                }
            }
        ],
        "structure": {
            "dimensions": {
                "observation": [
                    {
                        "values": [
                            {"id": "2024-Q1"},
                            {"id": "2024-Q2"},
                            {"id": "2024-Q3"},
                            {"id": "2024-Q4"},
                        ]
                    }
                ]
            }
        },
    }
    df = _parseSdmxJson(payload)
    assert df.height == 4
    dates = [d.isoformat() for d in df["date"].to_list()]
    assert dates == ["2024-01-01", "2024-04-01", "2024-07-01", "2024-10-01"]


def test_parseSdmxJson_null_value_preserved() -> None:
    """null 관측값 → pl.Float64 None 보존."""
    payload = {
        "dataSets": [
            {
                "series": {
                    "0": {
                        "observations": {
                            "0": [100.0],
                            "1": [None],
                            "2": [102.0],
                        }
                    }
                }
            }
        ],
        "structure": {
            "dimensions": {"observation": [{"values": [{"id": "2024-01"}, {"id": "2024-02"}, {"id": "2024-03"}]}]}
        },
    }
    df = _parseSdmxJson(payload)
    assert df.height == 3
    values = df["value"].to_list()
    assert values[0] == 100.0
    assert values[1] is None
    assert values[2] == 102.0
