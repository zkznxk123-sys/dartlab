"""EDGAR panel 테스트용 합성 SEC full-submission `.txt` (data 0, 실 SEC 구조 미니 재현).

5 BS concept(앵커 임계 ≥5 충족) + 1 IS concept + inline ix fact + xbrli:context(instant/duration) +
EX-101.PRE(role→concept) + EX-101.LAB(라벨). submission/instance/linkbase/walker/cell/builder 테스트 공용.
pytest 가 test_ prefix 아니라 본 모듈을 테스트로 수집하지 않음.
"""

from __future__ import annotations

_BS_CONCEPTS = ["Assets", "Liabilities", "CashAndCashEquivalentsAtCarryingValue", "InventoryNet", "StockholdersEquity"]
_IS_CONCEPTS = ["Revenues", "CostOfRevenue", "GrossProfit", "OperatingIncomeLoss", "NetIncomeLoss"]


def _ixFact(concept: str, ctx: str, value: str) -> str:
    return (
        f'<ix:nonFraction name="us-gaap:{concept}" contextRef="{ctx}" unitRef="usd" scale="0">{value}</ix:nonFraction>'
    )


def synthPrimaryHtml() -> str:
    """합성 iXBRL primary HTML — Item 1 텍스트 + BS 표(5 fact) + IS 표(1 fact) + Item 7 텍스트 + context."""
    instCtx = (
        '<xbrli:context id="c_inst_2024"><xbrli:entity><xbrli:identifier>0000012345</xbrli:identifier>'
        "</xbrli:entity><xbrli:period><xbrli:instant>2024-12-31</xbrli:instant></xbrli:period></xbrli:context>"
    )
    durCtx = (
        '<xbrli:context id="c_dur_2024"><xbrli:entity><xbrli:identifier>0000012345</xbrli:identifier>'
        "</xbrli:entity><xbrli:period><xbrli:startDate>2024-01-01</xbrli:startDate>"
        "<xbrli:endDate>2024-12-31</xbrli:endDate></xbrli:period></xbrli:context>"
    )
    bsCells = "".join(_ixFact(c, "c_inst_2024", str(1000 + i)) for i, c in enumerate(_BS_CONCEPTS))
    isCells = "".join(_ixFact(c, "c_dur_2024", str(5000 + i)) for i, c in enumerate(_IS_CONCEPTS))
    return (
        "<?xml version='1.0' encoding='ASCII'?>\n<html xmlns:us-gaap=\"x\"><body>"
        f"<div>{instCtx}{durCtx}</div>"
        "<p>Item 1. Business</p><div>We make widgets and provide services to customers worldwide.</div>"
        f"<table><tr><td>Balance Sheet</td><td>{bsCells}</td></tr></table>"
        "<p>Item 7. Management's Discussion and Analysis</p><div>Revenue grew this year.</div>"
        f"<table><tr><td>Income</td><td>{isCells}</td></tr></table>"
        "</body></html>"
    )


def synthPrimaryHtmlNoInline() -> str:
    """INS-era 합성 HTML — inline ix fact 0 (facts 가 별도 EX-101.INS). 재무제표 표는 **캡션 제목**으로만
    식별 → walker 의 captionToStatement fallback 앵커 검증용. 본표 캡션 + note 표(오앵커 가드)도 포함."""
    return (
        "<?xml version='1.0' encoding='ASCII'?>\n<html><body>"
        "<p>Item 1. Business</p><div>We make widgets and provide services worldwide.</div>"
        "<p>TEST CORP. AND SUBSIDIARIES CONSOLIDATED BALANCE SHEETS</p>"
        "<table><tr><td>Total assets</td><td>1000</td></tr><tr><td>Total liabilities</td><td>500</td></tr>"
        "<tr><td>Stockholders equity</td><td>500</td></tr></table>"
        "<p>TEST CORP. AND SUBSIDIARIES CONSOLIDATED STATEMENTS OF INCOME</p>"
        "<table><tr><td>Total revenues</td><td>5000</td></tr><tr><td>Net income</td><td>800</td></tr></table>"
        "<p>A summary of our off-balance sheet arrangements is as follows:</p>"
        "<table><tr><td>Operating leases</td><td>120</td></tr></table>"
        "</body></html>"
    )


def synthPre() -> str:
    """합성 EX-101.PRE — BS role(5 concept 순서) + IS role(1 concept)."""
    bsArcs = "".join(
        f'<link:loc xlink:href="t.xsd#us-gaap_{c}" xlink:label="loc_{c}"/>'
        f'<link:presentationArc xlink:from="bsRoot" xlink:to="loc_{c}" order="{i + 1}"/>'
        for i, c in enumerate(_BS_CONCEPTS)
    )
    isArcs = "".join(
        f'<link:loc xlink:href="t.xsd#us-gaap_{c}" xlink:label="loc_{c}"/>'
        f'<link:presentationArc xlink:from="isRoot" xlink:to="loc_{c}" order="{i + 1}"/>'
        for i, c in enumerate(_IS_CONCEPTS)
    )
    return (
        "<link:linkbase>"
        '<link:presentationLink xlink:role="http://t.com/role/StatementConsolidatedBalanceSheets">'
        f"{bsArcs}</link:presentationLink>"
        '<link:presentationLink xlink:role="http://t.com/role/StatementConsolidatedStatementsOfIncome">'
        f"{isArcs}</link:presentationLink></link:linkbase>"
    )


def synthLab() -> str:
    """합성 EX-101.LAB — Assets/Revenues 표준 라벨."""
    return (
        "<link:linkbase>"
        '<link:loc xlink:href="t.xsd#us-gaap_Assets" xlink:label="loc_Assets"/>'
        '<link:labelArc xlink:from="loc_Assets" xlink:to="lab_Assets"/>'
        '<link:label xlink:label="lab_Assets" xlink:role="http://www.xbrl.org/2003/role/label">Total assets</link:label>'
        '<link:loc xlink:href="t.xsd#us-gaap_Revenues" xlink:label="loc_Rev"/>'
        '<link:labelArc xlink:from="loc_Rev" xlink:to="lab_Rev"/>'
        '<link:label xlink:label="lab_Rev" xlink:role="http://www.xbrl.org/2003/role/label">Total revenues</link:label>'
        "</link:linkbase>"
    )


def synthSubmissionTxt(
    *, form: str = "10-K", cik: str = "0000012345", accession: str = "0000012345-25-000001", periodEnd: str = "20241231"
) -> str:
    """합성 SEC full-submission `.txt` — SEC-HEADER + 10-K(primary) + EX-101.PRE/LAB DOCUMENT."""
    header = (
        "<SEC-DOCUMENT>x.txt\n<SEC-HEADER>x.hdr.sgml\n"
        f"CONFORMED SUBMISSION TYPE:\t{form}\n"
        f"ACCESSION NUMBER:\t\t{accession}\n"
        f"CONFORMED PERIOD OF REPORT:\t{periodEnd}\n"
        "FISCAL YEAR END:\t\t1231\n"
        "FILER:\n\tCOMPANY DATA:\n"
        f"\t\tCENTRAL INDEX KEY:\t\t\t{int(cik)}\n"
        "\t\tCOMPANY CONFORMED NAME:\t\t\tTEST CORP\n"
        "</SEC-HEADER>\n"
    )
    primary = (
        f"<DOCUMENT>\n<TYPE>{form}\n<SEQUENCE>1\n<FILENAME>test.htm\n<TEXT>\n<XBRL>\n"
        f"{synthPrimaryHtml()}\n</TEXT>\n</DOCUMENT>\n"
    )
    pre = f"<DOCUMENT>\n<TYPE>EX-101.PRE\n<SEQUENCE>5\n<FILENAME>test_pre.xml\n<TEXT>\n{synthPre()}\n</TEXT>\n</DOCUMENT>\n"
    lab = f"<DOCUMENT>\n<TYPE>EX-101.LAB\n<SEQUENCE>6\n<FILENAME>test_lab.xml\n<TEXT>\n{synthLab()}\n</TEXT>\n</DOCUMENT>\n"
    return header + primary + pre + lab + "</SEC-DOCUMENT>\n"
