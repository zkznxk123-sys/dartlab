"""Landing finance viewer account order mirror regressions."""

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPT_PATH = _REPO_ROOT / "landing" / "_scripts" / "buildFinanceAccountOrder.py"
_TARGET_PATH = _REPO_ROOT / "landing" / "src" / "lib" / "viewer" / "finance" / "accountOrder.ts"
_PREFIX_RE = re.compile(r"^(?:ifrs-full_|ifrs_|dart_|ifrs-smes_)")


@pytest.fixture(scope="module")
def orderModel():
    spec = importlib.util.spec_from_file_location("buildFinanceAccountOrder", _SCRIPT_PATH)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["buildFinanceAccountOrder"] = mod
    spec.loader.exec_module(mod)
    return mod.buildModel(), mod


def _snake(model: dict, accountId: str, label: str, stmt: str) -> str | None:
    order = model["orders"][stmt]
    stripped = _PREFIX_RE.sub("", accountId or "")
    idSnake = model["idMap"].get(stripped)
    if idSnake and idSnake in order:
        return idSnake
    for candidate in model["nameCandidates"].get(label, []):
        if candidate in order:
            return candidate
    return idSnake


def _displayOrder(model: dict, accountId: str, label: str, rawOrd: int, stmt: str) -> int:
    snake = _snake(model, accountId, label, stmt)
    if snake and snake in model["orders"][stmt]:
        return model["orders"][stmt][snake]
    return 1_000_000 + rawOrd


def _depth(model: dict, accountId: str, label: str, stmt: str) -> int:
    snake = _snake(model, accountId, label, stmt)
    if not snake:
        return 2
    return model["depths"][stmt].get(snake, 2)


def test_account_order_ts_is_synced(orderModel) -> None:
    """Committed TS mirror matches current account SSOT."""
    model, mod = orderModel
    assert _TARGET_PATH.read_text(encoding="utf-8") == mod.render(model)


def test_bs_total_assets_sorts_after_current_and_noncurrent_assets(orderModel) -> None:
    """삼성 2026Q1 raw ord처럼 자산총계가 앞에 와도 SSOT 순서로 복구."""
    model, _ = orderModel
    rows = [
        ("ifrs-full_Assets", "자산총계", 7),
        ("ifrs-full_CurrentAssets", "유동자산", 8),
        ("ifrs-full_CashAndCashEquivalents", "현금및현금성자산", 10),
        ("ifrs-full_NoncurrentAssets", "비유동자산", 17),
        ("ifrs-full_PropertyPlantAndEquipment", "유형자산", 25),
    ]

    labels = [label for _, label, _ in sorted(rows, key=lambda r: _displayOrder(model, *r, stmt="BS"))]

    assert labels == ["유동자산", "현금및현금성자산", "비유동자산", "유형자산", "자산총계"]


def test_bs_depth_uses_total_sub_leaf_levels(orderModel) -> None:
    """총계/소계/리프 depth 가 hardcoded XBRL set 이 아닌 SSOT mirror 에서 나온다."""
    model, _ = orderModel

    assert _depth(model, "ifrs-full_Assets", "자산총계", "BS") == 0
    assert _depth(model, "ifrs-full_CurrentAssets", "유동자산", "BS") == 1
    assert _depth(model, "ifrs-full_CashAndCashEquivalents", "현금및현금성자산", "BS") == 2


def test_recent_ifrs_id_gaps_resolve_to_statement_order(orderModel) -> None:
    """최근 DART finance raw 에서 드러난 ID gap 이 raw ord fallback 으로 밀리지 않는다."""
    model, _ = orderModel
    order = model["orders"]["BS"]

    currentFvpl = _snake(
        model, "ifrs-full_CurrentFinancialAssetsAtFairValueThroughProfitOrLoss", "단기당기손익-공정가치금융자산", "BS"
    )
    noncurrentFvpl = _snake(
        model, "ifrs-full_NoncurrentFinancialAssetsAtFairValueThroughProfitOrLoss", "당기손익-공정가치금융자산", "BS"
    )
    currentPortion = _snake(model, "ifrs-full_CurrentPortionOfLongtermBorrowings", "유동성장기부채", "BS")

    assert currentFvpl == "shortterm_financial_assets_at_fair_value_through_profit_or_loss"
    assert noncurrentFvpl == "longterm_financial_assets_at_fair_value_through_profit_or_loss"
    assert currentPortion == "current_portion_of_longterm_borrowings"
    assert order[currentFvpl] < order["noncurrent_assets"] < order[noncurrentFvpl] < order["total_assets"]
