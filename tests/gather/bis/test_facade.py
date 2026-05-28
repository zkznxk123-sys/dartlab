"""dartlab.gather.bis 단위 테스트 — facade + catalog 구조 회귀 가드."""

from __future__ import annotations

import importlib

import pytest

from dartlab.gather.bis import Bis
from dartlab.gather.bis import catalog as _catalog
from dartlab.gather.infra.sdmxTypes import SdmxCatalogEntry, SdmxSeriesNotFoundError

pytestmark = pytest.mark.unit


def test_smoke_import() -> None:
    importlib.import_module("dartlab.gather.bis")
    importlib.import_module("dartlab.gather.bis.catalog")


def test_catalog_8_indicators() -> None:
    entries = _catalog.listCatalog()
    assert len(entries) >= 8
    for e in entries:
        assert isinstance(e, SdmxCatalogEntry)
        assert e.provider == "BIS"
        assert e.id.startswith("BIS_")


def test_catalog_hasIndicator() -> None:
    assert _catalog.hasIndicator("BIS_POLICY_RATE_US") is True
    assert _catalog.hasIndicator("UNKNOWN") is False


def test_getEntry_unknown_raises() -> None:
    with pytest.raises(KeyError, match="BIS catalog"):
        _catalog.getEntry("UNKNOWN")


def test_facade_series_unknown_raises() -> None:
    b = Bis()
    try:
        with pytest.raises(SdmxSeriesNotFoundError, match="BIS catalog"):
            b.series("UNKNOWN")
    finally:
        b.close()


def test_facade_catalog_returns_list() -> None:
    b = Bis()
    try:
        cat = b.catalog()
        assert isinstance(cat, list)
        assert len(cat) >= 8
    finally:
        b.close()
