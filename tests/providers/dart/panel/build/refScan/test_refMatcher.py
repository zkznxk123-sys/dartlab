"""refMatcher mirror — 공개 심볼 import-smoke (데이터 0).

``gather/dart/panel/build/refScan/refMatcher.py`` 의 1:1 mirror. 옛 양식 fuzzy 매칭 가속
함수(token pre-compute)가 존재·callable 인지 확인. 실 매칭은 ref + global token state 가
필요해 build 경로에서 검증 — 본 mirror 는 import/심볼 회귀 가드.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


def test_ref_matcher_symbols_callable() -> None:
    """precomputeRefTokens / setGlobalRefTokens 존재 + callable (builder 가 의존)."""
    from dartlab.providers.dart.panel.build.refScan.refMatcher import (
        precomputeRefTokens,
        setGlobalRefTokens,
    )

    assert callable(precomputeRefTokens)
    assert callable(setGlobalRefTokens)


def test_match_to_ref_empty_title_guard() -> None:
    """matchToRef: 빈 title → (None, 0.0) (global state 무관 deterministic)."""
    import polars as pl

    from dartlab.providers.dart.panel.build.refScan.refMatcher import matchToRef

    ref = pl.DataFrame(
        {"rawId": [], "rawTitleCanonical": [], "corpCount": []},
        schema={"rawId": pl.Utf8, "rawTitleCanonical": pl.Utf8, "corpCount": pl.Int64},
    )
    assert matchToRef("", ref) == (None, 0.0)


def test_evaluate_threshold_callable() -> None:
    """evaluateThreshold 공개표면 존재 (threshold sweep 평가)."""
    from dartlab.providers.dart.panel.build.refScan.refMatcher import evaluateThreshold

    assert callable(evaluateThreshold)
