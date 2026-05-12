"""providers/dart/docs/finance/auditSystem.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.providers.dart.docs.finance.auditSystem  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")


def test_audit_system_callable() -> None:
    """auditSystem() callable smoke."""
    from dartlab.providers.dart.docs.finance.auditSystem import auditSystem

    assert callable(auditSystem)


def test_is_separator_row_callable() -> None:
    """isSeparatorRow() callable smoke."""
    from dartlab.providers.dart.docs.finance.auditSystem import isSeparatorRow

    assert callable(isSeparatorRow)


def test_parse_audit_activity_callable() -> None:
    """parseAuditActivity() callable smoke."""
    from dartlab.providers.dart.docs.finance.auditSystem import parseAuditActivity

    assert callable(parseAuditActivity)


def test_parse_audit_committee_callable() -> None:
    """parseAuditCommittee() callable smoke."""
    from dartlab.providers.dart.docs.finance.auditSystem import parseAuditCommittee

    assert callable(parseAuditCommittee)


def test_split_cells_callable() -> None:
    """splitCells() callable smoke."""
    from dartlab.providers.dart.docs.finance.auditSystem import splitCells

    assert callable(splitCells)
