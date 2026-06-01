"""panel spineBuilder mirror — 순수 헬퍼(consensus·render) 합성 검증 (데이터 0).

``build/spineBuilder.py`` 의 ``_consensus``(median rank)/``_renderModule``(생성 소스)/공개
``buildSpine`` 표면. 실 zip→spine 빌드(최신 사업보고서 파싱)는 requires_data 라 제외 —
순수 집계·직렬화 로직만 합성 입력으로 검증.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


def test_build_spine_public_callable() -> None:
    """buildSpine 공개표면 존재 (build/__init__ export)."""
    from dartlab.providers.dart.panel.build import buildSpine

    assert callable(buildSpine)


def test_consensus_single_company_preserves_order() -> None:
    """단일 종목 → 그 회사 문서순서 그대로 (spineOrder 0..N 재부여)."""
    from dartlab.providers.dart.panel.build.spineBuilder import _consensus

    company = [
        ("NARR::I␟I", 0, None, 0),
        ("BS", 1, None, 1),
        ("NT_D826380", 2, None, 1),
    ]
    out = _consensus([company])
    assert [r[0] for r in out] == ["NARR::I␟I", "BS", "NT_D826380"]
    assert [r[1] for r in out] == [0, 1, 2]  # spineOrder 0..N


def test_consensus_median_rank_across_companies() -> None:
    """다종목 → identity 별 (chapterRank, order) median 정렬 → spineOrder 재부여."""
    from dartlab.providers.dart.panel.build.spineBuilder import _consensus

    # A 에서 X 가 BS 앞, B 에서 X 가 BS 뒤 → median 으로 안정 정렬.
    a = [("BS", 0, None, 0), ("X", 1, None, 0)]
    b = [("X", 0, None, 0), ("BS", 1, None, 0)]
    c = [("BS", 0, None, 0), ("X", 1, None, 0)]
    out = _consensus([a, b, c])
    idents = [r[0] for r in out]
    # BS median order = median(0,1,0)=0, X = median(1,0,1)=1 → BS 먼저.
    assert idents == ["BS", "X"]
    assert [r[1] for r in out] == [0, 1]


def test_consensus_parent_first_nonnull() -> None:
    """parentKey 는 회사 가로질러 첫 non-null 채택 (트리 안정)."""
    from dartlab.providers.dart.panel.build.spineBuilder import _consensus

    a = [("NT_D826380", 0, None, 0)]
    b = [("NT_D826380", 0, "NT_D810000", 0)]
    out = _consensus([a, b])
    assert out[0][2] == "NT_D810000"


def test_consensus_empty() -> None:
    """빈 입력 → 빈 spine."""
    from dartlab.providers.dart.panel.build.spineBuilder import _consensus

    assert _consensus([]) == []


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
