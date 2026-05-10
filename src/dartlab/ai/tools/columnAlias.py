"""한국어 ↔ snake_case 컬럼 alias 전면 SSOT.

워크벤치 (engineCall) + run_python prelude 가 공유. 운영자/사용자가 자연어로 부른
컬럼명 ("자산총계", "총자산", "asset_total") 을 dartlab Polars DataFrame 의 표준
snake_id 로 정규화한다. show("BS")/show("IS")/show("CF")/show("CIS")/show("SCE") 의
컬럼 추측 실패를 줄이는 것이 목적.

표준 5 topic — BS / IS / CF / CIS / SCE. 각 topic 별 (snake_id, korean_label,
*aliases) tuple list. aliases 는 한국어 약어, 영문 동의어, 공백 제거형 등.

사용:
    from dartlab.ai.tools.columnAlias import normalizeColumn, columnsFor

    snake = normalizeColumn("BS", "자산총계")        # → "total_assets"
    snake = normalizeColumn("BS", "총자산")          # → "total_assets" (alias)
    cols = columnsFor("BS")                          # → 표준 snake_id list
"""

from __future__ import annotations

# (snake_id, korean_label, *aliases) — alias 는 검색에서 동등.
ColumnEntry = tuple[str, str, tuple[str, ...]]

_BS_COLUMNS: tuple[ColumnEntry, ...] = (
    ("cash_and_cash_equivalents", "현금및현금성자산", ("현금", "현금성자산", "cash")),
    ("shortterm_financial_instruments", "단기금융상품", ("단기금융", "예금", "deposits")),
    ("accounts_receivable", "매출채권", ("매출채권및기타채권", "receivables")),
    ("inventories", "재고자산", ("재고", "inventory")),
    ("current_assets", "유동자산", ("유동", "current")),
    ("non_current_assets", "비유동자산", ("비유동", "고정자산", "noncurrent assets")),
    ("total_assets", "자산총계", ("총자산", "자산", "asset", "assets", "total asset")),
    ("current_liabilities", "유동부채", ("단기부채", "current liabilities")),
    ("non_current_liabilities", "비유동부채", ("장기부채", "noncurrent liabilities")),
    ("total_liabilities", "부채총계", ("총부채", "부채", "liabilities", "total debt")),
    ("owners_of_parent_equity", "지배주주지분", ("지배지분", "controlling interest")),
    ("non_controlling_interests", "비지배주주지분", ("비지배지분", "minority interest")),
    ("total_stockholders_equity", "자본총계", ("총자본", "자본", "equity", "shareholders equity")),
    ("total_equity", "자본총계", ("총자본", "자본", "equity")),
    ("retained_earnings", "이익잉여금", ("적립금", "retained")),
    ("capital_stock", "자본금", ("발행자본", "capital")),
)

_IS_COLUMNS: tuple[ColumnEntry, ...] = (
    ("sales", "매출액", ("매출", "수익", "revenue", "sales")),
    ("revenue", "매출액", ("매출", "수익")),
    ("cost_of_sales", "매출원가", ("원가", "cogs")),
    ("gross_profit", "매출총이익", ("총이익", "gross")),
    ("sga_expenses", "판매비와관리비", ("판관비", "sga", "selling general administrative")),
    ("operating_profit", "영업이익", ("영업", "OP", "operating income")),
    ("operating_income", "영업이익", ("영업", "OP")),
    ("non_operating_income", "영업외수익", ("기타수익", "non operating income")),
    ("non_operating_expenses", "영업외비용", ("기타비용", "non operating expense")),
    ("profit_before_tax", "법인세차감전순이익", ("세전이익", "pretax income", "EBT")),
    ("income_tax_expense", "법인세비용", ("법인세", "tax expense")),
    ("net_profit", "당기순이익", ("순이익", "NI", "net income")),
    ("net_income", "당기순이익", ("순이익", "NI")),
    ("net_income_attributable_to_parent", "지배주주순이익", ("지배순이익", "controlling NI")),
)

_CF_COLUMNS: tuple[ColumnEntry, ...] = (
    ("cash_flows_from_operating_activities", "영업활동현금흐름", ("영업현금흐름", "OCF", "operating cash")),
    ("operating_cashflow", "영업활동현금흐름", ("영업현금", "OCF")),
    ("cash_flows_from_investing_activities", "투자활동현금흐름", ("투자현금흐름", "investing cash")),
    ("investing_cashflow", "투자활동현금흐름", ("투자현금", "ICF")),
    ("cash_flows_from_financing_activities", "재무활동현금흐름", ("재무현금흐름", "financing cash")),
    ("financing_cashflow", "재무활동현금흐름", ("재무현금", "FCF")),
    ("purchase_of_property_plant_and_equipment", "유형자산의취득", ("CAPEX", "capital expenditure")),
    ("capital_expenditures", "유형자산의취득", ("CAPEX",)),
    ("sale_of_property_plant_and_equipment", "유형자산의처분", ("자산처분", "ppe sale")),
    ("dividends_paid", "배당금지급", ("배당지급", "dividend paid")),
    ("treasury_stock_acquisition", "자기주식취득", ("자사주매입", "buyback")),
    ("free_cash_flow", "잉여현금흐름", ("FCF", "free cash flow")),
)

_CIS_COLUMNS: tuple[ColumnEntry, ...] = (
    ("net_profit", "당기순이익", ("순이익",)),
    ("other_comprehensive_income", "기타포괄손익", ("OCI",)),
    ("total_comprehensive_income", "총포괄손익", ("총포괄",)),
)

_SCE_COLUMNS: tuple[ColumnEntry, ...] = (
    ("capital_stock", "자본금", ("발행자본",)),
    ("capital_surplus", "자본잉여금", ("주식발행초과금",)),
    ("retained_earnings", "이익잉여금", ("적립금",)),
    ("treasury_shares", "자기주식", ("자사주",)),
    ("total_equity", "자본총계", ("총자본",)),
)

_TOPIC_COLUMNS: dict[str, tuple[ColumnEntry, ...]] = {
    "BS": _BS_COLUMNS,
    "IS": _IS_COLUMNS,
    "CF": _CF_COLUMNS,
    "CIS": _CIS_COLUMNS,
    "SCE": _SCE_COLUMNS,
}


def _normalizeText(value: str) -> str:
    return "".join(ch.lower() for ch in str(value or "") if not ch.isspace())


def normalizeColumn(topic: str, hint: str) -> str | None:
    """topic 안에서 hint 와 매칭되는 표준 snake_id 반환. 매칭 없으면 None.

    매칭 규칙 (우선순위):
    1. snake_id 정확 일치
    2. 한국어 label 정확 일치
    3. alias 정확 일치
    4. 정규화 (공백 제거, 소문자) 후 일치
    """
    columns = _TOPIC_COLUMNS.get(str(topic or "").upper())
    if not columns:
        return None
    raw = str(hint or "").strip()
    if not raw:
        return None
    norm = _normalizeText(raw)
    for snakeId, label, aliases in columns:
        if raw == snakeId or raw == label or raw in aliases:
            return snakeId
        if _normalizeText(snakeId) == norm or _normalizeText(label) == norm:
            return snakeId
        if any(_normalizeText(a) == norm for a in aliases):
            return snakeId
    return None


def columnsFor(topic: str) -> list[dict[str, str | tuple[str, ...]]]:
    """topic 의 표준 컬럼 목록 — (snake_id, label, aliases) 메타.

    LLM 이 run_python 코드 짜기 전 사용 가능한 컬럼을 빠르게 확인하기 위함.
    """
    columns = _TOPIC_COLUMNS.get(str(topic or "").upper())
    if not columns:
        return []
    return [{"snake_id": s, "label": l, "aliases": list(a)} for s, l, a in columns]


def topicAccountPriority(topic: str) -> tuple[tuple[str, str], ...]:
    """engineCall._ACCOUNT_PRIORITY 호환 형태 — (snake_id, korean_label) tuple list."""
    columns = _TOPIC_COLUMNS.get(str(topic or "").upper())
    if not columns:
        return ()
    return tuple((s, l) for s, l, _ in columns)


def availableTopics() -> list[str]:
    return list(_TOPIC_COLUMNS.keys())
