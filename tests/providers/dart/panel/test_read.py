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
