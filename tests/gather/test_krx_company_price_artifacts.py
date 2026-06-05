"""KRX 회사별 가격 artifact 계약 테스트."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import polars as pl
import pytest

_ROOT = Path(__file__).resolve().parents[2]


def _load_build_krx_data():
    path = _ROOT / ".github" / "scripts" / "sync" / "buildKrxData.py"
    spec = importlib.util.spec_from_file_location("buildKrxData", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.unit
def test_company_price_frame_normalizes_schema_and_order():
    mod = _load_build_krx_data()
    raw = pl.DataFrame(
        [
            {
                "BAS_DD": "20260103",
                "ISU_CD": "A005930",
                "ISU_NM": "삼성전자",
                "MKT_NM": "KOSPI",
                "SECT_TP_NM": "보통주",
                "TDD_CLSPRC": 72000,
                "CMPPREVDD_PRC": 100,
                "FLUC_RT": 0.14,
                "TDD_OPNPRC": 71900,
                "TDD_HGPRC": 72500,
                "TDD_LWPRC": 71500,
                "ACC_TRDVOL": 1234,
                "ACC_TRDVAL": 88880000,
                "MKTCAP": 430000000000000,
                "LIST_SHRS": 5969782550,
            },
            {
                "BAS_DD": "20260102",
                "ISU_CD": "005930",
                "ISU_NM": "삼성전자",
                "MKT_NM": "KOSPI",
                "SECT_TP_NM": "보통주",
                "TDD_CLSPRC": 71900,
                "CMPPREVDD_PRC": 0,
                "FLUC_RT": 0.0,
                "TDD_OPNPRC": 71800,
                "TDD_HGPRC": 72100,
                "TDD_LWPRC": 71000,
                "ACC_TRDVOL": 1000,
                "ACC_TRDVAL": 71900000,
                "MKTCAP": 429000000000000,
                "LIST_SHRS": 5969782550,
            },
        ]
    )

    out = mod._companyPriceFrame(raw)

    assert out.columns == [
        "date",
        "stockCode",
        "name",
        "market",
        "open",
        "high",
        "low",
        "close",
        "priceChange",
        "fluctuationRate",
        "volume",
        "tradedValue",
        "marketCap",
        "listedShares",
    ]
    assert out["stockCode"].to_list() == ["005930", "005930"]
    assert out["date"].to_list() == ["20260102", "20260103"]
    assert out["close"].to_list() == [71900.0, 72000.0]


@pytest.mark.unit
def test_build_company_price_artifacts_writes_one_file_per_company(tmp_path: Path):
    mod = _load_build_krx_data()
    raw = pl.DataFrame(
        [
            {
                "BAS_DD": "20260102",
                "ISU_CD": "005930",
                "ISU_NM": "삼성전자",
                "MKT_NM": "KOSPI",
                "SECT_TP_NM": "보통주",
                "TDD_CLSPRC": 71900,
                "CMPPREVDD_PRC": 0,
                "FLUC_RT": 0.0,
                "TDD_OPNPRC": 71800,
                "TDD_HGPRC": 72100,
                "TDD_LWPRC": 71000,
                "ACC_TRDVOL": 1000,
                "ACC_TRDVAL": 71900000,
                "MKTCAP": 429000000000000,
                "LIST_SHRS": 5969782550,
            },
            {
                "BAS_DD": "20260102",
                "ISU_CD": "000660",
                "ISU_NM": "SK하이닉스",
                "MKT_NM": "KOSPI",
                "SECT_TP_NM": "보통주",
                "TDD_CLSPRC": 220000,
                "CMPPREVDD_PRC": 1000,
                "FLUC_RT": 0.46,
                "TDD_OPNPRC": 219000,
                "TDD_HGPRC": 222000,
                "TDD_LWPRC": 218000,
                "ACC_TRDVOL": 2000,
                "ACC_TRDVAL": 440000000,
                "MKTCAP": 160000000000000,
                "LIST_SHRS": 728002365,
            },
        ]
    )
    raw.write_parquet(tmp_path / "raw-2026.parquet")

    counts = mod.buildCompanyPriceArtifacts(tmp_path, minYears=1)

    assert counts == {"000660": 1, "005930": 1}
    samsung = pl.read_parquet(tmp_path / "company" / "005930.parquet")
    assert samsung.select("date", "stockCode", "close").to_dicts() == [
        {"date": "20260102", "stockCode": "005930", "close": 71900.0}
    ]
