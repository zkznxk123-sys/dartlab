"""runtimeProjection.py mirror test."""

import pytest

pytestmark = pytest.mark.unit


def test_imports() -> None:
    """모듈 import smoke."""
    from dartlab.providers.dart.docs.sections import runtimeProjection

    assert hasattr(runtimeProjection, "applyProjections")


def test_apply_projections_callable() -> None:
    """applyProjections() callable smoke."""
    from dartlab.providers.dart.docs.sections.runtimeProjection import applyProjections

    assert callable(applyProjections)
