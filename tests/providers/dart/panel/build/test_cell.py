"""panel build/cell mirror — ACONTEXT 분해 + 5표 셀 추출 (인라인 합성 XML, 데이터 0).

``build/cell.py`` 의 ``decodeAcontext``/``_markerToQuarterMode``/``iterCellRows``. 실 zip(5표 본문)은
git 미추적(요약첨부는 ctx 0)이라 인라인 합성 XML 로 검증. 실 zip 라운드트립은 tests/panel
(requires_data) 담당.
"""

from __future__ import annotations

import pytest
from lxml import etree

pytestmark = pytest.mark.unit


def test_decode_acontext_deterministic() -> None:
    """ACONTEXT period 토큰 → (year, flow, quarter, mode) 결정론 분해 (전 분기 marker)."""
    from dartlab.providers.dart.panel.build.cell import decodeAcontext

    base = "_ifrs-full_X_ifrs-full_ConsolidatedMember"
    assert decodeAcontext("CFY2025dFY" + base) == (2025, "d", 4, "Y", "ConsolidatedMember")
    assert decodeAcontext("BPFY2023eFY" + base) == (2023, "e", 4, "Y", "ConsolidatedMember")
    assert decodeAcontext("CFY2025dTQA" + base) == (2025, "d", 3, "A", "ConsolidatedMember")
    assert decodeAcontext("CFY2025dTQQ" + base) == (2025, "d", 3, "Q", "ConsolidatedMember")
    assert decodeAcontext("CFY2025dFQA" + base) == (2025, "d", 1, "A", "ConsolidatedMember")
    assert decodeAcontext("CFY2025dFQQ" + base) == (2025, "d", 1, "Q", "ConsolidatedMember")
    assert decodeAcontext("CFY2025dHYA" + base) == (2025, "d", 2, "A", "ConsolidatedMember")
    assert decodeAcontext("PFY2024eFQ" + base) == (2024, "e", 1, "P", "ConsolidatedMember")
    assert decodeAcontext("garbage") is None
    assert decodeAcontext("") is None


def test_marker_to_quarter_mode() -> None:
    """marker → (분기, 모드). FQ=1·HY=2·TQ=3·FY=연간(4), 접미 A/Q, bare=P."""
    from dartlab.providers.dart.panel.build.cell import _markerToQuarterMode

    assert _markerToQuarterMode("FY") == (4, "Y")
    assert _markerToQuarterMode("FQA") == (1, "A")
    assert _markerToQuarterMode("FQQ") == (1, "Q")
    assert _markerToQuarterMode("FQ") == (1, "P")
    assert _markerToQuarterMode("HYA") == (2, "A")
    assert _markerToQuarterMode("TQQ") == (3, "Q")
    assert _markerToQuarterMode("TQ") == (3, "P")


def test_axis_members_strip_standard_prefix() -> None:
    """축 멤버에서 ifrs-full_/dart_ prefix 벗기고 entity 는 보존."""
    from dartlab.providers.dart.panel.build.cell import _axisMembers

    segs = "ifrs-full_ConsolidatedAndSeparateFinancialStatementsAxis_ifrs-full_ConsolidatedMember".split("_")
    assert _axisMembers(segs) == ["ConsolidatedMember"]
    segs2 = "ifrs-full_Ax_entity00126380_FooClassMemberOfBarTableOfMember".split("_")
    assert _axisMembers(segs2) == ["entity00126380_FooClassMemberOfBarTableOfMember"]


_XML = """<BODY>
  <TABLE-GROUP ACLASS="{XBRL}IS_C2">
    <TITLE>연결 손익계산서</TITLE>
    <TABLE>
      <TR>
        <TE>매출액 (주30)</TE>
        <TE ACODE="ifrs-full_Revenue" ACONTEXT="CFY2025dFY_ifrs-full_Ax_ifrs-full_ConsolidatedMember">100</TE>
        <TE ACODE="ifrs-full_Revenue" ACONTEXT="PFY2024dFY_ifrs-full_Ax_ifrs-full_ConsolidatedMember">90</TE>
      </TR>
    </TABLE>
  </TABLE-GROUP>
  <TABLE-GROUP ACLASS="{XBRL}EF_C">
    <TITLE>연결 자본변동표</TITLE>
    <TABLE>
      <TR>
        <TE>이익잉여금</TE>
        <TE ACODE="ifrs-full_RetainedEarnings" ACONTEXT="CFY2025eFY_ifrs-full_Ax_ifrs-full_ConsolidatedMember_ifrs-full_ComponentsOfEquityAxis_ifrs-full_RetainedEarningsMember">7</TE>
      </TR>
    </TABLE>
  </TABLE-GROUP>
  <TABLE-GROUP ACLASS="{XBRL}NT_C_D826380">
    <TITLE>재고자산</TITLE>
    <TABLE>
      <TR>
        <TE>재고</TE>
        <TE ACODE="ifrs-full_Inventories" ACONTEXT="CFY2025eFY_ifrs-full_Ax_ifrs-full_ConsolidatedMember">50</TE>
      </TR>
    </TABLE>
  </TABLE-GROUP>
</BODY>"""


def _rows() -> list[dict]:
    from dartlab.providers.dart.panel.build.cell import iterCellRows

    root = etree.fromstring(_XML.encode("utf-8"), etree.XMLParser(recover=True))
    return list(iterCellRows(root, period="2025Q4", code="005930", rcept="20260310002820"))


def test_iter_cell_rows_five_statements_only() -> None:
    """iterCellRows 는 5표(IS_C2/EF_C)만 — 주석(NT_*)은 제외."""
    rows = _rows()
    statements = {r["statement"] for r in rows}
    assert statements == {"IS2", "EF"}  # NT_D826380(Inventories) 제외
    assert all(r["acode"] != "ifrs-full_Inventories" for r in rows)


def test_label_colocation() -> None:
    """value 셀에 같은 TR 한글 라벨 동거 (빈 문자열 아님)."""
    rows = _rows()
    rev = [r for r in rows if r["acode"] == "ifrs-full_Revenue"]
    assert len(rev) == 2  # CFY + PFY
    assert all(r["label"] == "매출액 (주30)" for r in rev)
    assert rev[0]["valueRaw"] == "100"


def test_iter_cell_rows_axis_depth_preserved() -> None:
    """깊은 축(자본구성)은 axisPath 에 멤버경로로 보존."""
    rows = _rows()
    re_row = next(r for r in rows if r["acode"] == "ifrs-full_RetainedEarnings")
    assert "RetainedEarningsMember" in re_row["axisPath"]
    assert re_row["statement"] == "EF"
    assert re_row["ctxQuarter"] == 4 and re_row["ctxMode"] == "Y" and re_row["ctxFlow"] == "e"
