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
    from dartlab.gather.dart.panel.build.refScan.refMatcher import (
        precomputeRefTokens,
        setGlobalRefTokens,
    )

    assert callable(precomputeRefTokens)
    assert callable(setGlobalRefTokens)
