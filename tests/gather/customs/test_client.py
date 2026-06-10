"""관세청 client XML 파싱 회귀 — gather/customs/client.py (네트워크 없음).

정상 item dict / 시스템오류(cmmMsgHeader) / 트래픽한도 / resultCode 분류.
"""

from __future__ import annotations

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
