"""providers/dart/report/types.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.providers.dart.report.types  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")


def test_to_wide_callable() -> None:
    """toWide() callable smoke."""
    from dartlab.providers.dart.report.types import AuditResult

    assert hasattr(AuditResult, "toWide")
