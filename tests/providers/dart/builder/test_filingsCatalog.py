"""providers/dart/builder/filingsCatalog.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    import dartlab.providers.dart.builder.filingsCatalog  # noqa: F401


def test_build_disclosure_callable() -> None:
    """buildDisclosure() callable smoke."""
    from dartlab.providers.dart.builder.filingsCatalog import buildDisclosure

    assert callable(buildDisclosure)


def test_build_filings_callable() -> None:
    """buildFilings() callable smoke."""
    from dartlab.providers.dart.builder.filingsCatalog import buildFilings

    assert callable(buildFilings)


def test_build_live_filings_callable() -> None:
    """buildLiveFilings() callable smoke."""
    from dartlab.providers.dart.builder.filingsCatalog import buildLiveFilings

    assert callable(buildLiveFilings)


def test_build_read_filing_callable() -> None:
    """buildReadFiling() callable smoke."""
    from dartlab.providers.dart.builder.filingsCatalog import buildReadFiling

    assert callable(buildReadFiling)


def test_build_update_callable() -> None:
    """buildUpdate() callable smoke."""
    from dartlab.providers.dart.builder.filingsCatalog import buildUpdate

    assert callable(buildUpdate)
