"""R31 audit 회귀 테스트 — review 엔진.

R31-1: c.review('없는섹션') silent 빈 Review → ValueError
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


def test_review_buildreview_validates_section():
    """R31-1: buildReview 에 section 검증 코드가 있는지 source check."""
    import inspect

    from dartlab.review.registry import buildReview

    src = inspect.getsource(buildReview)
    assert "section not in TEMPLATES" in src
    assert "ValueError" in src
    assert "찾을 수 없" in src


def test_review_templates_registry_has_keys():
    """TEMPLATES 가 비어 있지 않음."""
    from dartlab.review.registry import TEMPLATES

    assert isinstance(TEMPLATES, dict)
    assert len(TEMPLATES) >= 5
    assert "수익성" in TEMPLATES or "수익구조" in TEMPLATES


def test_review_unknown_preset_raises():
    """기존 동작 — 없는 preset 은 ValueError (회귀 보호)."""
    import inspect

    from dartlab.review.registry import buildReview

    from dartlab.review.reportTypes import resolveReportType

    src = inspect.getsource(resolveReportType)
    assert "알 수 ���는 보고서 타입" in src
