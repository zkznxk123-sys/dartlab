"""KRX index gather contract."""

from __future__ import annotations

import polars as pl
import pytest

pytestmark = pytest.mark.unit


def test_dataReleaseHasKrxIndices():
    """KRX 지수 HF 카테고리는 가격과 별도 SSOT 를 가진다."""
    from dartlab.core.dataConfig import DATA_RELEASES

    assert DATA_RELEASES["krxIndices"]["dir"] == "krx/indices"
    assert DATA_RELEASES["krxIndices"]["public"] is True


def test_parseKrxIndexResponseAddsMarketGroup():
    """원본 idx 응답에 시장군 컬럼을 보강해 연도 parquet 에 섞어 저장한다."""
    from dartlab.gather.krxIndex import _parseKrxIndexResponse

    df = _parseKrxIndexResponse(
        {
            "OutBlock_1": [
                {
                    "BAS_DD": "20260428",
                    "IDX_CLSS": "KOSPI",
                    "IDX_NM": "코스피",
                    "CLSPRC_IDX": "6641.02",
                    "ACC_TRDVOL": "1",
                }
            ]
        },
        market="KOSPI",
        basDd="20260428",
    )

    assert df["MARKET_GROUP"].to_list() == ["KOSPI"]
    assert df["CLSPRC_IDX"].to_list() == [6641.02]
    assert df["ACC_TRDVOL"].to_list() == [1]


def test_gatherKrxIndexDefaultsToHf(monkeypatch):
    """apiKey 가 없으면 KRX API 가 아니라 HF raw parquet 경로를 사용한다."""
    import importlib

    hf = importlib.import_module("dartlab.gather._hfIndexBulk")
    from dartlab.gather.krxIndex import gatherKrxIndex

    raw = pl.DataFrame(
        [
            {
                "BAS_DD": "20260428",
                "MARKET_GROUP": "KOSPI",
                "IDX_CLSS": "KOSPI",
                "IDX_NM": "코스피",
                "CLSPRC_IDX": 6641.02,
                "OPNPRC_IDX": 6600.0,
                "HGPRC_IDX": 6650.0,
                "LWPRC_IDX": 6590.0,
                "ACC_TRDVOL": 1,
                "ACC_TRDVAL": 2,
                "MKTCAP": 3,
            }
        ]
    )

    monkeypatch.setattr(hf, "_loadYear", lambda year: raw)

    df = gatherKrxIndex("close", market="KOSPI", start="2026-04-28", end="2026-04-28")

    assert df.to_dicts() == [{"indexName": "코스피", "20260428": 6641.02}]
