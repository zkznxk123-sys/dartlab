"""R31 audit 회귀 테스트 — story 엔진.

R31-1: c.story('없는섹션') silent 빈 Story → ValueError
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


def test_review_buildreview_validates_section():
    """R31-1: buildStory 에 section 검증 코드가 있는지 source check."""
    import inspect

    from dartlab.story.registry import buildStory

    src = inspect.getsource(buildStory)
    assert "section not in TEMPLATES" in src
    assert "ValueError" in src


def test_review_templates_registry_has_keys():
    """TEMPLATES 가 비어 있지 않음."""
    from dartlab.story.registry import TEMPLATES

    assert isinstance(TEMPLATES, dict)
    assert len(TEMPLATES) >= 5


def test_review_unknown_preset_raises():
    """preset deprecated → type 매핑. 알 수 없는 type은 ValueError."""
    from dartlab.story.reportTypes import resolveReportType

    with pytest.raises(ValueError):
        resolveReportType("nonexistent_type_xyz")
