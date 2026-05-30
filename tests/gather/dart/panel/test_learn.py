"""panel bridge-learning mirror — 공개 심볼 import-smoke (데이터 0).

``gather/dart/panel/learn.py`` 의 1:1 mirror. learnBridge/bridgeCoverage 가 공개표면에
존재·callable 인지 확인 (실제 학습은 panelXbrlRef + 부작용 write 라 requires_data 통합 검증
대상 — 본 mirror 는 import 회귀 가드).
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


def test_learn_public_symbols_callable() -> None:
    """learnBridge / bridgeCoverage 공개표면 존재 + callable."""
    from dartlab.gather.dart.panel import bridgeCoverage, learnBridge

    assert callable(learnBridge)
    assert callable(bridgeCoverage)
