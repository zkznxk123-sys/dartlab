"""quant KRX index benchmark contract."""

from __future__ import annotations

import math
from datetime import date, timedelta

import numpy as np
import polars as pl
import pytest

pytestmark = pytest.mark.unit


def _krx_listing() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "short_code": ["005930", "247540"],
            "marketCode": ["STK", "KSQ"],
            "marketEngName": ["KOSPI", "KOSDAQ GLOBAL"],
        }
    )


def test_resolve_benchmark_uses_listing_market(monkeypatch):
    """KOSPI/KOSDAQ 종목은 상장시장 기준 기본 지수를 사용한다."""
    from dartlab.gather.krx import listing
    from dartlab.quant.benchmark.data import resolveBenchmark

    monkeypatch.setattr(listing, "getKrxList", lambda: _krx_listing())

    kospi = resolveBenchmark("005930", market="KR")
    kosdaq = resolveBenchmark("247540", market="KR")

    assert kospi["source"] == "krxIndex"
    assert kospi["indexMarket"] == "KOSPI"
    assert kospi["indexName"] == "코스피"
    assert kosdaq["indexMarket"] == "KOSDAQ"
    assert kosdaq["indexName"] == "코스닥"


def test_resolve_benchmark_stack_adds_sector_candidate(monkeypatch):
    """industry node가 있으면 benchmarkStack에 섹터 지수 후보를 추가한다."""
    from dartlab.gather.krx import listing
    from dartlab.quant import benchmark as bm

    monkeypatch.setattr(listing, "getKrxList", lambda: _krx_listing())
    monkeypatch.setattr(
        "dartlab.synth.benchmarkData.primaryIndustryNode",
        lambda _: {"industry": "semiconductor", "confidence": 0.9, "source": "test"},
    )
    monkeypatch.setattr("dartlab.synth.benchmarkData.indexExists", lambda *_: True)

    stack = bm.resolveBenchmarkStack("005930", market="KR", benchmarkMode="sector")
    resolved = bm.resolveBenchmark("005930", market="KR", benchmarkMode="sector")

    assert stack["market"]["indexName"] == "코스피"
    assert stack["sector"]["indexName"] == "KRX 반도체"
    assert stack["primary"]["benchmarkType"] == "sector"
    assert resolved["indexName"] == "KRX 반도체"
    assert resolved["benchmarkStack"]["sector"]["industry"] == "semiconductor"


def test_resolve_benchmark_stack_explicit_override_wins(monkeypatch):
    """benchmark 직접 지정은 market/sector/style보다 우선한다."""
    from dartlab.gather.krx import listing
    from dartlab.quant import benchmark as bm

    monkeypatch.setattr(listing, "getKrxList", lambda: _krx_listing())
    monkeypatch.setattr(
        "dartlab.synth.benchmarkData.primaryIndustryNode",
        lambda _: {"industry": "semiconductor", "confidence": 0.9, "source": "test"},
    )

    resolved = bm.resolveBenchmark("005930", market="KR", benchmark="코스피 200", benchmarkMode="sector")

    assert resolved["benchmarkType"] == "explicit"
    assert resolved["indexMarket"] == "KOSPI"
    assert resolved["indexName"] == "코스피 200"


def test_resolve_benchmark_stack_sector_fallbacks_to_market(monkeypatch):
    """섹터 후보가 없으면 primary는 시장 지수로 fallback한다."""
    from dartlab.gather.krx import listing
    from dartlab.quant import benchmark as bm

    monkeypatch.setattr(listing, "getKrxList", lambda: _krx_listing())
    monkeypatch.setattr("dartlab.synth.benchmarkData.primaryIndustryNode", lambda _: None)
    monkeypatch.setattr("dartlab.synth.benchmarkData._latestSectorCandidate", lambda *_: None)

    resolved = bm.resolveBenchmark("005930", market="KR", benchmarkMode="sector")

    assert resolved["benchmarkType"] == "market"
    assert resolved["indexName"] == "코스피"
    assert resolved["fallbackReason"] == "sector_benchmark_unavailable"


def test_resolve_benchmark_stack_adds_size_style_candidate(monkeypatch):
    """시총 분위로 코스피/코스닥 대형·중형·소형 스타일 지수를 만든다."""
    import importlib

    hf = importlib.import_module("dartlab.gather.bulkData.hfBulk")
    from dartlab.gather.krx import listing
    from dartlab.quant import benchmark as bm

    rows = []
    for i, cap in enumerate([500, 400, 300, 200, 100]):
        code = "005930" if i == 0 else f"00000{i}"
        rows.append(
            {
                "BAS_DD": "20260428",
                "ISU_CD": code,
                "MKT_NM": "KOSPI",
                "SECT_TP_NM": "전기전자",
                "MKTCAP": cap,
            }
        )

    monkeypatch.setattr(listing, "getKrxList", lambda: _krx_listing())
    monkeypatch.setattr(hf, "loadFiltered", lambda **_: pl.DataFrame(rows))
    monkeypatch.setattr("dartlab.synth.benchmarkData.primaryIndustryNode", lambda _: None)
    monkeypatch.setattr("dartlab.synth.benchmarkData.indexExists", lambda *_: True)

    resolved = bm.resolveBenchmark("005930", market="KR", benchmarkMode="style")

    assert resolved["benchmarkType"] == "style"
    assert resolved["indexName"] == "코스피 대형주"
    assert resolved["styleBucket"] == "large"
    assert resolved["benchmarkStack"]["style"]["marketCapRank"] == 1


def test_sector_map_targets_existing_local_krx_indices():
    """매핑된 지수명은 로컬 KRX index catalog에 존재해야 한다."""
    from dartlab.quant.benchmark.map import SECTOR_INDEX_MAP, availableIndexNames

    names = availableIndexNames()
    if not names:
        pytest.skip("로컬 krxIndex catalog 없음")

    missing = []
    for industryId, rows in SECTOR_INDEX_MAP.items():
        for indexMarket, indexName, _confidence in rows:
            if (indexMarket, indexName) not in names:
                missing.append((industryId, indexMarket, indexName))

    assert missing == []


def test_fetch_benchmark_ohlcv_standardizes_krx_raw(monkeypatch):
    """KRX raw YYYYMMDD 지수 row를 quant OHLCV schema로 변환한다."""
    import importlib

    hf = importlib.import_module("dartlab.gather.bulkData.hfIndexBulk")
    from dartlab.gather.krx import listing
    from dartlab.quant.benchmark.data import fetchBenchmarkOhlcv

    raw = pl.DataFrame(
        [
            {
                "BAS_DD": "20260427",
                "MARKET_GROUP": "KOSPI",
                "IDX_NM": "코스피",
                "OPNPRC_IDX": 100.0,
                "HGPRC_IDX": 101.0,
                "LWPRC_IDX": 99.0,
                "CLSPRC_IDX": 100.5,
                "ACC_TRDVOL": 10,
                "ACC_TRDVAL": 20,
                "MKTCAP": 30,
            }
        ]
    )
    monkeypatch.setattr(listing, "getKrxList", lambda: _krx_listing())
    monkeypatch.setattr(hf, "loadFiltered", lambda **_: raw)

    df, meta = fetchBenchmarkOhlcv("005930", market="KR", returnMeta=True)

    assert meta["indexName"] == "코스피"
    assert meta["nObs"] == 1
    assert df.columns == ["date", "open", "high", "low", "close", "volume", "amount", "marketCap"]
    assert df["date"][0] == date(2026, 4, 27)
    assert df["close"][0] == 100.5


def test_quant_benchmark_axis_dispatch(monkeypatch):
    """quant('benchmark') 축은 벤치마크 요약 dict를 반환한다."""
    import importlib

    hf = importlib.import_module("dartlab.gather.bulkData.hfIndexBulk")
    from dartlab.gather.krx import listing
    from dartlab.quant import Quant

    rows = []
    start = date(2025, 1, 1)
    for i in range(260):
        d = start + timedelta(days=i)
        rows.append(
            {
                "BAS_DD": d.strftime("%Y%m%d"),
                "MARKET_GROUP": "KOSPI",
                "IDX_NM": "코스피",
                "OPNPRC_IDX": 100.0 + i,
                "HGPRC_IDX": 101.0 + i,
                "LWPRC_IDX": 99.0 + i,
                "CLSPRC_IDX": 100.0 + i,
                "ACC_TRDVOL": 10,
                "ACC_TRDVAL": 20,
                "MKTCAP": 30,
            }
        )

    monkeypatch.setattr(listing, "getKrxList", lambda: _krx_listing())
    monkeypatch.setattr(hf, "loadFiltered", lambda **_: pl.DataFrame(rows))

    result = Quant()("benchmark", "005930")

    assert result["benchmarkUsed"]["indexName"] == "코스피"
    assert result["latestClose"] == 359.0
    assert result["return1m"] is not None


def test_bab_ranks_by_beta_not_vol(monkeypatch):
    """BAB 기본 topLow/topHigh는 realized vol이 아니라 beta 기준이다."""
    import importlib

    hf = importlib.import_module("dartlab.gather.bulkData.hfBulk")
    from dartlab.quant.alphas.bab import calcBAB

    start = date(2025, 1, 1)
    dates = [start + timedelta(days=i) for i in range(270)]
    benchRet = 0.001 + np.sin(np.arange(len(dates) - 1) / 7.0) * 0.002
    bench_price = 100 * np.exp(np.r_[0.0, np.cumsum(benchRet)])

    def stock_prices(beta: float, noise_amp: float) -> np.ndarray:
        noise = np.sin(np.arange(len(benchRet))) * noise_amp
        ret = beta * benchRet + noise
        return 100 * np.exp(np.r_[0.0, np.cumsum(ret)])

    panel = {
        "LOWB": stock_prices(0.4, 0.0001),
        "HIGHB": stock_prices(1.8, 0.0001),
        "MIDB": stock_prices(1.0, 0.0001),
    }

    rows = []
    for code, px in panel.items():
        for d, close in zip(dates, px):
            rows.append(
                {
                    "BAS_DD": d.strftime("%Y%m%d"),
                    "ISU_CD": code,
                    "MKT_NM": "KOSPI",
                    "TDD_CLSPRC": float(close),
                }
            )

    bench_df = pl.DataFrame(
        {
            "date": dates,
            "open": bench_price,
            "high": bench_price,
            "low": bench_price,
            "close": bench_price,
            "volume": [1] * len(dates),
        }
    )

    def fake_fetch(*args, **kwargs):
        return bench_df

    monkeypatch.setattr(hf, "loadFiltered", lambda **_: pl.DataFrame(rows))
    monkeypatch.setattr("dartlab.quant.benchmark.data.fetchBenchmarkOhlcv", fake_fetch)

    result = calcBAB(betaWindow=252, volWindow=60)

    assert result is not None
    assert result["topLow"][0][0] == "LOWB"
    assert result["topHigh"][-1][0] == "HIGHB"
    assert "topLowVol" in result
    assert math.isclose(result["scores"]["MIDB"], 1.0, rel_tol=0.05)
