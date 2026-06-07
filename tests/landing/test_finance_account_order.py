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
    orderedCandidates = [
        (order[candidate], candidate) for candidate in model["nameCandidates"].get(label, []) if candidate in order
    ]
    if orderedCandidates:
        return min(orderedCandidates)[1]
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


def _isTotal(model: dict, accountId: str, label: str, stmt: str) -> bool:
    snake = _snake(model, accountId, label, stmt)
    if not snake:
        return False
    return bool(model["isTotal"][stmt].get(snake, False))


def test_account_order_ts_is_synced(orderModel) -> None:
    """Committed TS mirror matches current account SSOT."""
    model, mod = orderModel
    assert _TARGET_PATH.read_text(encoding="utf-8") == mod.render(model)


def test_bs_total_assets_sorts_before_current_and_noncurrent_assets(orderModel) -> None:
    """삼성 2026Q1 raw ord가 흔들려도 BS 총계 → 소계 → 리프 순서를 유지."""
    model, _ = orderModel
    rows = [
        ("ifrs-full_Assets", "자산총계", 7),
        ("ifrs-full_CurrentAssets", "유동자산", 8),
        ("ifrs-full_CashAndCashEquivalents", "현금및현금성자산", 10),
        ("ifrs-full_NoncurrentAssets", "비유동자산", 17),
        ("ifrs-full_PropertyPlantAndEquipment", "유형자산", 25),
    ]

    labels = [label for _, label, _ in sorted(rows, key=lambda r: _displayOrder(model, *r, stmt="BS"))]

    assert labels == ["자산총계", "유동자산", "현금및현금성자산", "비유동자산", "유형자산"]


def test_bs_depth_uses_total_sub_leaf_levels(orderModel) -> None:
    """총계/소계/리프 depth 가 hardcoded XBRL set 이 아닌 SSOT mirror 에서 나온다."""
    model, _ = orderModel

    assert _depth(model, "ifrs-full_Assets", "자산총계", "BS") == 0
    assert _depth(model, "ifrs-full_CurrentAssets", "유동자산", "BS") == 1
    assert _depth(model, "ifrs-full_CashAndCashEquivalents", "현금및현금성자산", "BS") == 2
    assert _depth(model, "ifrs-full_Liabilities", "부채총계", "BS") == 0
    assert _depth(model, "ifrs-full_CurrentLiabilities", "유동부채", "BS") == 1
    assert _depth(model, "ifrs-full_Equity", "자본총계", "BS") == 0


def test_is_bottom_line_depth_decoupled_from_total_emphasis(orderModel) -> None:
    """손익 본류(매출액~당기순이익)는 균일 depth 1 로 정렬되고, 당기순이익의 총계 강조는
    depth 가 아니라 isTotal mirror 로 따로 표현된다(들여쓰기/강조 분리)."""
    model, _ = orderModel

    # 들여쓰기: 당기순이익이 영업이익(본류)과 같은 depth 1 — 더 이상 좌측으로 튀지 않는다.
    assert _depth(model, "ifrs-full_ProfitLoss", "당기순이익", "IS") == 1
    assert _depth(model, "ifrs-full_NetProfit", "당기순이익", "IS") == 1
    assert _depth(model, "-표준계정코드 미사용-", "당기순이익", "IS") == 1
    assert _depth(model, "dart_OperatingIncomeLoss", "영업이익", "IS") == 1

    # 강조: 당기순이익은 depth 1 이어도 총계(isTotal=True), 본류 소계(영업이익)는 False.
    assert _isTotal(model, "ifrs-full_ProfitLoss", "당기순이익", "IS") is True
    assert _isTotal(model, "ifrs-full_NetProfit", "당기순이익", "IS") is True
    assert _isTotal(model, "dart_OperatingIncomeLoss", "영업이익", "IS") is False
    # BS 총계는 depth 0(루트) 유지 + isTotal True.
    assert _depth(model, "ifrs-full_Assets", "자산총계", "BS") == 0
    assert _isTotal(model, "ifrs-full_Assets", "자산총계", "BS") is True


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
    assert (
        order["total_assets"]
        < order["current_assets"]
        < order[currentFvpl]
        < order["noncurrent_assets"]
        < order[noncurrentFvpl]
    )


def test_korean_mapping_labels_resolve_when_account_id_is_missing(orderModel) -> None:
    """account_id 가 비표준이어도 standard account 라벨 SSOT 로 순서와 depth 를 복구한다."""
    model, _ = orderModel

    assert _snake(model, "-표준계정코드 미사용-", "자산총계", "BS") == "assets"
    assert _snake(model, "-표준계정코드 미사용-", "유동자산", "BS") == "current_assets"
    assert _snake(model, "-표준계정코드 미사용-", "재고자산", "BS") == "inventories"
    assert _displayOrder(model, "-표준계정코드 미사용-", "자산총계", 999, "BS") < _displayOrder(
        model, "-표준계정코드 미사용-", "유동자산", 999, "BS"
    )
    assert _depth(model, "-표준계정코드 미사용-", "자산총계", "BS") == 0
    assert _depth(model, "-표준계정코드 미사용-", "유동자산", "BS") == 1
