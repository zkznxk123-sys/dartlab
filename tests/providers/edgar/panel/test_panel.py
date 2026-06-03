"""EDGAR panel 공개 계약 — 보드 read + native 셀 dispatch + 배포 config (DART 표면 동형).

build round-trip(합성 원본→build→Panel(us)) + us native 라우팅(_nativeFn) + isStrongTopic + 배포 config.
"""

from __future__ import annotations

import functools

import polars as pl
import pytest

pytestmark = pytest.mark.unit


def test_panel_us_build_roundtrip(builtTicker) -> None:
    """합성 원본 → build → Panel(us) 보드 wide + 재무표 검색 + 본문검색."""
    from dartlab.providers.dart.panel import Panel
    from dartlab.providers.edgar.panel.build.builder import buildEdgarPanel

    buildEdgarPanel(builtTicker)
    p = Panel(builtTicker, marketNs="us")
    assert isinstance(p, pl.DataFrame) and not p.is_empty()
    for col in ("chapter", "sectionLeaf", "disclosureKey", "scope"):
        assert col in p.columns
    assert "2024Q4" in p.columns
    # 재무표 disclosureKey 행 검색
    assert p("BS") is not None
    # 서술 본문 전체검색
    assert p.search("widgets") is not None
    # EDGAR 연결-only → scope consolidated
    assert set(p["scope"].unique().to_list()) == {"consolidated"}


def test_panel_us_native_cell_contract(builtTicker) -> None:
    """c.panel("is") (facade _nativeFn 주입) → DART 계약 [account, label, *period]."""
    from dartlab.providers.dart.panel import Panel
    from dartlab.providers.edgar.panel import cellRead
    from dartlab.providers.edgar.panel.build.builder import buildEdgarPanel

    buildEdgarPanel(builtTicker)
    p = Panel(builtTicker, marketNs="us")
    p._nativeFn = functools.partial(cellRead.readNative, builtTicker)  # facade 주입 미러
    # 합성 원본은 연간(10-K)만 → freq="year" (분기 데이터 없음, quarter 면 정상적으로 빈손)
    isw = p("is", freq="year")
    assert isw is not None and isw.columns[:2] == ["account", "label"]
    assert "2024" in isw.columns
    bsw = p("bs", freq="year")
    assert bsw is not None and bsw.columns[:2] == ["account", "label"]


def test_panel_us_dispatch_native_vs_finance() -> None:
    """us: 소문자=native(_nativeFn) / 대문자=finance(_showFn) — DART native/finance 대칭 (data 0)."""
    from dartlab.providers.dart.panel import Panel

    p = Panel("000000nonexistent", marketNs="us")
    p._nativeFn = lambda statement, freq, periods: f"native:{statement}:{freq}"
    p._showFn = lambda topic, **kw: f"fin:{topic}"
    p._strongFn = lambda t: t.upper() in {"IS", "BS", "CF", "CIS", "SCE", "RATIOS"}

    assert p("is") == "native:is:quarter"  # 소문자 native → _nativeFn
    assert p("bs") == "native:bs:quarter"
    assert p("ratios") == "native:ratios:quarter"
    assert p("IS") == "fin:IS"  # 대문자 → companyfacts(finance)
    assert p("RATIOS") == "fin:ratios"
    assert p("Risk") is None  # 약한 소스 → board(artifact 없어 None)


def test_is_strong_topic_edgar() -> None:
    from dartlab.providers.edgar.builder.dataDispatcher import isStrongTopic

    assert isStrongTopic("IS") and isStrongTopic("is") and isStrongTopic("RATIOS") and isStrongTopic("ratios")
    assert not isStrongTopic("Risk") and not isStrongTopic("item1Business") and not isStrongTopic("")


def test_edgar_panel_distribution_config() -> None:
    """edgarPanel + edgarPanelCell DATA_RELEASES + deploy _CATEGORY_MAP 배선."""
    from dartlab.core.dataConfig import DATA_RELEASES, repoFor
    from dartlab.providers.edgar.openapi.deploy import _CATEGORY_MAP

    assert DATA_RELEASES["edgarPanel"]["dir"] == "edgar/panel"
    assert DATA_RELEASES["edgarPanelCell"]["dir"] == "edgar/panelCell"
    assert _CATEGORY_MAP["panel"] == "edgarPanel" and _CATEGORY_MAP["panelCell"] == "edgarPanelCell"
    assert repoFor("edgarPanel") and repoFor("edgarPanelCell")


def test_panel_us_ticker_case_insensitive(builtTicker) -> None:
    """Panel("test", marketNs="us") 소문자도 TEST artifact 해석."""
    from dartlab.providers.dart.panel import Panel
    from dartlab.providers.edgar.panel.build.builder import buildEdgarPanel

    buildEdgarPanel(builtTicker)
    p = Panel("test", marketNs="us")
    assert not p.is_empty()
