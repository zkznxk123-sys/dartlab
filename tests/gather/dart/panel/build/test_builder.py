"""panel builder mirror — 순수 헬퍼 + artifact 부재 빈 dict (데이터 0).

``gather/dart/panel/build/builder.py`` 의 1:1 mirror. 순수 _prevYear 와 zip 없는 종목의
빈 dict 경로를 검증. 실 zip→14col 빌드(손실0/dup0)는 tests/panel/test_build_lossless.py
(requires_data, heavy) 담당.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


def test_prev_year() -> None:
    """_prevYear: 연도 문자열 → 직전 연도 (변환 실패 시 원본)."""
    from dartlab.gather.dart.panel.build.builder import _prevYear

    assert _prevYear("2024") == "2023"
    assert _prevYear("abcd") == "abcd"


def test_build_callables_public() -> None:
    """buildPanel/buildPanelAll/buildPanelBaseline 공개표면 존재."""
    from dartlab.gather.dart.panel import buildPanel, buildPanelAll, buildPanelBaseline

    assert callable(buildPanel)
    assert callable(buildPanelAll)
    assert callable(buildPanelBaseline)
