"""R37 audit 회귀 — export + audit + display 보조 엔진.

R37 audit: 3 모듈 모두 import 정상. 안정화 KPI 1 만족.
회귀 보호.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


def test_export_module_loads():
    """dartlab.viz.export import + 핵심 함수."""
    from dartlab.viz import export

    assert hasattr(export, "exportToExcel")
    assert hasattr(export, "excel")


def test_display_module_loads():
    """dartlab.viz.display import + 핵심 함수."""
    from dartlab.viz import display

    assert hasattr(display, "renderCompany")
    assert hasattr(display, "renderFinance")


def test_ai_audit_legacy_surface_removed():
    """AI audit compatibility stubs are not part of the production surface."""

    with pytest.raises(ModuleNotFoundError):
        import dartlab.ai.audit  # noqa: F401
