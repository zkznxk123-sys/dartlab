"""panel spineBuilder mirror — 순수 헬퍼(render) + 공개표면 합성 검증 (데이터 0).

``build/spineBuilder.py`` 의 ``_renderModule``(생성 소스)/공개 ``buildSpine`` 표면. 실 zip→spine
빌드(최신 사업보고서 파싱)는 requires_data 라 제외 — 직렬화 로직만 합성 입력으로 검증. spine 은
한 회사 reference 순서(회사간 합의는 panel 책임 밖 = scan 엔진).
"""

from __future__ import annotations

import inspect

import pytest

pytestmark = pytest.mark.unit


def test_build_spine_public_callable_single_code() -> None:
    """buildSpine 공개표면 존재 + 단일 code 시그니처 (다종목 codes·consensus 제거)."""
    from dartlab.providers.dart.panel.build import buildSpine, spineBuilder

    assert callable(buildSpine)
    params = inspect.signature(buildSpine).parameters
    assert "code" in params and "codes" not in params  # 단일 회사 reference
    assert not hasattr(spineBuilder, "_consensus")  # 다종목 median 합의 제거


def test_render_module_valid_python_and_importable() -> None:
    """_renderModule 출력 = valid python, exec 시 SPINE_ROWS 복원."""
    from dartlab.providers.dart.panel.build.spineBuilder import _renderModule

    rows = [
        ("NARR::I␟1. 회사의 개요", 0, None, 0),
        ("NT_D826380", 1, "NT_D810000", 1),
    ]
    src = _renderModule(rows)
    assert "SPINE_ROWS" in src
    ns: dict = {}
    exec(compile(src, "<spineData>", "exec"), ns)
    assert ns["SPINE_ROWS"] == tuple(rows)


def test_render_module_double_quote_korean() -> None:
    """한국어 identity 는 double-quote 직렬화 (ruff 정본, 재포맷 0)."""
    from dartlab.providers.dart.panel.build.spineBuilder import _renderModule

    src = _renderModule([("NARR::I. 회사의 개요␟1. 회사의 개요", 0, None, 0)])
    assert '"NARR::I. 회사의 개요␟1. 회사의 개요"' in src
    assert "'NARR::" not in src  # single-quote 0
