"""core/axisGuide SSOT 빌더 단위 테스트."""

from __future__ import annotations

from dataclasses import dataclass

import polars as pl
import pytest

from dartlab.synth.axisGuide import buildAxisGuideDataFrame

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


class Test5EngineGuideRegression:
    """5엔진 _guide() 리팩터 전후 출력 DataFrame 회귀 보호.

    리팩터가 컬럼 순서·이름·행 개수·첫 행 내용을 바꾸지 않아야 한다.
    """

    def test_analysis_engine(self):
        from dartlab.analysis.financial import Analysis

        df = Analysis()._guide()
        assert df.columns == ["axis", "label", "description", "example", "group", "items", "apiKey"]
        assert df.height >= 20  # 최소 보장선 (축 추가될 수 있음)
        row0 = df.row(0, named=True)
        assert row0["axis"] == "수익구조"
        assert row0["apiKey"] == "불필요"
        assert isinstance(row0["items"], int) and row0["items"] >= 1

    def test_scan_engine(self):
        import dartlab

        df = dartlab.scan()
        assert df.columns == ["axis", "label", "group", "description", "example", "apiKey"]
        assert df.height >= 10
        row0 = df.row(0, named=True)
        assert row0["axis"] == "governance"
        assert row0["group"] == "DART"
        assert row0["apiKey"] == "불필요"

    def test_macro_engine(self):
        import dartlab

        df = dartlab.macro()
        assert df.columns == ["axis", "label", "description", "example", "group", "apiKey"]
        assert df.height >= 8
        row0 = df.row(0, named=True)
        assert row0["axis"] == "cycle"
        assert "제" in row0["group"] and "막" in row0["group"]
        assert "불필요" in row0["apiKey"]

    def test_credit_engine(self):
        import dartlab

        df = dartlab.credit()
        assert df.columns == ["axis", "label", "description", "example", "group", "apiKey"]
        assert df.height >= 7
        row0 = df.row(0, named=True)
        assert row0["axis"] == "grade"
        assert row0["apiKey"] == "불필요"

    def test_quant_engine(self):
        import dartlab

        df = dartlab.quant()
        # quant는 apiKey 컬럼 없음
        assert df.columns == ["axis", "label", "description", "example", "group"]
        assert df.height >= 20
        row0 = df.row(0, named=True)
        assert row0["axis"] == "indicators"
