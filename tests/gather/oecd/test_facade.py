"""dartlab.gather.oecd 단위 테스트 — facade + catalog 구조 회귀 가드."""

from __future__ import annotations

import importlib

import pytest

from dartlab.gather.infra.sdmxTypes import SdmxCatalogEntry, SdmxSeriesNotFoundError
from dartlab.gather.oecd import Oecd
from dartlab.gather.oecd import catalog as _catalog

pytestmark = pytest.mark.unit


def test_smoke_import() -> None:
    importlib.import_module("dartlab.gather.oecd")
    importlib.import_module("dartlab.gather.oecd.catalog")


def test_catalog_8_indicators() -> None:
    entries = _catalog.listCatalog()
    assert len(entries) >= 8
    for e in entries:
        assert isinstance(e, SdmxCatalogEntry)
        assert e.provider == "OECD"
        assert e.id.startswith("OECD_")


def test_catalog_hasIndicator() -> None:
    assert _catalog.hasIndicator("OECD_CPI_US") is True
    assert _catalog.hasIndicator("UNKNOWN") is False


def test_getEntry_unknown_raises() -> None:
    with pytest.raises(KeyError, match="OECD catalog"):
        _catalog.getEntry("UNKNOWN")


def test_facade_series_unknown_raises() -> None:
    o = Oecd()
    try:
        with pytest.raises(SdmxSeriesNotFoundError, match="OECD catalog"):
            o.series("UNKNOWN")
    finally:
        o.close()


def test_facade_catalog_returns_list() -> None:
    o = Oecd()
    try:
        cat = o.catalog()
        assert isinstance(cat, list)
        assert len(cat) >= 8
    finally:
        o.close()
