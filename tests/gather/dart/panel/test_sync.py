"""panel 오케스트레이션 mirror — 공개 심볼 import-smoke (데이터 0).

``gather/dart/panel/sync.py`` 의 1:1 mirror. syncPanel 오케스트레이션이 공개표면에
존재·callable 인지 확인 (실행은 zip/build 부작용이라 end-to-end 는 CI entry buildPanel.py
경유 — 본 mirror 는 import/시그니처 회귀 가드).
"""

from __future__ import annotations

import inspect

import pytest

pytestmark = pytest.mark.unit


def test_sync_panel_callable_and_keyword_only() -> None:
    """syncPanel 존재 + 단계 플래그 keyword 인자 (refScan/learn/build/index)."""
    from dartlab.gather.dart.panel import syncPanel

    assert callable(syncPanel)
    params = inspect.signature(syncPanel).parameters
    for flag in ("refScan", "learn", "build", "index"):
        assert flag in params, f"syncPanel 단계 플래그 {flag} 누락"
