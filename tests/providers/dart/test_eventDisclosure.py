"""eventDisclosure — KRX 수시공시 본문 파서 회귀 가드.

전수 실측(7,913 공시) 에서 발견한 병합-셀 concatenation 오파싱(b2b 3e14) + 값-정합 가드 박제.
순수 로직 (HTML string in → dict out), 데이터 로드 없음.
"""

from __future__ import annotations

import pytest

from dartlab.providers.dart.eventDisclosure import (
    classifyEventReport,
    expectedFields,
    parseEventDisclosure,
)
from dartlab.providers.dart.parse.htmlTableParser import flattenTableCells

pytestmark = [pytest.mark.unit]


def test_flatten_multi_table():
    html = "<table><tr><td>a</td><td>1</td></tr></table><table><tr><td>b</td><td>2</td></tr></table>"
    assert flattenTableCells(html) == ["a", "1", "b", "2"]


def test_parse_clean_contract():
    # 현대건설 양식 — 라벨 다음 단일 숫자 셀
    html = (
        "<table>"
        "<tr><td>계약금액 총액(원)</td><td>853,142,656,380</td></tr>"
        "<tr><td>최근 매출액(원)</td><td>31,062,912,168,499</td></tr>"
        "<tr><td>매출액 대비(%)</td><td>2.7</td></tr>"
        "<tr><td>3. 계약상대</td><td>범천4구역 주택재개발정비사업조합</td></tr>"
        "<tr><td>7. 계약(수주)일자</td><td>2026-06-22</td></tr>"
        "</table>"
    )
    row = parseEventDisclosure(html)
    assert row["contractAmount"] == 853142656380.0
    assert row["recentRevenue"] == 31062912168499.0
    assert row["revenueRatio"] == 2.7
    assert "범천4구역" in row["counterparty"]
    assert row["orderDate"] == "2026-06-22"


def test_merged_cell_not_astronomical():
    # 일부 양식의 '계약내역' 병합 셀 — parseAmount concatenation garbage(천문학적) 차단.
    # 병합 셀 다음에 깨끗한 '계약금액 총액(원)' 행이 따라온다 → 그 값을 채택.
    html = (
        "<table>"
        "<tr><td>2. 계약내역 - 확정 계약금액 - 계약금액 총액(원) - 매출액 대비(%)</td>"
        "<td>- 48,427,000,000 - 48,427,000,000 - 14.34</td></tr>"
        "<tr><td>계약금액 총액(원)</td><td>65,589,000,000</td></tr>"
        "<tr><td>매출액 대비(%)</td><td>19.43</td></tr>"
        "</table>"
    )
    row = parseEventDisclosure(html)
    # 천문학적 concatenation(4.8e24) 이 아니라 깨끗한 총액
    assert row["contractAmount"] == 65589000000.0
    assert row["contractAmount"] < 1e15


def test_value_sanity_guard():
    # 계약금액/최근매출*100 이 신고 매출대비%와 크게 어긋나면 오파싱 → contractAmount None.
    html = (
        "<table>"
        "<tr><td>계약금액 총액(원)</td><td>100</td></tr>"
        "<tr><td>최근 매출액(원)</td><td>100</td></tr>"
        "<tr><td>매출액 대비(%)</td><td>2.7</td></tr>"
        "</table>"
    )
    row = parseEventDisclosure(html)  # implied 100% vs 신고 2.7% → 불일치
    assert row["contractAmount"] is None
    assert row.get("amountSuspect") is True


def test_value_sanity_passes_consistent():
    html = (
        "<table>"
        "<tr><td>계약금액 총액(원)</td><td>270</td></tr>"
        "<tr><td>최근 매출액(원)</td><td>10000</td></tr>"
        "<tr><td>매출액 대비(%)</td><td>2.7</td></tr>"
        "</table>"
    )
    row = parseEventDisclosure(html)  # implied 2.7% == 신고 2.7%
    assert row["contractAmount"] == 270.0
    assert row.get("amountSuspect") is None


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("단일판매ㆍ공급계약체결", "contract"),
        ("[기재정정]단일판매ㆍ공급계약체결", "amend"),
        ("단일판매ㆍ공급계약해지", "cancel"),
        ("연결재무제표기준영업(잠정)실적", "other"),
    ],
)
def test_classify_report(name, expected):
    assert classifyEventReport(name) == expected


def test_expected_fields():
    fields = expectedFields("supplyContract")
    assert "contractAmount" in fields
    assert "recentRevenue" in fields
    assert "revenueRatio" in fields
