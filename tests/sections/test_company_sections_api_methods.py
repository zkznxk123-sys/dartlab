"""Company.sectionsRaw + Company.sectionsTables 신규 method 회귀 가드.

plan snazzy-wibbling-origami PR-2b + PR-5b. viewer / finance 별 의도 명시 API.
"""

from __future__ import annotations

import polars as pl
import pytest

from dartlab.providers.dart.company import Company

pytestmark = [
    pytest.mark.unit,
    pytest.mark.skip(
        reason="sections 사전빌드 파이프라인 (saveSectionsByPeriod 빌드 + wideToLong) 미완성 "
        "— parked (plan snazzy-wibbling-origami §3.5 B, sections 완성은 안정화 후 후속). 완성 시 해제."
    ),
]


def test_sectionsRaw_returns_mixed_format(monkeypatch, tmp_path):
    """sectionsRaw 가 sectionsAs(stripTags=False) 와 동일 결과."""
    monkeypatch.setattr("dartlab.config.dataDir", str(tmp_path))
    code = "RAWTEST"
    from dartlab.providers.dart.docs.sections.sectionsBuilder import saveSectionsByPeriod

    fixture = pl.DataFrame(
        {
            "topic": ["A"],
            "blockType": ["table"],
            "blockOrder": [0],
            "segmentKey": ["x"],
            "2025": ['<table><tr><td align="right">100</td></tr></table>'],
        }
    )
    saveSectionsByPeriod(code, fixture)

    class FakeCompany:
        stockCode = code
        sections = Company.sections
        sectionsAs = Company.sectionsAs
        sectionsRaw = Company.sectionsRaw

    fake = FakeCompany()
    raw = fake.sectionsRaw()
    # sectionsRaw 는 mixed 양식 — HTML 그대로 보존
    assert raw is not None
    # cell 에 HTML 태그 보존
    assert any("<table" in str(v) for v in raw["2025"].to_list() if v)


def test_sectionsTables_returns_table_struct_column(monkeypatch, tmp_path):
    """sectionsTables 가 content_table_struct 컬럼만 select."""
    monkeypatch.setattr("dartlab.config.dataDir", str(tmp_path))
    code = "TABTEST"
    from dartlab.providers.dart.docs.sections.sectionsBuilder import saveSectionsByPeriod

    fixture = pl.DataFrame(
        {
            "topic": ["A", "B"],
            "blockType": ["table", "text"],
            "blockOrder": [0, 0],
            "segmentKey": ["x", "y"],
            "2025": [
                '<table><tr><td align="right">100</td></tr></table>',
                "## 헤딩\n본문만",
            ],
        }
    )
    saveSectionsByPeriod(code, fixture)

    class FakeCompany:
        stockCode = code
        sections = Company.sections
        sectionsLong = Company.sectionsLong
        sectionsTables = Company.sectionsTables

    fake = FakeCompany()
    tables = fake.sectionsTables()
    assert tables is not None
    # content_table_struct 컬럼만 — content/content_plain 페이지 fault 0
    assert "content_table_struct" in tables.columns
    assert "content" not in tables.columns
    assert "content_plain" not in tables.columns
    # 표 있는 row 만 검증 (B 는 빈 문자열)
    aRow = tables.filter(pl.col("topic") == "A")
    assert aRow.height >= 1
    assert "<table" in aRow["content_table_struct"][0]


def test_sectionsTables_period_filter(monkeypatch, tmp_path):
    monkeypatch.setattr("dartlab.config.dataDir", str(tmp_path))
    code = "TABFILT"
    from dartlab.providers.dart.docs.sections.sectionsBuilder import saveSectionsByPeriod

    fixture = pl.DataFrame(
        {
            "topic": ["A"],
            "blockType": ["table"],
            "blockOrder": [0],
            "segmentKey": ["x"],
            "2025": ["<table><tr><td>2025</td></tr></table>"],
            "2024": ["<table><tr><td>2024</td></tr></table>"],
        }
    )
    saveSectionsByPeriod(code, fixture)

    class FakeCompany:
        stockCode = code
        sections = Company.sections
        sectionsLong = Company.sectionsLong
        sectionsTables = Company.sectionsTables

    fake = FakeCompany()
    only2025 = fake.sectionsTables(periods=["2025"])
    assert only2025 is not None
    assert set(only2025["period"].unique().to_list()) == {"2025"}
