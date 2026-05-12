"""providers/edinet/openapi/client.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.providers.edinet.openapi.client  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")


def test_download_document_callable() -> None:
    """downloadDocument() callable smoke."""
    from dartlab.providers.edinet.openapi.client import EdinetClient

    assert hasattr(EdinetClient, "downloadDocument")


def test_iter_documents_callable() -> None:
    """iterDocuments() callable smoke."""
    from dartlab.providers.edinet.openapi.client import EdinetClient

    assert hasattr(EdinetClient, "iterDocuments")


def test_iter_edinet_codes_callable() -> None:
    """iterEdinetCodes() callable smoke."""
    from dartlab.providers.edinet.openapi.client import EdinetClient

    assert hasattr(EdinetClient, "iterEdinetCodes")


def test_list_documents_callable() -> None:
    """listDocuments() callable smoke."""
    from dartlab.providers.edinet.openapi.client import EdinetClient

    assert hasattr(EdinetClient, "listDocuments")


def test_list_edinet_codes_callable() -> None:
    """listEdinetCodes() callable smoke."""
    from dartlab.providers.edinet.openapi.client import EdinetClient

    assert hasattr(EdinetClient, "listEdinetCodes")
