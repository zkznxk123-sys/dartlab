"""dartlab.gather.ecb 단위 테스트 — facade + catalog 구조 회귀 가드.

라이브 SDMX 호출은 nightly. 본 파일은 smoke + catalog 정합성 + lookup 분기.
"""

from __future__ import annotations

import importlib

import pytest

from dartlab.gather.ecb import Ecb
from dartlab.gather.ecb import catalog as _catalog
from dartlab.gather.infra.sdmxTypes import SdmxCatalogEntry, SdmxSeriesNotFoundError

pytestmark = pytest.mark.unit


def test_smoke_import() -> None:
    """모듈 import 회귀 차단."""
    importlib.import_module("dartlab.gather.ecb")
    importlib.import_module("dartlab.gather.ecb.catalog")
    importlib.import_module("dartlab.gather.ecb.facade")


def test_catalog_8_indicators() -> None:
    """ECB catalog 최소 8 지표."""
    entries = _catalog.listCatalog()
    assert len(entries) >= 8
    for e in entries:
        assert isinstance(e, SdmxCatalogEntry)
        assert e.provider == "ECB"
        assert e.id.startswith("ECB_")
        assert e.dataflow
        assert e.key


def test_catalog_hasIndicator_true_false() -> None:
    """등록/미등록 분기."""
    assert _catalog.hasIndicator("ECB_M3") is True
    assert _catalog.hasIndicator("FOO_BAR") is False


def test_getEntry_unknown_raises() -> None:
    """미등록 indicator → KeyError."""
    with pytest.raises(KeyError, match="ECB catalog"):
        _catalog.getEntry("UNKNOWN")


def test_facade_series_unknown_raises() -> None:
    """facade.series 미등록 → SdmxSeriesNotFoundError."""
    e = Ecb()
    try:
        with pytest.raises(SdmxSeriesNotFoundError, match="ECB catalog"):
            e.series("UNKNOWN")
    finally:
        e.close()


def test_facade_compare_empty_returns_empty() -> None:
    """빈 리스트 → 빈 DataFrame."""
    e = Ecb()
    try:
        df = e.compare([])
        assert df.is_empty()
    finally:
        e.close()


def test_facade_catalog_returns_list() -> None:
    """catalog() 동작 확인."""
    e = Ecb()
    try:
        cat = e.catalog()
        assert isinstance(cat, list)
        assert len(cat) >= 8
    finally:
        e.close()
