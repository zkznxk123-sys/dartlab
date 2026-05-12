"""providers/edgar/report/auditOpinion.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.providers.edgar.report.auditOpinion  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")


def test_extract_audit_opinion_callable() -> None:
    """extractAuditOpinion() callable smoke."""
    from dartlab.providers.edgar.report.auditOpinion import extractAuditOpinion

    assert callable(extractAuditOpinion)
