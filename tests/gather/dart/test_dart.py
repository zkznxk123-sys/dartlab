"""providers/dart/openapi/dart.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.gather.dart.dart  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")


def test_company_callable() -> None:
    """company() callable smoke."""
    from dartlab.gather.dart.dart import Dart

    assert hasattr(Dart, "company")


def test_corp_code_callable() -> None:
    """corpCode() callable smoke."""
    from dartlab.gather.dart.dart import Dart

    assert hasattr(Dart, "corpCode")


def test_corp_codes_callable() -> None:
    """corpCodes() callable smoke."""
    from dartlab.gather.dart.dart import Dart

    assert hasattr(Dart, "corpCodes")


def test_document_callable() -> None:
    """document() callable smoke."""
    from dartlab.gather.dart.dart import Dart

    assert hasattr(Dart, "document")


def test_document_text_callable() -> None:
    """documentText() callable smoke."""
    from dartlab.gather.dart.dart import Dart

    assert hasattr(Dart, "documentText")


def test_executive_shares_callable() -> None:
    """executiveShares() callable smoke."""
    from dartlab.gather.dart.dart import Dart

    assert hasattr(Dart, "executiveShares")


def test_filing_types_callable() -> None:
    """filingTypes() callable smoke."""
    from dartlab.gather.dart.dart import Dart

    assert hasattr(Dart, "filingTypes")


def test_filings_callable() -> None:
    """filings() callable smoke."""
    from dartlab.gather.dart.dart import Dart

    assert hasattr(Dart, "filings")


def test_finstate_callable() -> None:
    """finstate() callable smoke."""
    from dartlab.gather.dart.dart import Dart

    assert hasattr(Dart, "finstate")


def test_finstate_multi_callable() -> None:
    """finstateMulti() callable smoke."""
    from dartlab.gather.dart.dart import Dart

    assert hasattr(Dart, "finstateMulti")


def test_major_shareholders_callable() -> None:
    """majorShareholders() callable smoke."""
    from dartlab.gather.dart.dart import Dart

    assert hasattr(Dart, "majorShareholders")


def test_markets_callable() -> None:
    """markets() callable smoke."""
    from dartlab.gather.dart.dart import Dart

    assert hasattr(Dart, "markets")


def test_report_callable() -> None:
    """report() callable smoke."""
    from dartlab.gather.dart.dart import Dart

    assert hasattr(Dart, "report")


def test_report_types_callable() -> None:
    """reportTypes() callable smoke."""
    from dartlab.gather.dart.dart import Dart

    assert hasattr(Dart, "reportTypes")


def test_search_callable() -> None:
    """search() callable smoke."""
    from dartlab.gather.dart.dart import Dart

    assert hasattr(Dart, "search")


def test_xbrl_taxonomy_callable() -> None:
    """xbrlTaxonomy() callable smoke."""
    from dartlab.gather.dart.dart import Dart

    assert hasattr(Dart, "xbrlTaxonomy")


def test_finance_callable() -> None:
    """finance() callable smoke."""
    from dartlab.gather.dart.dart import DartCompany

    assert hasattr(DartCompany, "finance")


def test_info_callable() -> None:
    """info() callable smoke."""
    from dartlab.gather.dart.dart import DartCompany

    assert hasattr(DartCompany, "info")


def test_save_filings_callable() -> None:
    """saveFilings() callable smoke."""
    from dartlab.gather.dart.dart import DartCompany

    assert hasattr(DartCompany, "saveFilings")


def test_save_finance_callable() -> None:
    """saveFinance() callable smoke."""
    from dartlab.gather.dart.dart import DartCompany

    assert hasattr(DartCompany, "saveFinance")


def test_save_report_callable() -> None:
    """saveReport() callable smoke."""
    from dartlab.gather.dart.dart import DartCompany

    assert hasattr(DartCompany, "saveReport")


def test_shares_callable() -> None:
    """shares() callable smoke."""
    from dartlab.gather.dart.dart import DartCompany

    assert hasattr(DartCompany, "shares")


def test_xbrl_callable() -> None:
    """xbrl() callable smoke."""
    from dartlab.gather.dart.dart import DartCompany

    assert hasattr(DartCompany, "xbrl")
