"""brokerage.schema 단위 테스트 — ReportMeta + toDataFrame 스키마 가드."""

from __future__ import annotations

import pytest

from dartlab.gather.sources.brokerage.schema import ReportMeta, toDataFrame

pytestmark = pytest.mark.unit

_COLUMNS = [
    "report_id",
    "broker",
    "broker_name",
    "title",
    "report_type",
    "ticker",
    "pub_date",
    "url",
    "author",
]


def test_to_dataframe_schema() -> None:
    items = [
        ReportMeta("nh", "NH투자", "[한세실업] 과도한 우려", "https://x", "2026-06-26", "기업", "정지윤", "105630")
    ]
    df = toDataFrame(items)
    assert df.height == 1
    assert df.columns == _COLUMNS
    assert df["ticker"][0] == "105630"


def test_to_dataframe_empty() -> None:
    df = toDataFrame([])
    assert df.height == 0
    assert df.columns == _COLUMNS


def test_report_id_stable_on_url_change() -> None:
    a = ReportMeta("nh", "NH투자", "t", "u1", "2026-06-26")
    b = ReportMeta("nh", "NH투자", "t", "u2", "2026-06-26")
    assert a.reportId() == b.reportId()  # (broker·title·date) 기준 dedup


def test_report_id_differs_on_title() -> None:
    a = ReportMeta("nh", "NH투자", "t1", "u", "2026-06-26")
    b = ReportMeta("nh", "NH투자", "t2", "u", "2026-06-26")
    assert a.reportId() != b.reportId()
