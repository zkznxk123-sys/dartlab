"""EDGAR panel linkbase — EX-101.PRE(role→concept) + EX-101.LAB(라벨) (data 0)."""

from __future__ import annotations

import pytest

from .synthData import synthLab, synthPre

pytestmark = pytest.mark.unit


def test_parse_presentation_roles_and_order() -> None:
    from dartlab.providers.edgar.panel.build.linkbase import parsePresentation

    roles = parsePresentation(synthPre())
    bsRole = next(r for r in roles if "BalanceSheets" in r)
    concepts = [e["conceptKey"] for e in roles[bsRole]]
    assert "us-gaap:Assets" in concepts and "us-gaap:StockholdersEquity" in concepts
    assert len(roles[bsRole]) == 5  # 5 BS concept
    # order 정렬 — 첫 concept order 최소
    assert roles[bsRole][0]["order"] <= roles[bsRole][1]["order"]


def test_parse_labels_standard() -> None:
    from dartlab.providers.edgar.panel.build.linkbase import parseLabels

    labels = parseLabels(synthLab())
    assert labels.get("us-gaap:Assets") == "Total assets"
    assert labels.get("us-gaap:Revenues") == "Total revenues"
