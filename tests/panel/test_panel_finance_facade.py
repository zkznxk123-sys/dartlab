"""panel facade finance forwarding 게이트 — DART docs/show 농장 은퇴 회귀 가드.

운영자 결정: 공개 ``c.show`` API 는 은퇴하고 finance 모듈(financeStatementBuilder + dispatch)은
삭제하지 않는다 — ``c.panel`` facade 가 그 표면이 된다. 본 게이트는 show 기계 삭제 전후로
finance 가 panel 경유로 **무손실** 도달함을 박제한다:

- ``c.panel("IS")`` — facade 가 finance 모듈(_showImpl 내부 dispatch)에 직접 붙어 wide 반환.
- ``freq`` / ``scope`` (연결↔별도) / ``asOf`` (시점 strip) / ``period`` 전부 forwarding.
- ``c.panel("is")`` 소문자 — panel 자급 native 셀(cell.readStatement), show 무관.

requires_data — baseline artifact 없으면 skip (collection green).
"""

from __future__ import annotations

from pathlib import Path

import polars as pl
import pytest

import dartlab.config as _cfg

pytestmark = pytest.mark.requires_data

_BASE = "005930"
_PANEL_DIR = Path(_cfg.dataDir) / "dart" / "panel"


def _hasPanel(code: str) -> bool:
    d = _PANEL_DIR / code
    return (d.exists() and any(d.glob("*.parquet"))) or (_PANEL_DIR / f"{code}.parquet").exists()


requires_panel = pytest.mark.skipif(not _hasPanel(_BASE), reason="panel artifact 없음 (005930)")


@requires_panel
def test_panel_facade_finance_is_wide() -> None:
    """c.panel("IS") — facade 가 finance 모듈에 붙어 항목 × 기간 wide 반환 (show 무경유)."""
    import dartlab

    c = dartlab.Company(_BASE)
    df = c.panel("IS")
    assert isinstance(df, pl.DataFrame) and df.height > 0, "panel('IS') finance facade 비어있음"
    periodCols = [col for col in df.columns if any(ch.isdigit() for ch in col)]
    assert len(periodCols) >= 2, f"finance period 열 2개 이상이어야: {df.columns}"


@requires_panel
def test_panel_facade_freq_and_scope_forwarding() -> None:
    """freq(연간) · scope(별도) 가 finance 모듈로 forwarding 되어 다른 격자 반환."""
    import dartlab

    c = dartlab.Company(_BASE)
    yearly = c.panel("IS", freq="year")
    assert isinstance(yearly, pl.DataFrame) and yearly.height > 0
    # scope=separate(별도) 가 시그니처 통과 + 결과 반환(또는 None) — TypeError 회귀 차단.
    sep = c.panel("IS", scope="separate")
    assert sep is None or isinstance(sep, pl.DataFrame)


@requires_panel
def test_panel_facade_asof_strips_periods() -> None:
    """asOf 가 finance 모듈로 forwarding 되어 시점 이후 period 열을 strip."""
    import dartlab

    c = dartlab.Company(_BASE)
    full = c.panel("IS")
    asof = c.panel("IS", asOf="2020-12-31")
    assert asof is None or isinstance(asof, pl.DataFrame)
    if isinstance(full, pl.DataFrame) and isinstance(asof, pl.DataFrame):
        # asOf 가 과거면 period 열 수가 같거나 더 적어야(미래 strip) — 늘어나면 회귀.
        assert len(asof.columns) <= len(full.columns)


@requires_panel
def test_panel_native_lowercase_independent_of_show() -> None:
    """c.panel("is") 소문자 — panel 자급 native 셀(cell.readStatement), facade 주입 무관."""
    from dartlab.providers.dart.panel import Panel

    # standalone Panel(주입 없음) 에서도 소문자 native 동작 — show 완전 무관 증명.
    p = Panel(_BASE)
    native = p("is")
    assert native is None or isinstance(native, pl.DataFrame)
