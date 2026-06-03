"""EDGAR panel instance — inline facts + context 해소 + EX-101.INS native facts (data 0)."""

from __future__ import annotations

import pytest

from .synthData import synthPrimaryHtml

pytestmark = pytest.mark.unit


def test_extract_facts() -> None:
    from dartlab.providers.edgar.panel.build.instance import extractFacts

    facts = extractFacts(synthPrimaryHtml())
    byConcept = {f["concept"]: f for f in facts if f["namespace"] == "us-gaap"}
    assert "Assets" in byConcept and "Revenues" in byConcept
    assert byConcept["Assets"]["contextRef"] == "c_inst_2024"
    assert byConcept["Assets"]["valueRaw"] == "1000"  # scale=0 적용
    assert byConcept["Revenues"]["valueRaw"] == "5000"


def test_resolve_value_scale_sign_nil() -> None:
    from dartlab.providers.edgar.panel.build.instance import extractFacts

    html = (
        '<ix:nonFraction name="us-gaap:A" contextRef="c" scale="3" unitRef="u">1,234</ix:nonFraction>'
        '<ix:nonFraction name="us-gaap:B" contextRef="c" sign="-" unitRef="u">500</ix:nonFraction>'
        '<ix:nonFraction name="us-gaap:C" contextRef="c" xsi:nil="true" unitRef="u"></ix:nonFraction>'
    )
    f = {x["concept"]: x["valueRaw"] for x in extractFacts(html)}
    assert f["A"] == "1234000"  # scale 3 → ×1000, comma strip
    assert f["B"] == "-500"  # sign
    assert f["C"] == ""  # nil → 미공시


def test_extract_contexts_instant_duration_members() -> None:
    from dartlab.providers.edgar.panel.build.instance import extractContexts

    ctxs = extractContexts(synthPrimaryHtml())
    assert ctxs["c_inst_2024"]["instant"] == "2024-12-31"
    assert ctxs["c_dur_2024"]["start"] == "2024-01-01" and ctxs["c_dur_2024"]["end"] == "2024-12-31"


def test_extract_instance_facts_native() -> None:
    """EX-101.INS native fact (separate-instance era) — prefix-optional context + native 원소."""
    from dartlab.providers.edgar.panel.build.instance import extractContexts, extractInstanceFacts

    ins = (
        "<xbrl>"
        '<context id="c1"><period><instant>2018-12-31</instant></period></context>'
        '<us-gaap:Assets contextRef="c1" unitRef="usd" decimals="-3">123456</us-gaap:Assets>'
        '<us-gaap:Liabilities contextRef="c1" unitRef="usd">55000</us-gaap:Liabilities>'
        "</xbrl>"
    )
    facts = extractInstanceFacts(ins)
    fc = {f["concept"]: f["valueRaw"] for f in facts}
    assert fc.get("Assets") == "123456" and fc.get("Liabilities") == "55000"
    # prefix-optional context 파싱
    ctxs = extractContexts(ins)
    assert ctxs["c1"]["instant"] == "2018-12-31"
