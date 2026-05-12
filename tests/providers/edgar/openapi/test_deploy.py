"""providers/edgar/openapi/deploy.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.providers.edgar.openapi.deploy  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")


def test_deploy_edgar_to_h_f_callable() -> None:
    """deployEdgarToHF() callable smoke."""
    from dartlab.providers.edgar.openapi.deploy import deployEdgarToHF

    assert callable(deployEdgarToHF)
