"""R34 audit 회귀 — guide handleError feature 전달."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


def test_guide_handle_error_with_feature_includes_feature_label():
    """R34-1: feature 인자 전달 시 결과에 [feature] prefix 포함."""
    import dartlab
    msg = dartlab.guide.handleError(ValueError('test'), feature='ai')
    assert "[ai]" in msg
    assert "checkReady" in msg or "whatCanIDo" in msg


def test_guide_handle_error_without_feature_no_prefix():
    """feature 없으면 prefix 없음."""
    import dartlab
    msg = dartlab.guide.handleError(ValueError('test'))
    assert "[ai]" not in msg
    assert "ValueError" in msg


def test_guide_check_ready_returns_result_object():
    """checkReady 가 ReadinessResult 반환 (회귀 보호)."""
    import dartlab
    r = dartlab.guide.checkReady('ai')
    assert hasattr(r, 'feature')
    assert hasattr(r, 'status')
    assert r.feature == 'ai'


def test_guide_what_can_i_do_returns_str():
    """whatCanIDo 가 str 반환 (회귀 보호)."""
    import dartlab
    r = dartlab.guide.whatCanIDo('재무 분석')
    assert isinstance(r, str)
    assert len(r) > 0
