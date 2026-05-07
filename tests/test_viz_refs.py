"""viz refs (evidence binding helpers) 단위 테스트."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


def test_table_ref_with_period_kind():
    from dartlab.viz.refs import tableRef

    assert tableRef("finance", "IS", "Y") == "finance:IS:Y"


def test_table_ref_without_period_kind():
    from dartlab.viz.refs import tableRef

    assert tableRef("scan", "PEER") == "scan:PEER"


def test_value_ref_format():
    from dartlab.viz.refs import valueRef

    assert valueRef("005930", "finance", "IS", "sales", "2024") == "finance:005930:IS:sales:2024"


def test_filing_deep_link_basic():
    from dartlab.viz.refs import filingDeepLink

    url = filingDeepLink("20250315000123")
    assert url == "https://dart.fss.or.kr/dsaf001/main.do?rcpNo=20250315000123"


def test_filing_deep_link_with_page():
    from dartlab.viz.refs import filingDeepLink

    url = filingDeepLink("20250315000123", page=42)
    assert url == "https://dart.fss.or.kr/dsaf001/main.do?rcpNo=20250315000123#page=42"


def test_filing_deep_link_none_for_empty_rcept():
    from dartlab.viz.refs import filingDeepLink

    assert filingDeepLink(None) is None
    assert filingDeepLink("") is None


def test_chart_evidence_binding_minimum():
    from dartlab.viz.refs import chartEvidenceBinding

    binding = chartEvidenceBinding(stockCode="005930", source="finance", topic="IS")
    assert binding == {
        "tableRef": "finance:IS",
        "source": "finance",
        "stockCode": "005930",
        "topic": "IS",
    }


def test_chart_evidence_binding_full():
    from dartlab.viz.refs import chartEvidenceBinding

    binding = chartEvidenceBinding(
        stockCode="005930",
        source="finance",
        topic="IS",
        periodKind="Y",
        periods=["2022", "2023", "2024"],
        extra={"reportName": "사업보고서"},
    )
    assert binding["tableRef"] == "finance:IS:Y"
    assert binding["periodKind"] == "Y"
    assert binding["periods"] == ["2022", "2023", "2024"]
    assert binding["reportName"] == "사업보고서"


def test_series_point_refs_without_rcept():
    from dartlab.viz.refs import seriesPointRefs

    refs = seriesPointRefs(
        stockCode="005930",
        source="finance",
        topic="IS",
        account="sales",
        periods=["2022", "2023"],
    )
    assert len(refs) == 2
    assert refs[0] == {"period": "2022", "valueRef": "finance:005930:IS:sales:2022"}
    # rcept_no 없을 때는 filingUrl 키도 없다
    assert "filingUrl" not in refs[0]


def test_series_point_refs_with_rcept_and_page():
    from dartlab.viz.refs import seriesPointRefs

    refs = seriesPointRefs(
        stockCode="005930",
        source="finance",
        topic="IS",
        account="sales",
        periods=["2022", "2023"],
        rceptMap={"2022": "20230315000111", "2023": "20240315000222"},
        pageMap={"2023": 42},
    )
    assert refs[0]["rcept_no"] == "20230315000111"
    assert refs[0]["filingUrl"] == "https://dart.fss.or.kr/dsaf001/main.do?rcpNo=20230315000111"
    assert "pdfPage" not in refs[0]
    assert refs[1]["pdfPage"] == 42
    assert refs[1]["filingUrl"].endswith("#page=42")


def test_series_point_refs_partial_rcept():
    from dartlab.viz.refs import seriesPointRefs

    refs = seriesPointRefs(
        stockCode="005930",
        source="finance",
        topic="IS",
        account="sales",
        periods=["2022", "2023"],
        rceptMap={"2023": "20240315000222"},  # 2022 는 누락
    )
    assert "rcept_no" not in refs[0]
    assert refs[1]["rcept_no"] == "20240315000222"
