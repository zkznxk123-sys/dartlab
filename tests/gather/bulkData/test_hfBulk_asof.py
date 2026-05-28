"""hfBulk loadFiltered asof 옵션 — Sprint 4 PR3.

라이브 HF 다운로드 없음 (monkeypatch _loadYear).
asof 컷오프 동작 + bitemporal 컬럼 자동 감지 + 기존 동작 회귀 0.
"""

from __future__ import annotations

from datetime import date

import polars as pl
import pytest

from dartlab.gather.bulkData import hfBulk
from dartlab.gather.bulkData.hfBulk import (
    _COL_BUSINESS_TIME,
    _COL_CODE,
    _COL_DATE,
    _COL_KNOWLEDGE_TIME,
    loadFiltered,
)

pytestmark = pytest.mark.unit


def _fakeLegacyParquet(year: int) -> pl.DataFrame:
    """legacy schema (BAS_DD + ISU_CD + 가격) — bitemporal 컬럼 없음."""
    return pl.DataFrame(
        {
            _COL_DATE: ["20240101", "20240615", "20241231"],
            _COL_CODE: ["005930", "005930", "005930"],
            "TDD_CLSPRC": [70000, 75000, 80000],
            "TDD_OPNPRC": [69000, 74000, 79000],
            "TDD_HGPRC": [71000, 76000, 81000],
            "TDD_LWPRC": [68000, 73000, 78000],
            "ACC_TRDVOL": [1000000, 2000000, 3000000],
        }
    )


def _fakeBitemporalParquet(year: int) -> pl.DataFrame:
    """신 schema (business_time + knowledge_time 추가)."""
    return pl.DataFrame(
        {
            _COL_DATE: ["20240101", "20240615", "20241231"],
            _COL_CODE: ["005930", "005930", "005930"],
            "TDD_CLSPRC": [70000, 75000, 80000],
            _COL_BUSINESS_TIME: [date(2024, 1, 1), date(2024, 6, 15), date(2024, 12, 31)],
            _COL_KNOWLEDGE_TIME: [date(2024, 1, 2), date(2024, 6, 16), date(2025, 1, 5)],
        }
    )


def test_loadFiltered_no_asof_unchanged(monkeypatch) -> None:
    """asof=None → 기존 동작 100% 유지."""
    monkeypatch.setattr(hfBulk, "_loadYear", _fakeLegacyParquet)
    df = loadFiltered(stockCode="005930", year=2024, adjustment="raw")
    assert df.height == 3
    # 컷오프 무관 — 전체 반환


def test_loadFiltered_asof_legacy_falls_back_to_BAS_DD(monkeypatch) -> None:
    """bitemporal 컬럼 없으면 BAS_DD (string) 로 컷오프."""
    monkeypatch.setattr(hfBulk, "_loadYear", _fakeLegacyParquet)
    df = loadFiltered(stockCode="005930", year=2024, adjustment="raw", asof="2024-06-30")
    # 6/30 이전: 1/1, 6/15 → 2 row
    assert df.height == 2
    assert df[_COL_DATE].to_list() == ["20240101", "20240615"]


def test_loadFiltered_asof_bitemporal_dual_filter(monkeypatch) -> None:
    """bitemporal 있으면 business+knowledge 둘 다 ≤ asof."""
    monkeypatch.setattr(hfBulk, "_loadYear", _fakeBitemporalParquet)
    df = loadFiltered(stockCode="005930", year=2024, adjustment="raw", asof="2024-12-31")
    # 12/31 이전 business + 12/31 이전 knowledge_time:
    # row1 (2024-01-01, 2024-01-02) ✓ / row2 (2024-06-15, 2024-06-16) ✓ /
    # row3 (2024-12-31, 2025-01-05) — knowledge > asof → 제외
    assert df.height == 2


def test_loadFiltered_asof_returns_empty_when_all_after(monkeypatch) -> None:
    """모든 row 가 asof 이후 → 빈 DataFrame."""
    monkeypatch.setattr(hfBulk, "_loadYear", _fakeLegacyParquet)
    df = loadFiltered(stockCode="005930", year=2024, adjustment="raw", asof="2023-12-31")
    assert df.height == 0


def test_loadFiltered_asof_date_object(monkeypatch) -> None:
    """asof 가 date 객체여도 OK."""
    monkeypatch.setattr(hfBulk, "_loadYear", _fakeLegacyParquet)
    df = loadFiltered(stockCode="005930", year=2024, adjustment="raw", asof=date(2024, 6, 30))
    assert df.height == 2
