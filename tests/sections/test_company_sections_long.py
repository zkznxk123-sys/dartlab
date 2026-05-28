"""Company.sectionsLong() 신규 method 회귀 가드.

plan snazzy-wibbling-origami PR-4a-i. D.1 모듈이 docs.parquet 직접 read 하던 패턴을
Company.sectionsLong 으로 수렴. artifact 있으면 mmap long read, 없으면 wide→long 변환.
"""

from __future__ import annotations

import types

import polars as pl
import pytest

pytestmark = [pytest.mark.unit]


def test_sectionsLong_uses_artifact_when_present(monkeypatch, tmp_path):
    """artifact 있으면 loadSectionsLong 직접 호출 — fallback buildSections 0."""
    monkeypatch.setattr("dartlab.config.dataDir", str(tmp_path))
    code = "LONGART"
    from dartlab.providers.dart.docs.sectionsArchive.sectionsBuilder import saveSectionsByPeriod

    fixture = pl.DataFrame(
        {
            "topic": ["사업의 개요", "주주 현황"],
            "blockType": ["text", "text"],
            "blockOrder": [0, 0],
            "segmentKey": ["a", "b"],
            "2025": ["개요 본문", "주주 본문"],
            "2024": ["전년 개요", "전년 주주"],
        }
    )
    saveSectionsByPeriod(code, fixture)

    def shouldNotBeCalled(self):
        raise RuntimeError("artifact 있는데 fallback path 진입 — 회귀")

    monkeypatch.setattr("dartlab.providers.dart.builder.docsProfileBuilder.buildSections", shouldNotBeCalled)

    from dartlab.providers.dart.company import Company

    fake = types.SimpleNamespace()
    fake.stockCode = code

    long = Company.sectionsLong(fake)
    assert long is not None
    # 2 row × 2 period = 4 (sparse drop 후)
    assert long.height == 4
    assert {"period", "content"}.issubset(set(long.columns))


def test_sectionsLong_period_filter(monkeypatch, tmp_path):
    monkeypatch.setattr("dartlab.config.dataDir", str(tmp_path))
    code = "LONGFILT"
    from dartlab.providers.dart.docs.sectionsArchive.sectionsBuilder import saveSectionsByPeriod

    fixture = pl.DataFrame(
        {
            "topic": ["A"],
            "blockType": ["text"],
            "blockOrder": [0],
            "segmentKey": ["x"],
            "2025": ["c1"],
            "2024": ["c2"],
            "2023": ["c3"],
        }
    )
    saveSectionsByPeriod(code, fixture)

    from dartlab.providers.dart.company import Company

    fake = types.SimpleNamespace()
    fake.stockCode = code

    long = Company.sectionsLong(fake, periods=["2025"])
    assert long is not None
    assert set(long["period"].unique().to_list()) == {"2025"}


def test_sectionsLong_columnar_projection(monkeypatch, tmp_path):
    monkeypatch.setattr("dartlab.config.dataDir", str(tmp_path))
    code = "LONGCOL"
    from dartlab.providers.dart.docs.sectionsArchive.sectionsBuilder import saveSectionsByPeriod

    fixture = pl.DataFrame(
        {
            "topic": ["A"],
            "blockType": ["text"],
            "blockOrder": [0],
            "segmentKey": ["x"],
            "2025": ["content text"],
        }
    )
    saveSectionsByPeriod(code, fixture)

    from dartlab.providers.dart.company import Company

    fake = types.SimpleNamespace()
    fake.stockCode = code

    # meta only — content 컬럼 페이지 fault 0
    metaOnly = Company.sectionsLong(fake, columns=["topic", "period"])
    assert metaOnly is not None
    assert set(metaOnly.columns) == {"topic", "period"}


def test_sectionsLong_falls_back_to_wide(monkeypatch, tmp_path):
    """artifact 부재 시 Company.sections (fallback path) → wideToLong 변환."""
    monkeypatch.setattr("dartlab.config.dataDir", str(tmp_path))
    code = "NOLONG"

    fakeWide = pl.DataFrame(
        {
            "topic": ["FB"],
            "blockType": ["text"],
            "blockOrder": [0],
            "2025": ["fallback content"],
        }
    )

    def fakeBuildSections(self):
        return fakeWide

    monkeypatch.setattr("dartlab.providers.dart.builder.docsProfileBuilder.buildSections", fakeBuildSections)

    from dartlab.providers.dart.company import Company

    # SimpleNamespace 가 self.sections property access 가능하도록 wrap. sections property
    # 가 fget(self) 호출하면 fake.stockCode 사용해 hasSectionsArtifact False → fakeBuildSections.
    class FakeCompany:
        stockCode = code
        sections = Company.sections

    fake = FakeCompany()

    long = Company.sectionsLong(fake)
    assert long is not None
    assert long.height == 1
    assert long["period"][0] == "2025"
    assert long["content"][0] == "fallback content"
