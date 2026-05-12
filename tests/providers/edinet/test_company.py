"""providers/edinet/company.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.providers.edinet.company  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")


def test_ask_callable() -> None:
    """ask() callable smoke."""
    from dartlab.providers.edinet.company import Company

    assert hasattr(Company, "ask")


def test_cleanup_cache_callable() -> None:
    """cleanupCache() callable smoke."""
    from dartlab.providers.edinet.company import Company

    assert hasattr(Company, "cleanupCache")


def test_diff_callable() -> None:
    """diff() callable smoke."""
    from dartlab.providers.edinet.company import Company

    assert hasattr(Company, "diff")


def test_disclosure_callable() -> None:
    """disclosure() callable smoke."""
    from dartlab.providers.edinet.company import Company

    assert hasattr(Company, "disclosure")


def test_filings_callable() -> None:
    """filings() callable smoke."""
    from dartlab.providers.edinet.company import Company

    assert hasattr(Company, "filings")


def test_live_filings_callable() -> None:
    """liveFilings() callable smoke."""
    from dartlab.providers.edinet.company import Company

    assert hasattr(Company, "liveFilings")


def test_memory_snapshot_callable() -> None:
    """memorySnapshot() callable smoke."""
    from dartlab.providers.edinet.company import Company

    assert hasattr(Company, "memorySnapshot")


def test_quant_callable() -> None:
    """quant() callable smoke."""
    from dartlab.providers.edinet.company import Company

    assert hasattr(Company, "quant")


def test_read_filing_callable() -> None:
    """readFiling() callable smoke."""
    from dartlab.providers.edinet.company import Company

    assert hasattr(Company, "readFiling")


def test_select_callable() -> None:
    """select() callable smoke."""
    from dartlab.providers.edinet.company import Company

    assert hasattr(Company, "select")


def test_show_callable() -> None:
    """show() callable smoke."""
    from dartlab.providers.edinet.company import Company

    assert hasattr(Company, "show")


def test_trace_callable() -> None:
    """trace() callable smoke."""
    from dartlab.providers.edinet.company import Company

    assert hasattr(Company, "trace")


def test_view_callable() -> None:
    """view() callable smoke."""
    from dartlab.providers.edinet.company import Company

    assert hasattr(Company, "view")
