"""R37 audit 회귀 — export + audit + display 보조 엔진.

R37 audit: 3 모듈 모두 import 정상. 안정화 KPI 1 만족.
회귀 보호.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


def test_export_module_loads():
    """dartlab.export import + 핵심 함수."""
    from dartlab import export

    assert hasattr(export, "exportToExcel")
    assert hasattr(export, "excel")


def test_display_module_loads():
    """dartlab.display import + 핵심 함수."""
    from dartlab import display

    assert hasattr(display, "renderCompany")
    assert hasattr(display, "renderFinance")


def test_audit_module_loads():
    """dartlab.audit import + 핵심 함수."""
    from dartlab import audit

    assert hasattr(audit, "runAudit")
    assert hasattr(audit, "queryAudit")
