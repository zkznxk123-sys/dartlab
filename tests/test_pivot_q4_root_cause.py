"""Sentinel — DART pivot Q4 함정 회귀 차단 (Layer 1+2+3.1).

Phase A1 발견:
- raw `scan/finance.parquet` 의 IS/CIS 4분기 thstrm_amount = 이미 연간값
- `pivot.py::_normalizeQ4` 가 의도적으로 standalone 분기로 변환
- 위층(calc)이 변환을 잊고 직접 read 하면 4배 작은 값

이 sentinel:
- SK하이닉스 매출액 2025 = 97.1조 (annualSumFlow 결과)
- pivot.py 의 _normalizeQ4 가 깨지면 이 값이 변함
- 99.7% Q4 패턴 회귀
"""

from __future__ import annotations

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.requires_data]


def test_sk_hynix_revenue_2025_annual():
    """SK하이닉스 2025 매출 = 97조 (Plan v4: pivot annual 컬럼 자동 노출).

    Layer A 후 c.IS 가 분기 컬럼 + annual 컬럼 둘 다 노출.
    annualColsFromPeriods 가 annual 컬럼 우선 잡음 → calc 가 row['2025'] 직접 read.
    """
    import dartlab
    from dartlab.analysis.financial._helpers import annualColsFromPeriods, toDict

    c = dartlab.Company("000660")
    parsed = toDict(c.select("IS", ["매출액"]))
    assert parsed is not None
    isData, isPeriods = parsed
    revRow = isData.get("매출액", {})

    yCols = annualColsFromPeriods(isPeriods)
    # Plan v4 root fix: annual 컬럼이 노출되므로 yCols[0] = "2025" (Q4 fallback 아님)
    assert yCols[0] == "2025", f"annualColsFromPeriods[0] = {yCols[0]} (expected '2025'). Layer A 회귀."
    assert "Q" not in yCols[0], "annual 컬럼 노출 시 Q4 fallback 아님"

    val = revRow.get(yCols[0])

    # SK하이닉스 2025 매출액 ≈ 97.1조
    assert val is not None, "SK하이닉스 2025 매출액 결손"
    assert 95e12 < val < 100e12, f"SK하이닉스 2025 매출 = {val:.2e} (expected ~97조)"


def test_sk_hynix_q4_standalone_not_annual():
    """SK하이닉스 c.IS 의 2025Q4 컬럼은 분기 단독값 (32.8조)이어야 한다.

    pivot.py::_normalizeQ4 회귀: raw 4분기 연간을 standalone 으로 변환.
    Q4 단독 ≈ 연간 / 4 정도. 직접 read 하면 분기 단독.
    """
    import dartlab

    c = dartlab.Company("000660")
    df = c.select("IS", ["매출액"])
    assert df is not None
    parsedDf = df.df if hasattr(df, "df") else df
    rev = parsedDf.filter(parsedDf["항목"] == "매출액")
    assert rev.height > 0

    q4 = rev["2025Q4"][0]
    # Q4 단독값 ≈ 32.8조 (97.1조 - Q1Q2Q3 누적 64.3조)
    assert q4 is not None
    assert 30e12 < q4 < 35e12, f"SK하이닉스 2025Q4 standalone = {q4:.2e} (expected ~32.8조). pivot._normalizeQ4 회귀."


def test_q4_pattern_invariant():
    """전 종목 sample: Q4 ths > Q3 ths 비율 99% 이상.

    Phase A1: scan/finance.parquet raw 의 99.7% Q4 패턴.
    pivot 변환 전 raw 데이터 검증.
    """
    import polars as pl

    lf = pl.scan_parquet("data/dart/scan/finance.parquet")
    base = lf.with_columns(
        pl.col("thstrm_amount").cast(pl.Utf8).str.replace_all(",", "").cast(pl.Float64, strict=False).alias("ths"),
    )
    cisQ4 = (
        base.filter(pl.col("sj_div") == "CIS")
        .filter(pl.col("fs_div") == "CFS")
        .filter(pl.col("account_nm") == "매출액")
        .filter(pl.col("ths").is_not_null())
        .group_by(["stockCode", "bsns_year"])
        .agg(
            pl.col("ths").filter(pl.col("reprt_nm") == "3분기").first().alias("q3"),
            pl.col("ths").filter(pl.col("reprt_nm") == "4분기").first().alias("q4"),
        )
        .filter(pl.col("q4").is_not_null() & pl.col("q3").is_not_null())
        .with_columns((pl.col("q4") > pl.col("q3")).alias("q4GtQ3"))
        .collect()
    )

    if len(cisQ4) < 100:
        pytest.skip("scan/finance.parquet 통합본 부족")

    ratio = cisQ4["q4GtQ3"].mean()
    # 99% 이상 (Phase A1: 99.7% 검증)
    assert ratio > 0.99, f"Q4>Q3 패턴 비율 {ratio:.3f} (expected >0.99). raw 데이터 또는 sample 변동."
