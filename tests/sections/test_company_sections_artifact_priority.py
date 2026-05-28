"""Company.sections 가 신 sections artifact 우선 사용 + artifact 부재 시 fallback 회귀 가드.

plan snazzy-wibbling-origami PR-2a. ``data/dart/sections/{code}/{period}.parquet``
artifact 가 있으면 mmap parquet read (콜드 1s 목표). 없으면 옛 ``buildSections``
런타임 fallback (회귀 0).
"""

from __future__ import annotations

import polars as pl
import pytest

pytestmark = [pytest.mark.unit]


def test_company_sections_uses_artifact_when_present(monkeypatch, tmp_path):
    """artifact 있으면 buildSections 호출 0, artifact mmap read 결과 반환."""
    monkeypatch.setattr("dartlab.config.dataDir", str(tmp_path))

    code = "TESTART"
    from dartlab.providers.dart.docs.sectionsArchive.sectionsBuilder import saveSectionsByPeriod
    from dartlab.providers.dart.docs.sectionsArchive.sectionsStorage import hasSectionsArtifact

    fixtureWide = pl.DataFrame(
        {
            "topic": ["사업의 개요", "주주 현황"],
            "blockType": ["text", "text"],
            "blockOrder": [0, 0],
            "segmentKey": ["body|p:개요|occ:1", "body|p:주주|occ:1"],
            "2025": ["연간 개요 본문", "연간 주주 본문"],
            "2024": ["전년 개요 본문", "전년 주주 본문"],
        }
    )
    saveSectionsByPeriod(code, fixtureWide)
    assert hasSectionsArtifact(code)

    # buildSections 가 호출되면 안 됨 — sentinel raise.
    def shouldNotBeCalled(*args, **kwargs):
        raise RuntimeError("artifact 있는데 buildSections fallback 호출 — PR-2a 회귀")

    monkeypatch.setattr("dartlab.providers.dart.builder.docsProfileBuilder.buildSections", shouldNotBeCalled)

    # Company 생성 시 docs.parquet 검증 등 회피 위해 __init__ 도 부분 monkeypatch.
    # 직접 Company 인스턴스 만들지 않고 sections property 만 검증.
    import types

    from dartlab.providers.dart.company import Company

    fake = types.SimpleNamespace()
    fake.stockCode = code
    result = Company.sections.fget(fake)
    assert result is not None
    assert result.height == 2
    # period 컬럼 보존
    assert "2025" in result.columns and "2024" in result.columns


def test_company_sections_falls_back_when_artifact_missing(monkeypatch, tmp_path):
    """artifact 부재 시 옛 buildSections 호출 + 그 결과 반환."""
    monkeypatch.setattr("dartlab.config.dataDir", str(tmp_path))

    code = "NOARTIFACT"
    from dartlab.providers.dart.docs.sectionsArchive.sectionsStorage import hasSectionsArtifact

    assert not hasSectionsArtifact(code)

    fakeResult = pl.DataFrame({"topic": ["fallback"], "2025": ["fallback content"]})
    callCount = {"n": 0}

    def fakeBuildSections(self):
        callCount["n"] += 1
        return fakeResult

    monkeypatch.setattr("dartlab.providers.dart.builder.docsProfileBuilder.buildSections", fakeBuildSections)

    import types

    from dartlab.providers.dart.company import Company

    fake = types.SimpleNamespace()
    fake.stockCode = code
    result = Company.sections.fget(fake)
    assert callCount["n"] == 1  # fallback 호출됨
    assert result is not None
    assert result["topic"][0] == "fallback"


def test_company_sections_falls_back_when_artifact_empty(monkeypatch, tmp_path):
    """artifact 디렉터리 있지만 빈 (parquet 부재) → fallback."""
    monkeypatch.setattr("dartlab.config.dataDir", str(tmp_path))

    code = "EMPTYART"
    from dartlab.providers.dart.docs.sectionsArchive.sectionsStorage import sectionsDir

    sectionsDir(code).mkdir(parents=True, exist_ok=True)

    fakeResult = pl.DataFrame({"topic": ["fallback"], "2025": ["fallback"]})
    monkeypatch.setattr("dartlab.providers.dart.builder.docsProfileBuilder.buildSections", lambda self: fakeResult)

    import types

    from dartlab.providers.dart.company import Company

    fake = types.SimpleNamespace()
    fake.stockCode = code
    result = Company.sections.fget(fake)
    assert result is not None
    assert result["topic"][0] == "fallback"
