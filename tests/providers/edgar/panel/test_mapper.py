"""EDGAR panel mapper — role→statement·context→cell·period·item (순수, data 0).

DART ``panel.mapper`` 의 us-gaap 미러 검증. role 패턴 분류, instant/duration mode, calendar quarter.
"""

from __future__ import annotations

from datetime import date

import pytest

pytestmark = pytest.mark.unit


def test_role_to_statement() -> None:
    from dartlab.providers.edgar.panel.build.mapper import roleToStatement

    assert roleToStatement("http://x/role/StatementConsolidatedBalanceSheets") == "BS"
    assert roleToStatement("http://x/role/StatementConsolidatedStatementsOfIncome") == "IS"
    assert roleToStatement("http://x/role/StatementConsolidatedStatementsOfCashFlows") == "CF"
    assert roleToStatement("http://x/role/StatementConsolidatedStatementsOfComprehensiveIncome") == "CIS"
    assert roleToStatement("http://x/role/StatementConsolidatedStatementsOfChangesInEquity") == "EF"
    # parenthetical = 본표 아님, Disclosure = 주석 → None
    assert roleToStatement("http://x/role/StatementBalanceSheetsParenthetical") is None
    assert roleToStatement("http://x/role/DisclosureLeases") is None
    assert roleToStatement("") is None


def test_comprehensive_income_before_income() -> None:
    """ComprehensiveIncome 은 IS 가 아니라 CIS (검사 순서 가드)."""
    from dartlab.providers.edgar.panel.build.mapper import roleToStatement

    assert roleToStatement("http://x/role/StatementOfComprehensiveIncome") == "CIS"


def test_context_to_cell_instant_year_vs_interim() -> None:
    from dartlab.providers.edgar.panel.build.mapper import contextToCell

    # 연말(FYE 12월) instant → mode Y
    assert contextToCell({"instant": "2024-12-31", "start": None, "end": None, "members": []}, fyEndMonth=12) == (
        2024,
        "e",
        4,
        "Y",
        "",
    )
    # 중간 instant(8월, FYE 12월 아님) → mode A
    assert contextToCell({"instant": "2024-08-31", "start": None, "end": None, "members": []}, fyEndMonth=12) == (
        2024,
        "e",
        3,
        "A",
        "",
    )


def test_context_to_cell_duration_modes() -> None:
    from dartlab.providers.edgar.panel.build.mapper import contextToCell

    # FY duration(~365d) → Y
    assert contextToCell({"instant": None, "start": "2024-01-01", "end": "2024-12-31", "members": []}) == (
        2024,
        "d",
        4,
        "Y",
        "",
    )
    # 단독 분기(~90d) → Q
    assert contextToCell({"instant": None, "start": "2024-07-01", "end": "2024-09-30", "members": []}) == (
        2024,
        "d",
        3,
        "Q",
        "",
    )
    # YTD(~180d) → A
    out = contextToCell({"instant": None, "start": "2024-01-01", "end": "2024-06-30", "members": []})
    assert out[3] == "A"


def test_context_to_cell_axis_members() -> None:
    from dartlab.providers.edgar.panel.build.mapper import contextToCell

    ctx = {"instant": "2024-12-31", "start": None, "end": None, "members": [("srt:SegAxis", "air:NorthMember")]}
    out = contextToCell(ctx, fyEndMonth=12)
    assert out[4] == "NorthMember"  # member local-name only (DART axisPath 동형)


def test_period_from_report_no_hyphen() -> None:
    """periodFromReport 는 'YYYYQn' (하이픈 금지 — isPeriodColumn 규약)."""
    from dartlab.providers.edgar.panel.build.mapper import periodFromReport

    assert periodFromReport("10-K", date(2024, 12, 31)) == "2024Q4"
    assert periodFromReport("10-K", date(2025, 5, 31)) == "2025Q2"  # May-end → Q2 (calendar)
    assert periodFromReport("10-K", None) is None


def test_canonical_item() -> None:
    from dartlab.providers.edgar.panel.build.mapper import canonicalItem

    leaf, path = canonicalItem("10-K", "ITEM 1A. RISK FACTORS")
    assert leaf == "Item 1A. Risk Factors"
    assert path == "10-K␟Item 1A. Risk Factors"
    leaf2, _ = canonicalItem("10-K", "Item 1.")
    assert leaf2 == "Item 1. Business"  # 카탈로그 표준명
