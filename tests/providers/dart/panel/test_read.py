"""panel read 엔진 mirror — scope/anchor/long/wide 순수 단위 (데이터 0).

``providers/dart/panel/read.py`` 의 1:1 mirror. scopeExpr(연결/별도)·anchorLatest(era drift
최신기준 정렬)는 합성 DataFrame 으로, _panelDir/readLong/readWide 는 artifact 부재 None 경로로
검증 (read 표면 network/lxml 0, R2). 실데이터 수평화는 tests/panel/test_panel_intra.py 담당.
"""

from __future__ import annotations

import polars as pl
import pytest

pytestmark = pytest.mark.unit


def test_scope_expr_consolidated_standalone() -> None:
    """xbrlClass → scope: _S=standalone, 그 외/None=consolidated."""
    from dartlab.providers.dart.panel.read import scopeExpr

    df = pl.DataFrame({"xbrlClass": ["BS_C", "BS_S", "BS", "NT_S_D826385", None]})
    assert df.select(scopeExpr())["scope"].to_list() == [
        "consolidated",
        "standalone",
        "consolidated",
        "standalone",
        "consolidated",
    ]


def test_anchor_latest_propagates_latest_label() -> None:
    """(disclosureKey, scope) 그룹의 최신 period 라벨을 과거 기간에 덮어쓴다 (한 행 정렬)."""
    from dartlab.providers.dart.panel.read import anchorLatest

    df = pl.DataFrame(
        {
            "disclosureKey": ["inv", "inv"],
            "period": ["2023Q4", "2024Q4"],
            "chapter": ["A", "A"],
            "sectionLeaf": ["oldName", "newName"],
            "blockLeaf": ["", ""],
            "xbrlClass": ["NT_C", "NT_C"],
        }
    )
    out = anchorLatest(df)
    assert "scope" in out.columns
    # 최신(2024Q4) 라벨 newName 이 두 기간 모두에 통일 → era drift 흡수.
    assert set(out["sectionLeaf"].to_list()) == {"newName"}


def test_anchor_latest_passthrough_when_no_key() -> None:
    """disclosureKey 컬럼 부재 시 원본 그대로 (방어)."""
    from dartlab.providers.dart.panel.read import anchorLatest

    df = pl.DataFrame({"period": ["2024Q4"], "chapter": ["A"]})
    assert anchorLatest(df).equals(df)


def test_panel_dir_path_market_namespace() -> None:
    """_panelDir: kr→dart/panel, us→edgar/panel."""
    from dartlab.providers.dart.panel.read import _panelDir

    assert _panelDir("005930", "kr").as_posix().endswith("dart/panel/005930")
    assert _panelDir("AAPL", "us").as_posix().endswith("edgar/panel/AAPL")


def test_read_long_and_wide_none_when_absent() -> None:
    """artifact 없는 종목 → readLong/readWide 모두 None (데이터 로드 0)."""
    from dartlab.providers.dart.panel.read import readLong, readWide

    assert readLong("000000nonexistent") is None
    assert readWide("000000nonexistent") is None
    assert readWide("000000nonexistent", tag=False) is None


def test_order_by_spine_period_columns_latest_first() -> None:
    """orderBySpine: period 열 최신순(내림차순) 배치, index 컬럼 먼저."""
    from dartlab.providers.dart.panel.read import orderBySpine

    wide = pl.DataFrame(
        {
            "chapter": ["I. 회사의 개요"],
            "sectionLeaf": ["1. 회사의 개요"],
            "disclosureKey": [None],
            "2015Q4": ["a"],
            "2026Q1": ["b"],
            "2020Q2": ["c"],
        }
    )
    out = orderBySpine(wide, ["chapter", "sectionLeaf", "disclosureKey"])
    periodCols = [c for c in out.columns if c[:4].isdigit()]
    assert periodCols == ["2026Q1", "2020Q2", "2015Q4"]  # 최신순
    assert out.columns[:3] == ["chapter", "sectionLeaf", "disclosureKey"]  # index 먼저


def test_order_by_spine_government_order() -> None:
    """orderBySpine: SPINE 등재 행을 (chapterRank, spineOrder) 정부순서로 정렬."""
    from dartlab.providers.dart.panel.read import orderBySpine
    from dartlab.providers.dart.panel.spine import SPINE, spineOrderOf

    if not SPINE:
        pytest.skip("spineData 비어있음 (buildSpine 미실행)")
    # 정부순서상 재고(NT_D826380)보다 뒤인 항목을 일부러 앞 행에 두고 정렬 복원 확인.
    later = next((k for k in SPINE if (spineOrderOf(k) or 0) > (spineOrderOf("NT_D826380") or 0)), None)
    if later is None or later.startswith("NARR::"):
        pytest.skip("비교 대상 keyed 항목 부족")
    wide = pl.DataFrame(
        {
            "chapter": ["III. 재무에 관한 사항", "III. 재무에 관한 사항"],
            "sectionLeaf": ["x", "y"],
            "disclosureKey": [later, "NT_D826380"],
            "2026Q1": ["a", "b"],
        }
    )
    out = orderBySpine(wide, ["chapter", "sectionLeaf", "disclosureKey"])
    # spineOrder 작은 NT_D826380 이 later 보다 먼저.
    assert out["disclosureKey"].to_list() == ["NT_D826380", later]


def test_order_by_spine_unranked_rows_last() -> None:
    """orderBySpine: SPINE 미등재 행은 chapter 말미(nulls_last)."""
    from dartlab.providers.dart.panel.read import orderBySpine
    from dartlab.providers.dart.panel.spine import SPINE

    if not SPINE:
        pytest.skip("spineData 비어있음")
    wide = pl.DataFrame(
        {
            "chapter": ["I. 회사의 개요", "I. 회사의 개요"],
            "sectionLeaf": ["__unranked__", "1. 회사의 개요"],
            "disclosureKey": ["__NOT_IN_SPINE__", None],
            "2026Q1": ["a", "b"],
        }
    )
    out = orderBySpine(wide, ["chapter", "sectionLeaf", "disclosureKey"])
    # 등재된 narrative(1.회사의 개요)가 미등재(__unranked__)보다 먼저.
    assert out["disclosureKey"].to_list()[-1] == "__NOT_IN_SPINE__"
