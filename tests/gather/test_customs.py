"""관세청 무역통계 소스 회귀 — `gather/customs/` (네트워크 없음).

검증:
  1. XML 파싱 — 정상 item dict / 시스템오류(cmmMsgHeader) / 트래픽한도 / resultCode.
  2. 월 파싱·윈도 분할 — '2025.10'→date, '총계' 제외, 1년 윈도 경계.
  3. 월별 집계 — 하위HS·국가행 합산, 총계행 제외, metric 선택.
  4. fetchSeries — stub client 로 (date, value) 환원 + metric 전환 + 잘못된 metric.
  5. catalog — getAllEntries/getEntry/Customs.catalog 형태 (명시 키, 무네트워크).
"""

from __future__ import annotations

import datetime as dt

import pytest

pytestmark = pytest.mark.unit

_OK_XML = (
    "<response><header><resultCode>00</resultCode><resultMsg>정상서비스.</resultMsg></header>"
    "<body><items>"
    "<item><year>총계</year><hsCd>-</hsCd><expDlr>150</expDlr><impDlr>50</impDlr><balPayments>100</balPayments></item>"
    "<item><year>2025.10</year><hsCd>854231</hsCd><expDlr>100</expDlr><impDlr>40</impDlr><balPayments>60</balPayments></item>"
    "<item><year>2025.10</year><hsCd>854239</hsCd><expDlr>50</expDlr><impDlr>10</impDlr><balPayments>40</balPayments></item>"
    "</items></body></response>"
)
_KEY_ERR_XML = (
    "<OpenAPI_ServiceResponse><cmmMsgHeader>"
    "<returnReasonCode>30</returnReasonCode><returnAuthMsg>SERVICE_KEY_IS_NOT_REGISTERED_ERROR</returnAuthMsg>"
    "</cmmMsgHeader></OpenAPI_ServiceResponse>"
)
_RATE_XML = (
    "<OpenAPI_ServiceResponse><cmmMsgHeader>"
    "<returnReasonCode>22</returnReasonCode><returnAuthMsg>LIMITED_NUMBER_OF_SERVICE_REQUESTS_EXCEEDS</returnAuthMsg>"
    "</cmmMsgHeader></OpenAPI_ServiceResponse>"
)


def test_parseItems_ok() -> None:
    from dartlab.gather.customs.client import _parseItems

    items = _parseItems(_OK_XML)
    assert len(items) == 3
    assert items[1]["year"] == "2025.10"
    assert items[1]["expDlr"] == "100"


def test_parseItems_key_error() -> None:
    from dartlab.gather.customs.client import _parseItems
    from dartlab.gather.customs.types import CustomsError

    with pytest.raises(CustomsError):
        _parseItems(_KEY_ERR_XML)


def test_parseItems_rate_limit() -> None:
    from dartlab.gather.customs.client import _parseItems
    from dartlab.gather.customs.types import RateLimitError

    with pytest.raises(RateLimitError):
        _parseItems(_RATE_XML)


def test_parseItems_bad_resultcode() -> None:
    from dartlab.gather.customs.client import _parseItems
    from dartlab.gather.customs.types import CustomsError

    xml = "<response><header><resultCode>03</resultCode><resultMsg>NODATA</resultMsg></header><body><items/></body></response>"
    with pytest.raises(CustomsError):
        _parseItems(xml)


def test_parseMonth() -> None:
    from dartlab.gather.customs.series import _parseMonth

    assert _parseMonth("2025.10") == dt.date(2025, 10, 1)
    assert _parseMonth("총계") is None
    assert _parseMonth("garbage") is None


def test_monthWindows_splits_by_year() -> None:
    from dartlab.gather.customs.series import _monthWindows

    wins = _monthWindows("202001", "202212", maxMonths=12)
    assert wins == [("202001", "202012"), ("202101", "202112"), ("202201", "202212")]
    # 역순/단월
    assert _monthWindows("202205", "202201") == []
    assert _monthWindows("202203", "202203") == [("202203", "202203")]


def test_aggregateMonthly_excludes_total() -> None:
    from dartlab.gather.customs.client import _parseItems
    from dartlab.gather.customs.series import _aggregateMonthly

    items = _parseItems(_OK_XML)
    agg = _aggregateMonthly(items, "expDlr")
    # 총계행 제외, 같은 월 하위코드 합산 (100 + 50)
    assert agg == {dt.date(2025, 10, 1): 150.0}


class _StubClient:
    def __init__(self, items: list[dict]) -> None:
        self._items = items
        self.calls = 0

    def get(self, hsCode: str, startYm: str, endYm: str, **_: object) -> list[dict]:
        self.calls += 1
        return self._items


def test_fetchSeries_aggregates_and_metric() -> None:
    from dartlab.gather.customs.series import fetchSeries

    items = [
        {"year": "총계", "expDlr": "999", "impDlr": "0", "balPayments": "999"},
        {"year": "2025.10", "expDlr": "100", "impDlr": "40", "balPayments": "60"},
        {"year": "2025.10", "expDlr": "50", "impDlr": "10", "balPayments": "40"},
        {"year": "2025.11", "expDlr": "200", "impDlr": "0", "balPayments": "200"},
    ]
    stub = _StubClient(items)
    df = fetchSeries(stub, "8542", start="2025-10", end="2025-11", metric="expDlr")
    assert df["date"].to_list() == [dt.date(2025, 10, 1), dt.date(2025, 11, 1)]
    assert df["value"].to_list() == [150.0, 200.0]

    bal = fetchSeries(stub, "8542", start="2025-10", end="2025-11", metric="balPayments")
    assert bal["value"].to_list() == [100.0, 200.0]


def test_fetchSeries_invalid_metric() -> None:
    from dartlab.gather.customs.series import fetchSeries

    with pytest.raises(ValueError):
        fetchSeries(_StubClient([]), "8542", metric="nope")


def test_catalog_entries_and_lookup() -> None:
    from dartlab.gather.customs import getAllEntries, getEntry

    entries = getAllEntries()
    assert len(entries) >= 15
    assert getEntry("8542").group == "반도체"
    assert getEntry("0000") is None
    # id 중복 없음
    ids = [e.id for e in entries]
    assert len(ids) == len(set(ids))


def test_facade_catalog_no_network() -> None:
    from dartlab.gather.customs import Customs, getAllEntries

    c = Customs(apiKey="dummy")  # 명시 키 — 무네트워크
    assert c.catalog("반도체").height == 2
    full = c.catalog()
    assert full.height == len(getAllEntries())
    assert set(full.columns) == {"id", "label", "group", "frequency", "unit", "description"}
