"""관세청 무역통계 REST 클라이언트 — rate limit + retry + XML 파싱.

공공데이터포털 관세청_품목별 국가별 수출입실적(GW). HTTP only(비-TLS), 응답 XML
전용(resultType=json 미지원). cntyCd 생략 시 전 국가 합산행 + 월별·하위HS·국가
분해행을 반환 — 월별 국가총계는 series 레이어가 합산해 환원한다.
인증키(`DATA_GO_KR_KEY`, Decoding)는 credentials 레지스트리로 해석.
"""

from __future__ import annotations

import logging
import time
import xml.etree.ElementTree as ET

import httpx

from dartlab.core.providers.dataCredentials import resolveKey

from .types import CustomsError, RateLimitError

log = logging.getLogger(__name__)

_BASE_URL = "http://apis.data.go.kr/1220000/nitemtrade/getNitemtradeList"

# 일 10,000건 한도 — 보수적 60 RPM 슬라이딩 윈도.
_RATE_LIMIT_RPM = 60
_RATE_LIMIT_WINDOW = 60.0


class CustomsClient:
    """관세청 품목별 수출입실적 REST 클라이언트.

    - 인증키 ``DATA_GO_KR_KEY`` (Decoding) — credentials.resolveKey 해석.
    - 60 RPM 슬라이딩 레이트 리밋.
    - 5xx/타임아웃 지수 백오프 재시도 (최대 3회).
    """

    def __init__(self, apiKey: str | None = None) -> None:
        self._key = resolveKey("dataGoKr", apiKey)
        self._session = httpx.Client(headers={"User-Agent": "dartlab-customs/1.0"}, follow_redirects=True)
        self._timestamps: list[float] = []

    def _rateLimit(self) -> None:
        now = time.monotonic()
        self._timestamps = [t for t in self._timestamps if now - t < _RATE_LIMIT_WINDOW]
        if len(self._timestamps) >= _RATE_LIMIT_RPM:
            wait = _RATE_LIMIT_WINDOW - (now - self._timestamps[0])
            if wait > 0:
                time.sleep(wait)
        self._timestamps.append(time.monotonic())

    def get(self, hsCode: str, startYm: str, endYm: str, *, numOfRows: int = 10000) -> list[dict[str, str]]:
        """단일 (HS, 기간) 조회 → raw item dict 리스트.

        Capabilities: 관세청 품목별 수출입실적 1콜 + XML 파싱 + resultCode 검증.
            cntyCd 생략 → 전 국가 합산. 윈도는 1년 이내 (caller 분할).

        Args:
            hsCode: HS 코드 (2/4/6자리). API ``hsSgn`` 파라미터.
            startYm: 시작 년월 ``YYYYMM``.
            endYm: 종료 년월 ``YYYYMM`` (startYm 과 최대 12개월 이내).
            numOfRows: 페이지당 행수 (기본 10000 — 1년치 하위분해 수용).

        Returns:
            list[dict[str, str]] — item 별 원본 태그 dict (year/hsCd/expDlr/impDlr/
            balPayments/expWgt/impWgt 등). 빈 결과는 [].

        Raises:
            CustomsError: resultCode 비정상 또는 시스템 오류 XML.
            RateLimitError: 트래픽 한도 초과(returnReasonCode 22).
            httpx.HTTPStatusError: 재시도 후에도 4xx/5xx.

        Example:
            >>> rows = CustomsClient(apiKey=key).get("8542", "202601", "202603")  # doctest: +SKIP
        """
        params = {
            "serviceKey": self._key,
            "strtYymm": startYm,
            "endYymm": endYm,
            "hsSgn": hsCode,
            "numOfRows": str(numOfRows),
            "pageNo": "1",
        }
        text = self._requestWithRetry(params)
        return _parseItems(text)

    def _requestWithRetry(self, params: dict[str, str], *, maxRetries: int = 3) -> str:
        delay = 1.0
        lastError: Exception | None = None
        for attempt in range(maxRetries):
            self._rateLimit()
            try:
                resp = self._session.get(_BASE_URL, params=params, timeout=60.0)
                if resp.status_code >= 500:
                    raise httpx.HTTPStatusError("5xx", request=resp.request, response=resp)
                resp.raise_for_status()
                return resp.text
            except (httpx.HTTPStatusError, httpx.TransportError) as exc:
                lastError = exc
                if attempt < maxRetries - 1:
                    time.sleep(delay)
                    delay *= 2
        raise CustomsError(f"관세청 API 요청 실패 (재시도 {maxRetries}회): {lastError}") from lastError

    def close(self) -> None:
        """HTTP 세션 종료 (idempotent).

        Raises:
            없음.

        Example:
            >>> CustomsClient(apiKey="x").close()
        """
        self._session.close()


def _parseItems(text: str) -> list[dict[str, str]]:
    """관세청 응답 XML → item dict 리스트. 시스템 오류 XML 은 예외."""
    try:
        root = ET.fromstring(text)
    except ET.ParseError as exc:
        raise CustomsError(f"관세청 응답 XML 파싱 실패: {exc}") from exc

    # 시스템 오류 (키 미등록·트래픽 초과 등) — cmmMsgHeader 구조.
    cmm = root.find(".//cmmMsgHeader")
    if cmm is not None:
        code = (cmm.findtext("returnReasonCode") or "").strip()
        msg = (cmm.findtext("returnAuthMsg") or cmm.findtext("errMsg") or "").strip()
        if code == "22":
            raise RateLimitError(f"관세청 트래픽 한도 초과 (code 22): {msg}")
        raise CustomsError(f"관세청 시스템 오류 (code {code}): {msg}")

    header = root.find("./header")
    if header is not None:
        code = (header.findtext("resultCode") or "").strip()
        if code and code != "00":
            raise CustomsError(f"관세청 resultCode {code}: {header.findtext('resultMsg')}")

    items = root.findall("./body/items/item")
    return [{child.tag: (child.text or "").strip() for child in item} for item in items]
