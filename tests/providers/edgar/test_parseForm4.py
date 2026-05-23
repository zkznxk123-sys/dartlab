"""parseForm4Xml 실 구현 — SEC Form 4 ownership XML 파싱."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


_SAMPLE_FORM4_XML = """<?xml version="1.0"?>
<ownershipDocument>
  <reportingOwner>
    <reportingOwnerId>
      <rptOwnerCik>0001214156</rptOwnerCik>
      <rptOwnerName>COOK TIMOTHY D</rptOwnerName>
    </reportingOwnerId>
    <reportingOwnerRelationship>
      <isDirector>0</isDirector>
      <isOfficer>1</isOfficer>
      <officerTitle>CEO</officerTitle>
    </reportingOwnerRelationship>
  </reportingOwner>
  <nonDerivativeTable>
    <nonDerivativeTransaction>
      <transactionDate><value>2024-04-02</value></transactionDate>
      <transactionAmounts>
        <transactionShares><value>50000</value></transactionShares>
        <transactionPricePerShare><value>170.50</value></transactionPricePerShare>
      </transactionAmounts>
      <postTransactionAmounts>
        <sharesOwnedFollowingTransaction><value>3000000</value></sharesOwnedFollowingTransaction>
      </postTransactionAmounts>
      <transactionCoding>
        <transactionCode>S</transactionCode>
      </transactionCoding>
    </nonDerivativeTransaction>
  </nonDerivativeTable>
</ownershipDocument>
"""


def test_empty_xml() -> None:
    """빈 XML → 빈 DataFrame (schema 보존)."""
    from dartlab.providers.edgar.disclosure import parseForm4Xml

    df = parseForm4Xml("")
    assert df.is_empty()
    assert set(df.columns) == {
        "insider",
        "role",
        "transactionDate",
        "shares",
        "price",
        "postShares",
        "transactionCode",
    }


def test_malformed_xml() -> None:
    """잘못된 XML → 빈 DataFrame (graceful)."""
    from dartlab.providers.edgar.disclosure import parseForm4Xml

    df = parseForm4Xml("<not-form4")
    assert df.is_empty()


def test_extract_insider_name() -> None:
    """rptOwnerName 추출."""
    from dartlab.providers.edgar.disclosure import parseForm4Xml

    df = parseForm4Xml(_SAMPLE_FORM4_XML)
    assert df.shape[0] == 1
    assert df["insider"][0] == "COOK TIMOTHY D"


def test_extract_officer_role() -> None:
    """officer + officerTitle → role 합성."""
    from dartlab.providers.edgar.disclosure import parseForm4Xml

    df = parseForm4Xml(_SAMPLE_FORM4_XML)
    assert "officer" in df["role"][0].lower()
    assert "CEO" in df["role"][0]


def test_extract_transaction_amounts() -> None:
    """shares / price / postShares / transactionCode 정확 파싱."""
    from dartlab.providers.edgar.disclosure import parseForm4Xml

    df = parseForm4Xml(_SAMPLE_FORM4_XML)
    assert df["transactionDate"][0] == "2024-04-02"
    assert df["shares"][0] == 50000.0
    assert df["price"][0] == 170.50
    assert df["postShares"][0] == 3000000.0
    assert df["transactionCode"][0] == "S"


def test_multiple_transactions() -> None:
    """다중 nonDerivativeTransaction → 각 row."""
    from dartlab.providers.edgar.disclosure import parseForm4Xml

    xml = """<?xml version="1.0"?>
<ownershipDocument>
  <reportingOwner>
    <reportingOwnerId><rptOwnerName>Test Insider</rptOwnerName></reportingOwnerId>
    <reportingOwnerRelationship><isDirector>1</isDirector></reportingOwnerRelationship>
  </reportingOwner>
  <nonDerivativeTable>
    <nonDerivativeTransaction>
      <transactionDate><value>2024-01-15</value></transactionDate>
      <transactionAmounts>
        <transactionShares><value>100</value></transactionShares>
      </transactionAmounts>
      <transactionCoding><transactionCode>A</transactionCode></transactionCoding>
    </nonDerivativeTransaction>
    <nonDerivativeTransaction>
      <transactionDate><value>2024-02-15</value></transactionDate>
      <transactionAmounts>
        <transactionShares><value>200</value></transactionShares>
      </transactionAmounts>
      <transactionCoding><transactionCode>D</transactionCode></transactionCoding>
    </nonDerivativeTransaction>
  </nonDerivativeTable>
</ownershipDocument>"""
    df = parseForm4Xml(xml)
    assert df.shape[0] == 2
    assert df["transactionCode"].to_list() == ["A", "D"]
