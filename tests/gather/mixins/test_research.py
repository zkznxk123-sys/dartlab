"""research mixin 단위 테스트 — Gather 배선 + 필터 (네트워크 0)."""

from __future__ import annotations

import importlib

import polars as pl
import pytest

from dartlab.gather.mixins.research import _applyFilters

pytestmark = pytest.mark.unit


def test_smoke_import() -> None:
    importlib.import_module("dartlab.gather.mixins.research")


def test_gather_has_method() -> None:
    from dartlab.gather.engine import Gather

    assert hasattr(Gather, "brokerageReports")


def _sampleDf() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "report_id": ["a", "b", "c"],
            "broker": ["miraeasset", "nh", "yuanta"],
            "broker_name": ["미래에셋", "NH투자", "유안타"],
            "title": ["삼성전자 좋다", "SK하이닉스 분석", "시황 브리핑"],
            "report_type": ["기업분석", "기업", "투자전략"],
            "ticker": ["005930", "000660", None],
            "pub_date": ["2026-06-20", "2026-06-25", "2026-06-26"],
            "url": ["u1", "u2", "u3"],
            "author": ["갑", "을", "병"],
        }
    )


def test_filter_ticker() -> None:
    out = _applyFilters(_sampleDf(), ticker="005930", query=None, start=None, end=None, broker=None, reportType=None)
    assert out.height == 1 and out["broker"][0] == "miraeasset"


def test_filter_query_and_sort() -> None:
    out = _applyFilters(_sampleDf(), ticker=None, query="분석", start=None, end=None, broker=None, reportType=None)
    assert out.height == 1 and out["ticker"][0] == "000660"


def test_filter_date_range_desc() -> None:
    out = _applyFilters(
        _sampleDf(), ticker=None, query=None, start="2026-06-24", end=None, broker=None, reportType=None
    )
    assert out.height == 2
    # 발간일 내림차순
    assert out["pub_date"].to_list() == ["2026-06-26", "2026-06-25"]
