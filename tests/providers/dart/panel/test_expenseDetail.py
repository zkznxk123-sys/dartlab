"""panel.expenseDetail 추출 검증 — core 순수성·R1(finance import 0)·OUTPUT_SCHEMA 23컬럼.

비용 주석 추출(readNoteBlocks → expenseDetailRows)이 finance 결합 전 단계에서 23컬럼 long 을
내고, panel 레이어가 finance 를 import 하지 않는지(by-nature 설계 정당성) 게이트한다.

데이터 없으면 skip. 종목 로드는 module-scope fixture(OOM 가드).
"""

from __future__ import annotations

import ast
from pathlib import Path

import polars as pl
import pytest

pytestmark = pytest.mark.unit

_SRC = Path(__file__).resolve().parents[4] / "src" / "dartlab"
_CORE = _SRC / "core" / "accounts" / "expenseDetail.py"
_PANEL = _SRC / "providers" / "dart" / "panel" / "expenseDetail.py"


@pytest.fixture(scope="module")
def rows() -> pl.DataFrame | None:
    """제조(005930) 비용상세 panel 추출 1회 로드 — 데이터 없으면 None."""
    try:
        from dartlab.providers.dart.panel.expenseDetail import expenseDetailRows

        return expenseDetailRows("005930")
    except (ValueError, FileNotFoundError, OSError) as exc:
        pytest.skip(f"panel expenseDetail requires data ({exc})")
        return None


def test_core_layer_purity() -> None:
    """core(L0)는 polars/dartlab 를 import 하지 않는 순수 SSOT(AST 검사)."""
    hits: list[str] = []
    for node in ast.walk(ast.parse(_CORE.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            hits += [n.name for n in node.names if n.name.split(".")[0] in {"polars", "dartlab"}]
        elif isinstance(node, ast.ImportFrom):
            if (node.module or "").split(".")[0] in {"polars", "dartlab"}:
                hits.append(node.module or "")
    assert not hits, f"core 순수성 위반: {hits}"


def test_panel_no_finance_import() -> None:
    """panel(L1)은 finance 를 import 하지 않는다(R1 — by-nature 설계 정당성 가드)."""
    finance = [
        (node.module or "")
        for node in ast.walk(ast.parse(_PANEL.read_text(encoding="utf-8")))
        if isinstance(node, ast.ImportFrom) and "finance" in (node.module or "")
    ]
    assert not finance, f"panel 이 finance 를 import 함(R1 위반): {finance}"


def test_output_schema_23(rows: pl.DataFrame | None) -> None:
    """expenseDetailRows 컬럼이 OUTPUT_SCHEMA 23 과 정확 일치 + reconciledTarget 포함."""
    from dartlab.core.accounts.expenseDetail import OUTPUT_SCHEMA

    expected = [column.column for column in OUTPUT_SCHEMA]
    assert len(expected) == 23
    if rows is None or rows.is_empty():
        pytest.skip("005930 panel expenseDetail empty")
    assert rows.columns == expected, rows.columns
    assert "reconciledTarget" in rows.columns


def test_bynature_lane_extracted(rows: pl.DataFrame | None) -> None:
    """성격별(strictExpensesByNature) lane 이 추출에 포함(by-nature 회복 입력)."""
    if rows is None or rows.is_empty():
        pytest.skip("005930 panel expenseDetail empty")
    lanes = set(rows["sourceLane"].to_list())
    assert "strictExpensesByNature" in lanes, lanes
