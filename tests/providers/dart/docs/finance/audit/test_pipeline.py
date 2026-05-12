"""providers/dart/docs/finance/audit/pipeline.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.providers.dart.docs.finance.audit.pipeline  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")


def test_audit_callable() -> None:
    """audit() callable smoke."""
    from dartlab.providers.dart.docs.finance.audit.pipeline import audit

    assert callable(audit)
