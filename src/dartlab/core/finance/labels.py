"""항목 snakeId → 사람이 읽기 쉬운 라벨 변환.

DART accountMappings.json의 standardAccounts에서 korName을 추출하여
AI 컨텍스트와 도구 반환에서 한글/영문 라벨을 제공한다.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=1)
def _load_account_mappings() -> dict:
    """DART mapperData/accountMappings.json 전체 로드."""
    mapper_path = (
        Path(__file__).resolve().parents[2] / "providers" / "dart" / "finance" / "mapperData" / "accountMappings.json"
    )
    if not mapper_path.exists():
        return {}
    return json.loads(mapper_path.read_text(encoding="utf-8"))


def _load_standard_accounts() -> dict[str, dict]:
    """{snakeId: {korName, code, level, sj}}."""
    return _load_account_mappings().get("standardAccounts", {})


# standardAccounts에 없지만 AI 컨텍스트에서 자주 쓰는 snakeId 보충 매핑
_KR_SUPPLEMENTS: dict[str, str] = {
    "pretax_income": "법인세비용차감전순이익",
    "profit_before_tax": "법인세비용차감전순이익",
    "income_before_income_taxes_expenses": "법인세비용차감전순이익",
    "income_tax_expense": "법인세비용",
    "net_income": "당기순이익",
    "net_income_controlling": "지배기업귀속순이익",
    "net_income_cf": "당기순이익",
    "operating_cash_flow": "영업활동현금흐름",
    "investing_cash_flow": "투자활동현금흐름",
    "financing_cash_flow": "재무활동현금흐름",
    "basic_eps": "기본주당이익",
    "diluted_eps": "희석주당이익",
    "dividends_per_share": "주당배당금",
    "interest_expense": "이자비용",
    "free_cash_flow": "잉여현금흐름",
    "short_term_borrowings": "단기차입금",
    "debentures": "사채",
    "net_debt": "순차입금",
    "ebitda": "EBITDA",
    "total_equity": "자본총계",
    "owners_of_parent_equity": "지배기업소유주지분",
    "noncontrolling_interests_equity": "비지배지분",
    "common_stock": "보통주자본금",
    "additional_paid_in_capital": "주식발행초과금",
    "accumulated_other_comprehensive_income": "기타포괄손익누계액",
    "treasury_stock": "자기주식",
}


@lru_cache(maxsize=1)
def get_korean_labels() -> dict[str, str]:
    """snakeId → 한글 라벨 SSOT.

    우선순위:
    1. standardAccounts.korName (정본, 3,143개)
    2. mappings 역인덱스 — 한국어 → snakeId 의 가장 짧은 한국어명 (1:N 충돌 시 alt 탐색)
    3. _KR_SUPPLEMENTS 보충 (자주 쓰는 미등록 snakeId)
    """
    data = _load_account_mappings()
    stdAccounts: dict[str, dict] = data.get("standardAccounts", {})
    mappings: dict[str, str] = data.get("mappings", {})

    result: dict[str, str] = {}
    used: set[str] = set()

    # 1. standardAccounts 정본
    for snakeId, meta in stdAccounts.items():
        korName = meta.get("korName")
        if korName:
            result[snakeId] = korName
            used.add(korName)

    # 2. mappings 역인덱스 (한국어 → snakeId 를 snakeId → [한국어들]로 뒤집어 짧은 것)
    if mappings:
        reverse: dict[str, list[str]] = {}
        for name, snakeId in mappings.items():
            if any("\uac00" <= ch <= "\ud7a3" for ch in name):
                reverse.setdefault(snakeId, []).append(name)
        for snakeId, names in reverse.items():
            if snakeId in result:
                continue
            candidate = min(names, key=len)
            if candidate in used:
                # korName 충돌 — alt 탐색, 없으면 snakeId
                alt = sorted(names, key=len)
                chosen = next((n for n in alt if n not in used), snakeId)
                result[snakeId] = chosen
            else:
                result[snakeId] = candidate
            used.add(result[snakeId])

    # 3. 보충
    for sid, name in _KR_SUPPLEMENTS.items():
        if sid not in result:
            result[sid] = name

    return result


def _snake_to_title(snake_id: str) -> str:
    """snake_case → Title Case. 영문 fallback."""
    words = snake_id.replace("_", " ").strip()
    return words.title()


# ── EDGAR 영문 readable 라벨 (주요 계정 하드코딩 + fallback) ──

_EDGAR_LABELS: dict[str, str] = {
    "current_assets": "Current Assets",
    "cash_and_cash_equivalents": "Cash & Equivalents",
    "short_term_investments": "Short-term Investments",
    "trade_and_other_receivables": "Receivables",
    "inventories": "Inventories",
    "noncurrent_assets": "Non-current Assets",
    "tangible_assets": "PP&E",
    "intangible_assets": "Intangible Assets",
    "goodwill": "Goodwill",
    "total_assets": "Total Assets",
    "current_liabilities": "Current Liabilities",
    "trade_and_other_payables": "Payables",
    "short_term_borrowings": "Short-term Debt",
    "noncurrent_liabilities": "Non-current Liabilities",
    "longterm_borrowings": "Long-term Debt",
    "debentures": "Bonds Payable",
    "total_liabilities": "Total Liabilities",
    "total_stockholders_equity": "Total Equity",
    "retained_earnings": "Retained Earnings",
    "accumulated_other_comprehensive_income": "Accumulated OCI",
    "treasury_stock": "Treasury Stock",
    "paidin_capital": "Paid-in Capital",
    "capital_surplus": "Capital Surplus",
    "sales": "Revenue",
    "cost_of_sales": "Cost of Revenue",
    "gross_profit": "Gross Profit",
    "selling_and_administrative_expenses": "SG&A",
    "operating_profit": "Operating Income",
    "operating_income": "Operating Income",
    "pretax_income": "Pre-tax Income",
    "income_tax_expense": "Income Tax",
    "net_income": "Net Income",
    "net_income_controlling": "Net Income (Parent)",
    "net_income_cf": "Net Income",
    "basic_eps": "Basic EPS",
    "diluted_eps": "Diluted EPS",
    "dividends_per_share": "DPS",
    "operating_cash_flow": "Operating CF",
    "investing_cash_flow": "Investing CF",
    "financing_cash_flow": "Financing CF",
    "depreciation": "Depreciation",
    "capex": "CAPEX",
    "free_cash_flow": "Free Cash Flow",
    "interest_expense": "Interest Expense",
    "research_and_development": "R&D",
    "common_stock": "Common Stock",
    "additional_paid_in_capital": "Additional Paid-in Capital",
    "owners_of_parent_equity": "Parent Equity",
    "noncontrolling_interests_equity": "NCI",
    "total_equity": "Total Equity",
    "restricted_cash_current": "Restricted Cash",
    "deferred_revenue_current": "Deferred Revenue",
}


@lru_cache(maxsize=1)
def get_english_labels() -> dict[str, str]:
    """snakeId → 영문 readable 라벨. 하드코딩 + snake_to_title fallback."""
    return dict(_EDGAR_LABELS)


def get_account_labels(locale: str = "kr") -> dict[str, str]:
    """snakeId → 사람이 읽기 쉬운 라벨.

    Args:
        locale: "kr"이면 한글, "en"이면 영문.

    Returns:
        {snakeId: label} dict.
    """
    if locale == "kr":
        return get_korean_labels()
    return get_english_labels()


# 사용자가 자주 쓰는 줄임말/변형 → 정규 snakeId 매핑
# DART 회사마다 항목이 다르므로 (법인세비용차감전순이익 vs 법인세차감전순이익)
# 사용자 입력을 snakeId로 통일하여 정확한 매칭을 보장한다.
_KR_SYNONYMS: dict[str, str] = {
    "세전순이익": "profit_before_tax",
    "세전이익": "profit_before_tax",
    "법인세차감전순이익": "profit_before_tax",
    "법인세차감전이익": "profit_before_tax",
    "세전계속사업이익": "pretax_profit_from_continuing_operations",
    "법인세": "income_taxes",
    "순이익": "net_profit",
    "순손익": "net_profit",
    "총매출": "sales",
    "총매출액": "sales",
}


@lru_cache(maxsize=1)
def get_reverse_korean_labels() -> dict[str, str]:
    """한글 라벨 → snakeId 역조회. get_korean_labels()의 역방향.

    동일 한글 라벨이 여러 snakeId에 매핑될 경우 첫 번째를 유지한다.
    정규화된(소문자+공백제거) 키도 함께 등록하여 cascade 매칭에서 활용한다.
    _KR_SYNONYMS: 사용자 줄임말/변형도 등록.
    """
    import re
    import unicodedata

    forward = get_korean_labels()
    reverse: dict[str, str] = {}
    for sid, kr in forward.items():
        if kr not in reverse:
            reverse[kr] = sid
        # 정규화 키 (show.py normalizeItemKey와 동일 로직)
        nk = unicodedata.normalize("NFKC", kr)
        nk = re.sub(r"\s+", "", nk).lower()
        if nk not in reverse:
            reverse[nk] = sid
    # 사용자 줄임말 등록 (기존 키가 없을 때만)
    for synonym, sid in _KR_SYNONYMS.items():
        if synonym not in reverse:
            reverse[synonym] = sid
    return reverse


def resolve_label(snake_id: str, market: str = "KR") -> str:
    """단일 snakeId를 라벨로 변환. 매칭 실패 시 snake_to_title fallback."""
    labels = get_account_labels("kr" if market == "KR" else "en")
    label = labels.get(snake_id)
    if label:
        return label
    if market != "KR":
        return _snake_to_title(snake_id)
    return snake_id


# ── DART ↔ EDGAR snakeId alias (L0에 배치 — import 방향 준수) ──

SNAKEID_ALIASES: dict[str, str] = {
    # ── 현금흐름 (모두 short form 으로 통일 — 양방향 머지) ──
    # canonical = operating_cashflow / investing_cashflow / financing_cashflow.
    # mapper 가 만든 long form (`cash_flows_from_*_activities`) 은 alias 로 통합.
    "operating_cash_flow": "operating_cashflow",
    "investing_cash_flow": "investing_cashflow",
    "financing_cash_flow": "financing_cashflow",
    "cash_flows_from_operating": "operating_cashflow",
    "cash_flows_from_investing": "investing_cashflow",
    "cash_flows_from_financing": "financing_cashflow",
    "cash_flows_from_operating_activities": "operating_cashflow",
    "cash_flows_from_investing_activities": "investing_cashflow",
    "cash_flows_from_financing_activities": "financing_cashflow",
    "net_cash_flows_from_financing_activities": "financing_cashflow",
    "net_cash_flows_from_operating_activities": "operating_cashflow",
    "net_cash_flows_from_investing_activities": "investing_cashflow",
    # ── 손익 ──
    "revenue": "sales",
    "operating_income": "operating_profit",
    "operating_incomeloss": "operating_profit",
    "net_income": "net_profit",
    "net_incomenet_loss_for_the_year": "net_profit",
    "cost_of_revenue": "cost_of_sales",
    "income_before_tax": "profit_before_tax",
    "pretax_income": "profit_before_tax",
    "income_tax_expense": "income_taxes",
    "taxes_expenses": "income_taxes",
    "interest_expense": "finance_costs",
    "interest_expenses": "finance_costs",
    "finance_cost": "finance_costs",
    "financial_cost": "finance_costs",
    "interest_income": "finance_income",
    "financial_income": "finance_income",
    "selling_general_admin": "selling_and_administrative_expenses",
    "basic_eps": "basic_earnings_per_share",
    "diluted_eps": "diluted_earnings_per_share",
    "gross_profit_on_sales": "gross_profit",
    # ── 자산 ──
    "total_assets": "assets",
    "inventory": "inventories",
    "property_plant_equipment": "tangible_assets",
    "ppe": "tangible_assets",
    "accounts_receivable": "trade_and_other_receivables",
    "trade_receivables": "trade_and_other_receivables",
    "trade_and_other_current_receivables": "trade_and_other_receivables",
    "cash_and_equivalents": "cash_and_cash_equivalents",
    "noncurrent_assets": "noncurrent_assets",
    "non_current_assets": "noncurrent_assets",
    # ── 부채 ──
    "total_liabilities": "liabilities",
    "short_term_debt": "shortterm_borrowings",
    "long_term_debt": "longterm_borrowings",
    "short_term_borrowings": "shortterm_borrowings",
    "long_term_borrowings": "longterm_borrowings",
    "accounts_payable": "trade_and_other_payables",
    "trade_payables": "trade_and_other_payables",
    "bonds": "debentures",
    "shortterm_bonds": "debentures",
    "noncurrent_liabilities": "noncurrent_liabilities",
    "non_current_liabilities": "noncurrent_liabilities",
    # ── 자본 ──
    "total_equity": "owners_of_parent_equity",
    "total_stockholders_equity": "stockholders_equity",
    "equity_including_nci": "total_stockholders_equity",
    "equity_nci": "noncontrolling_interests_equity",
    "noncontrolling_interest": "noncontrolling_interests_equity",
    "other_equity_components": "other_equity",
    "issued_capital": "paidin_capital",
    # ── 투자 ──
    "capex": "purchase_of_property_plant_and_equipment",
}


def mergeAliasRows(
    rowMap: dict[str, dict],
    *,
    metaCols: set[str] | None = None,
) -> set[str]:
    """SNAKEID_ALIASES 양방향 row 머지 — 단일 진실의 원천 (SSOT).

    같은 개념이 두 snakeId 로 분리된 케이스 (예: ``cash_flows_from_financing_activities``
    ↔ ``financing_cashflow``) 를 한 row 로 in-place 합친다. col 별 not-null 우선.
    canonical row 만 살아남고 alias row 는 제거 대상으로 분류.

    DART pivot (``_financeToDataFrame``) 과 calc 헬퍼 (``toDictBySnakeId``)
    양쪽 모두 이 함수를 호출 — 머지 로직은 이 한 곳에만 존재.

    Args:
        rowMap: ``{snakeId: row_dict}``. row_dict 는 in-place 수정됨.
        metaCols: 머지 대상에서 제외할 메타 컬럼 (snakeId, 항목 등).
            None 이면 ``{"snakeId", "항목", "_level", "_sort"}`` default.
            calc 단계 dict 머지에서는 ``set()`` 전달.

    Returns:
        머지된 (= 제거 대상) alias snakeId set. 호출자가 필요 시 ``rowMap`` 에서 제거.
    """
    if metaCols is None:
        metaCols = {"snakeId", "항목", "_level", "_sort"}
    mergedSnakeIds: set[str] = set()
    for alias, canonical in SNAKEID_ALIASES.items():
        if alias == canonical:
            continue
        aRow = rowMap.get(alias)
        cRow = rowMap.get(canonical)
        if aRow is None or cRow is None:
            continue
        for col, val in aRow.items():
            if col in metaCols:
                continue
            if cRow.get(col) is None and val is not None:
                cRow[col] = val
        mergedSnakeIds.add(alias)
    return mergedSnakeIds
