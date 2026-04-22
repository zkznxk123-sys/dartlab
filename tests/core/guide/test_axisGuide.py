"""core/guide/axisGuide SSOT 빌더 단위 테스트."""

from __future__ import annotations

from dataclasses import dataclass

import polars as pl
import pytest

from dartlab.core.guide import buildAxisGuideDataFrame

pytestmark = pytest.mark.unit


@dataclass
class _FakeAxisEntry:
    label: str
    description: str
    example: str
    section: str = ""
    items: int = 0


def _sampleRegistry() -> dict[str, _FakeAxisEntry]:
    return {
        "수익성": _FakeAxisEntry(
            label="수익성", description="이익률 분석", example='analysis("수익성")', section="2-1", items=6
        ),
        "성장성": _FakeAxisEntry(
            label="성장성", description="성장률 추이", example='analysis("성장성")', section="2-2", items=5
        ),
    }


class TestBuildAxisGuideDataFrame:
    def test_minimum_columns(self):
        df = buildAxisGuideDataFrame(
            _sampleRegistry(),
            groupExtractor=lambda k, e: e.section,
        )
        assert df.columns == ["axis", "label", "description", "example", "group", "apiKey"]
        assert df.height == 2
        row = df.row(0, named=True)
        assert row["axis"] == "수익성"
        assert row["group"] == "2-1"
        assert row["apiKey"] == "불필요"

    def test_extra_columns_injected_between_group_and_apiKey(self):
        df = buildAxisGuideDataFrame(
            _sampleRegistry(),
            groupExtractor=lambda k, e: e.section,
            extraColumns={"items": lambda k, e: e.items},
        )
        assert df.columns == ["axis", "label", "description", "example", "group", "items", "apiKey"]
        assert df.row(0, named=True)["items"] == 6

    def test_apiKey_none_drops_column(self):
        df = buildAxisGuideDataFrame(
            _sampleRegistry(),
            groupExtractor=lambda k, e: e.section,
            apiKey=None,
        )
        assert "apiKey" not in df.columns
        assert df.columns == ["axis", "label", "description", "example", "group"]

    def test_apiKey_callable_per_row(self):
        df = buildAxisGuideDataFrame(
            _sampleRegistry(),
            groupExtractor=lambda k, e: e.section,
            apiKey=lambda k, e: "KEY1" if k == "수익성" else "KEY2",
        )
        assert df.filter(pl.col("axis") == "수익성").row(0, named=True)["apiKey"] == "KEY1"
        assert df.filter(pl.col("axis") == "성장성").row(0, named=True)["apiKey"] == "KEY2"

    def test_description_extractor_postprocess(self):
        df = buildAxisGuideDataFrame(
            _sampleRegistry(),
            groupExtractor=lambda k, e: e.section,
            descriptionExtractor=lambda k, e: e.description + " (종목 불필요)",
        )
        assert df.row(0, named=True)["description"].endswith(" (종목 불필요)")

    def test_custom_column_order(self):
        df = buildAxisGuideDataFrame(
            _sampleRegistry(),
            groupExtractor=lambda k, e: e.section,
            columnOrder=["axis", "group", "label"],
        )
        assert df.columns == ["axis", "group", "label"]

    def test_empty_registry(self):
        df = buildAxisGuideDataFrame({}, groupExtractor=lambda k, e: "")
        assert df.is_empty()
