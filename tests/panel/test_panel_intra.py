"""panel 회사내 수평화 실데이터 게이트 (G2) — PRD jazzy-napping-seal.

빌드된 baseline artifact(005930) 위에서 단일 표면 ``Panel`` 을 검증:

- **잡는 순간 wide**: ``Panel(code)`` 가 곧 pl.DataFrame (항목 행 × period 열). era drift
  (BS→BS_C, 제목 변동)를 흡수해 한 disclosure 가 여러 period 에 한 행으로 정렬(행 쪼개짐 0).
- **callable 검색**: ``Panel(code)("재고")`` 가 섹션명 매칭 행을 반환.
- **tag**: 기본 plain(태그 제거), ``tag=True`` 면 원본 XML(``<`` 태그 보존) → 무손실(R4).

requires_data — baseline artifact 없으면 skip. artifact 부재 CI 에서도 collection green.
"""

from __future__ import annotations

from pathlib import Path

import polars as pl
import pytest

import dartlab.config as _cfg

pytestmark = pytest.mark.requires_data

_BASE = "005930"
_PANEL_DIR = Path(_cfg.dataDir) / "dart" / "panel"
_INDEX_COLS = ("chapter", "sectionLeaf", "blockLeaf", "disclosureKey", "scope")


def _hasPanel(code: str) -> bool:
    d = _PANEL_DIR / code
    return d.exists() and any(d.glob("*.parquet"))


requires_panel = pytest.mark.skipif(not _hasPanel(_BASE), reason="panel artifact 없음 (005930)")


@requires_panel
def test_panel_is_wide_one_row_multi_period() -> None:
    """G2 — Panel(code) 가 곧 wide, 한 disclosure 가 여러 period 에 한 행으로 정렬."""
    from dartlab.providers.dart.panel import Panel

    p = Panel(_BASE)
    assert isinstance(p, pl.DataFrame)
    assert p.height > 0, "Panel 비어있음"

    idxPresent = [c for c in _INDEX_COLS if c in p.columns]
    assert idxPresent, f"pivot index 컬럼 부재: {p.columns}"
    periodCols = [c for c in p.columns if c not in idxPresent]
    assert len(periodCols) >= 2, f"period 열 2개 이상이어야 수평화 증명: {periodCols}"

    # pivot index unique — 행 쪼개짐 0 (era drift 흡수 결과 한 행).
    dupCount = int(p.select(idxPresent).is_duplicated().sum())
    assert dupCount == 0, f"pivot index 중복 {dupCount} — 행 쪼개짐(era drift 미흡수)"

    # 적어도 한 항목은 2+ period 에 걸쳐 한 행에 정렬 (다기간 가로 정렬 실증).
    spans = p.select([pl.col(c).is_not_null().cast(pl.Int32) for c in periodCols])
    maxSpan = int(spans.with_columns(pl.sum_horizontal(pl.all()).alias("_n"))["_n"].max())
    assert maxSpan >= 2, "한 행이 2+ period 를 가로로 덮는 항목이 없음 — 회사내 수평화 실패"


@requires_panel
def test_panel_call_filters_section_rows() -> None:
    """callable — Panel(code)("재고") 가 섹션명 매칭 행만 반환(전체보다 작음)."""
    from dartlab.providers.dart.panel import Panel

    p = Panel(_BASE)
    rows = p("재고")
    if rows is None:  # baseline 에 '재고' 섹션 부재 가능 — skip 대신 관대
        pytest.skip("baseline 에 '재고' 매칭 섹션 없음")
    assert rows.height >= 1
    assert rows.height <= p.height
    # 매칭 행은 sectionLeaf/blockLeaf 에 '재고' 포함 또는 disclosureKey exact.
    leafHit = rows.select(
        (
            pl.col("sectionLeaf").str.contains("재고", literal=True)
            | pl.col("blockLeaf").str.contains("재고", literal=True)
        )
        if "sectionLeaf" in rows.columns
        else pl.lit(True)
    ).to_series()
    assert bool(leafHit.any())


@requires_panel
def test_panel_tag_default_strips_raw_preserves() -> None:
    """tag — 기본 plain(태그 제거), tag=True 면 원본 XML(< 태그 보존)."""
    from dartlab.providers.dart.panel import Panel

    plain = Panel(_BASE)  # tag=False 기본
    raw = Panel(_BASE, tag=True)
    periodCols = [c for c in plain.columns if c not in _INDEX_COLS]
    assert periodCols, "period 열 없음"
    col = periodCols[0]

    rawJoined = "".join(v for v in raw[col].to_list() if v)
    plainJoined = "".join(v for v in plain[col].to_list() if v)
    assert "<" in rawJoined, "tag=True 인데 XML 태그 없음 — 무손실 위반"
    assert "<" not in plainJoined, "tag=False(기본) 인데 태그 잔존 — strip 실패"
    # plain 은 raw 보다 작다 (태그 제거 → 바이트 감소).
    assert len(plainJoined) < len(rawJoined)
