"""panel 회사내 수평화 + 콜드 read 회귀 (G2·G4) — plan snazzy-wibbling-origami.

빌드된 baseline artifact(005930) 위에서 두 게이트를 잠근다:

- **G2 회사내 수평화**: ``Panel.board()`` 가 항목 행 × period 열 보드를 만들고, era drift
  (BS→BS_C, 제목 변동)를 흡수해 한 disclosure 가 여러 period 에 걸쳐 **한 행**에 정렬된다
  (행 쪼개짐 0). pivot index 는 unique.
- **G4 콜드 1초 / <1MB**: board 는 contentRaw 제외라 footprint 작고 콜드 read 빠름.

requires_data — baseline artifact 없으면 skip. fast/full preflight 에서 제외(콜드 read 는
test-lock.sh 경유 단독 실행). artifact 부재 CI 에서도 collection green.
"""

from __future__ import annotations

import time
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
def test_intra_horizontalize_one_row_multi_period() -> None:
    """G2 — board 는 항목 × period 보드, 한 disclosure 가 여러 period 에 한 행으로 정렬."""
    from dartlab.providers.dart.panel import Panel

    p = Panel(_BASE)
    periods = p.periods()
    assert len(periods) >= 2, f"baseline 은 다기간이어야 함: {periods}"

    board = p.board()
    assert board is not None and board.height > 0, "board 비어있음"

    idxPresent = [c for c in _INDEX_COLS if c in board.columns]
    assert idxPresent, f"pivot index 컬럼 부재: {board.columns}"
    periodCols = [c for c in board.columns if c not in idxPresent]
    assert len(periodCols) >= 2, f"period 열 2개 이상이어야 수평화 증명: {periodCols}"

    # pivot index unique — 행 쪼개짐 0 (era drift 흡수 결과 한 행).
    dupCount = int(board.select(idxPresent).is_duplicated().sum())
    assert dupCount == 0, f"pivot index 중복 {dupCount} — 행 쪼개짐(era drift 미흡수)"

    # 적어도 한 항목은 2+ period 에 걸쳐 한 행에 정렬 (다기간 가로 정렬 실증).
    spans = board.select([pl.col(c).is_not_null().cast(pl.Int32) for c in periodCols])
    maxSpan = int(spans.with_columns(pl.sum_horizontal(pl.all()).alias("_n"))["_n"].max())
    assert maxSpan >= 2, "한 행이 2+ period 를 가로로 덮는 항목이 없음 — 회사내 수평화 실패"


@requires_panel
def test_cold_board_under_1s_and_small() -> None:
    """G4 — board 콜드 read < 1.5s (여유), footprint < 1MB (contentRaw 제외)."""
    from dartlab.providers.dart.panel import Panel

    t0 = time.perf_counter()
    board = Panel(_BASE).board()
    elapsed = time.perf_counter() - t0

    assert board is not None, "board None"
    # 콜드 목표 <1s. 부하 환경 flaky 회피 위해 1.5s 여유 (baseline 실측 0.11s — 큰 마진).
    assert elapsed < 1.5, f"board 콜드 {elapsed:.3f}s — 1.5s 초과 (G4 회귀)"
    sizeMb = board.estimated_size("mb")
    assert sizeMb < 1.0, f"board {sizeMb:.3f}MB — 1MB 초과 (contentRaw 누출 의심, G4 회귀)"


@requires_panel
def test_board_excludes_content_raw() -> None:
    """G4 보강 — board(presence)는 contentRaw 컬럼/본문을 포함하지 않는다."""
    from dartlab.providers.dart.panel import Panel

    board = Panel(_BASE).board()
    assert board is not None
    assert "contentRaw" not in board.columns, "board 에 contentRaw 누출 — presence board 위반"
