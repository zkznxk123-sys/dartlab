"""dartlab.gather.imf 단위 테스트 — facade + catalog 구조 회귀 가드."""

from __future__ import annotations

import importlib

import pytest

from dartlab.gather.imf import Imf
from dartlab.gather.imf import catalog as _catalog
from dartlab.gather.infra.sdmxTypes import SdmxCatalogEntry, SdmxSeriesNotFoundError

pytestmark = pytest.mark.unit


def test_smoke_import() -> None:
    importlib.import_module("dartlab.gather.imf")
    importlib.import_module("dartlab.gather.imf.catalog")


def test_catalog_8_indicators() -> None:
    entries = _catalog.listCatalog()
    assert len(entries) >= 8
    for e in entries:
        assert isinstance(e, SdmxCatalogEntry)
        assert e.provider == "IMF"
        assert e.id.startswith("IMF_")


def test_catalog_hasIndicator() -> None:
    assert _catalog.hasIndicator("IMF_FX_USD_KRW") is True
    assert _catalog.hasIndicator("UNKNOWN") is False


def test_getEntry_unknown_raises() -> None:
    with pytest.raises(KeyError, match="IMF catalog"):
        _catalog.getEntry("UNKNOWN")


def test_facade_series_unknown_raises() -> None:
    i = Imf()
    try:
        with pytest.raises(SdmxSeriesNotFoundError, match="IMF catalog"):
            i.series("UNKNOWN")
    finally:
        i.close()


def test_facade_catalog_returns_list() -> None:
    i = Imf()
    try:
        cat = i.catalog()
        assert isinstance(cat, list)
        assert len(cat) >= 8
    finally:
        i.close()
