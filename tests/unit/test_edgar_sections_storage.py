"""EDGAR sectionsStorage read-only API 가드 — PR-E1 plan delegated-prancing-tower.

본 PR 단독 검증 항목:
- 모듈 import 성공 + DART sectionsStorage 와 API parity
- artifact 부재 ticker 에 대해 hasSectionsArtifact → False, loadSectionsLong/Wide → None
- ``DATA_RELEASES["edgarSections"]`` 등록 + nested=True
- path 분리 — DART ``dart/sections`` 와 EDGAR ``edgar/sections`` cross-pollination 0
"""

from __future__ import annotations

import pytest

from dartlab.core.dataConfig import DATA_RELEASES
from dartlab.providers.edgar.docs.sections import sectionsStorage as edgarStorage


def test_module_imports_clean() -> None:
    assert hasattr(edgarStorage, "sectionsDir")
    assert hasattr(edgarStorage, "sectionsPath")
    assert hasattr(edgarStorage, "indexPath")
    assert hasattr(edgarStorage, "listAvailablePeriods")
    assert hasattr(edgarStorage, "hasSectionsArtifact")
    assert hasattr(edgarStorage, "loadSectionsLong")
    assert hasattr(edgarStorage, "loadSectionsWide")
    assert hasattr(edgarStorage, "loadSectionsIndex")


def test_artifact_absent_returns_none() -> None:
    """현재 시점 EDGAR sections artifact 가 아직 빌드 안 됨 (PR-E2 후 생김).

    artifact 부재 ticker 는 None / False / [] 반환 의무.
    """
    ticker = "ZZZNONEXISTENT"
    assert edgarStorage.hasSectionsArtifact(ticker) is False
    assert edgarStorage.listAvailablePeriods(ticker) == []
    # HF 다운로드 차단해서 본 unit 이 네트워크 의존 안 하도록.
    import os

    os.environ["DARTLAB_NO_HF_DOWNLOAD"] = "1"
    try:
        assert edgarStorage.loadSectionsLong(ticker) is None
        assert edgarStorage.loadSectionsWide(ticker) is None
        assert edgarStorage.loadSectionsIndex(ticker) is None
    finally:
        os.environ.pop("DARTLAB_NO_HF_DOWNLOAD", None)


def test_data_releases_has_edgar_sections() -> None:
    """``DATA_RELEASES["edgarSections"]`` 등록 + nested=True."""
    assert "edgarSections" in DATA_RELEASES
    entry = DATA_RELEASES["edgarSections"]
    assert entry["dir"] == "edgar/sections"
    assert entry.get("public") is True
    assert entry.get("nested") is True, "period-sharded → nested upload 필수"


def test_path_provider_isolation() -> None:
    """EDGAR ``edgar/sections`` path segment 격리 (DART docs 농장 은퇴 — EDGAR 단독)."""
    edgarParts = edgarStorage.sectionsDir("AAPL").parts
    assert "edgar" in edgarParts and "sections" in edgarParts


def test_ticker_normalization() -> None:
    """ticker 소문자 입력도 대문자 path 로 해석."""
    upper = edgarStorage.sectionsDir("AAPL")
    lower = edgarStorage.sectionsDir("aapl")
    assert str(upper) == str(lower)


def test_period_sort_key() -> None:
    """Q1=1, Q2=2, Q3=3, Q4=4, annual=4 sort key 동작."""
    fn = edgarStorage._periodSortKey
    assert fn("2024Q1") == (2024, 1)
    assert fn("2024Q4") == (2024, 4)
    assert fn("2024") == (2024, 4)
    assert fn("") == (-1, -1)
    assert fn("garbage") == (-1, -1)
