"""EDGAR panel cell — facts × context × role → EDGAR_CELL_SCHEMA (data 0)."""

from __future__ import annotations

import pytest

from .synthData import synthLab, synthPre, synthPrimaryHtml

pytestmark = pytest.mark.unit


def test_build_cells_schema_and_anchoring() -> None:
    from dartlab.providers.edgar.panel.build.cell import buildCells
    from dartlab.providers.edgar.panel.build.cellSchema import EDGAR_CELL_SCHEMA
    from dartlab.providers.edgar.panel.build.instance import extractContexts, extractFacts
    from dartlab.providers.edgar.panel.build.linkbase import parseLabels, parsePresentation

    html = synthPrimaryHtml()
    facts = extractFacts(html)
    ctxs = extractContexts(html)
    roles = parsePresentation(synthPre())
    labels = parseLabels(synthLab())
    cells = buildCells(
        facts,
        ctxs,
        roles,
        labels,
        meta={"ticker": "TEST", "accession": "a1", "filingPeriod": "2024Q4", "fyEndMonth": 12},
    )
    assert cells, "셀 0"
    # 컬럼 == EDGAR_CELL_SCHEMA
    assert set(cells[0].keys()) == set(EDGAR_CELL_SCHEMA.keys())
    byStmt = {}
    for c in cells:
        byStmt.setdefault(c["statement"], []).append(c)
    assert "BS" in byStmt and "IS" in byStmt
    # BS Assets cell — instant 연말 → mode Y, value scale 적용
    assets = next(c for c in byStmt["BS"] if c["concept"] == "Assets")
    assert assets["valueRaw"] == "1000" and assets["ctxMode"] == "Y" and assets["scope"] == "consolidated"
    assert assets["label"] == "Total assets"  # EX-101.LAB
    # IS Revenues — duration FY → mode Y
    rev = next(c for c in byStmt["IS"] if c["concept"] == "Revenues")
    assert rev["valueRaw"] == "5000" and rev["ctxMode"] == "Y"


def test_disclosure_role_excluded() -> None:
    """Disclosure role concept 은 셀 0 (statement 만 분해)."""
    from dartlab.providers.edgar.panel.build.cell import buildCells

    roles = {
        "http://t/role/DisclosureLeases": [
            {
                "conceptKey": "us-gaap:LeaseCost",
                "concept": "LeaseCost",
                "ns": "us-gaap",
                "order": 0.0,
                "preferredLabel": None,
            }
        ]
    }
    facts = [
        {
            "concept": "LeaseCost",
            "namespace": "us-gaap",
            "contextRef": "c",
            "unitRef": "u",
            "valueRaw": "10",
            "factType": "numeric",
            "htmlPos": 0,
        }
    ]
    ctxs = {"c": {"instant": "2024-12-31", "start": None, "end": None, "members": []}}
    cells = buildCells(
        facts, ctxs, roles, {}, meta={"ticker": "T", "accession": "a", "filingPeriod": "2024Q4", "fyEndMonth": 12}
    )
    assert cells == []  # 비-statement role → 셀 0
