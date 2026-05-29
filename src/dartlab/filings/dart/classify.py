"""key → (finance | report | sections) 분류 + alias resolve — show 디스패치 SSOT.

facade `show(key)` 의 분기를 결정. 옛 source-컬럼 synthetic 행·mapper 없이, 키
자체로 판정:
    - finance: 재무제표 5종 alias/disclosureKey → ("finance", {sjDiv, scope}).
    - report: OpenAPI apiType 26종 → ("report", {apiType}).
    - sections: 그 외 → ("sections", {key}) — sections artifact 에서 canonical 키 매칭.

LLM Specifications:
    AntiPatterns:
        - mapper 591줄 regex 부활 금지 — finite alias map + apiType set 만.
        - 미지 key 에 추측 매핑 금지 — sections 로 보내 artifact 매칭에 위임.
    OutputSchema:
        - ``classify(key) -> tuple[str, dict]``.
    Prerequisites:
        - 없음.
    TargetMarkets:
        - KR (DART). EDGAR 는 자체 classify.
"""

from __future__ import annotations

# 재무제표 alias/disclosureKey → (sjDiv, scope). consolidated default.
_FINANCE: dict[str, tuple[str, str]] = {
    "BS": ("BS", "consolidated"),
    "재무상태표": ("BS", "consolidated"),
    "balanceSheet": ("BS", "consolidated"),
    "consolidatedBalanceSheet": ("BS", "consolidated"),
    "standaloneBalanceSheet": ("BS", "separate"),
    "IS": ("IS", "consolidated"),
    "손익계산서": ("IS", "consolidated"),
    "incomeStatement": ("IS", "consolidated"),
    "consolidatedIncomeStatement": ("IS", "consolidated"),
    "standaloneIncomeStatement": ("IS", "separate"),
    "CIS": ("CIS", "consolidated"),
    "포괄손익계산서": ("CIS", "consolidated"),
    "CF": ("CF", "consolidated"),
    "현금흐름표": ("CF", "consolidated"),
    "cashFlow": ("CF", "consolidated"),
    "consolidatedCashFlowStatement": ("CF", "consolidated"),
    "standaloneCashFlowStatement": ("CF", "separate"),
    "SCE": ("SCE", "consolidated"),
    "자본변동표": ("SCE", "consolidated"),
    "consolidatedEquityChanges": ("SCE", "consolidated"),
    "standaloneEquityChanges": ("SCE", "separate"),
}

# DART OpenAPI 정기보고서 apiType 26종 (report parquet 의 apiType 컬럼 SSOT).
_REPORT: frozenset[str] = frozenset(
    {
        "dividend",
        "executive",
        "employee",
        "treasuryStock",
        "stockTotal",
        "majorHolder",
        "majorHolderChange",
        "minorityHolder",
        "investedCompany",
        "debtSecurities",
        "corporateBond",
        "shortTermBond",
        "commercialPaper",
        "capitalChange",
        "auditOpinion",
        "auditContract",
        "nonAuditContract",
        "outsideDirector",
        "executivePayType",
        "executivePayApproval",
        "executivePayIndividual",
        "executivePayAllTotal",
        "unregisteredExecutivePay",
        "topPay",
        "privateOfferingUsage",
        "publicOfferingUsage",
    }
)


def classify(key: str) -> tuple[str, dict]:
    """key → ("finance"|"report"|"sections", params).

    Args:
        key: show 인자 (재무제표 alias / report apiType / disclosureKey / sectionLeaf).

    Returns:
        ("finance", {"sjDiv", "scope"}) / ("report", {"apiType"}) / ("sections", {"key"}).

    Examples:
        >>> classify("BS")
        ('finance', {'sjDiv': 'BS', 'scope': 'consolidated'})
        >>> classify("dividend")
        ('report', {'apiType': 'dividend'})
        >>> classify("inventoryDisclosure")
        ('sections', {'key': 'inventoryDisclosure'})
    """
    if key in _FINANCE:
        sjDiv, scope = _FINANCE[key]
        return ("finance", {"sjDiv": sjDiv, "scope": scope})
    if key in _REPORT:
        return ("report", {"apiType": key})
    return ("sections", {"key": key})


def isFinanceKey(key: str) -> bool:
    """재무제표 키 여부 (facade 빠른 판정용)."""
    return key in _FINANCE


def isReportKey(key: str) -> bool:
    """report apiType 키 여부."""
    return key in _REPORT
