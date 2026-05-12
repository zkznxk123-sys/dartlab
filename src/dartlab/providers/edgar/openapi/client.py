"""EDGAR OpenAPI 공통 HTTP 클라이언트."""

from __future__ import annotations

import time
from typing import Any

import httpx

DEFAULT_USER_AGENT = "DartLab eddmpython@gmail.com"
DEFAULT_BASE_URL = "https://data.sec.gov"
DEFAULT_SEC_URL = "https://www.sec.gov"


class EdgarApiError(RuntimeError):
    """SEC API 호출 오류."""


class EdgarClient:
    """SEC public API 클라이언트.

    원칙:
    - source-native JSON 응답 유지
    - polite pacing + 재시도
    - 실패는 명시적 예외로 전파
    """

    def __init__(
        self,
        *,
        userAgent: str | None = None,
        email: str | None = None,
        minInterval: float = 0.2,
        timeout: float = 30.0,
        maxRetries: int = 3,
    ):
        self.userAgent = self._buildUserAgent(userAgent=userAgent, email=email)
        self.minInterval = max(float(minInterval), 0.0)
        self.timeout = float(timeout)
        self.maxRetries = max(int(maxRetries), 1)
        self._session = httpx.Client(follow_redirects=True)
        self._lastRequestAt = 0.0

    @staticmethod
    def _buildUserAgent(*, userAgent: str | None, email: str | None) -> str:
        if userAgent:
            return userAgent
        if email:
            return f"DartLab {email}"
        return DEFAULT_USER_AGENT

    @property
    def headers(self) -> dict[str, str]:
        """SEC API 요청에 사용할 HTTP 헤더.

        Returns:
            ``{"User-Agent": ...}`` dict.

        Raises:
            없음.

        Example:
            >>> EdgarClient().headers

        LLM Specifications:
            AntiPatterns:
                - User-Agent 미설정 → 403. _buildUserAgent 가 기본 주입.
                - minInterval 너무 짧음 (< 0.1) → rate limit. 0.2 권장.
            OutputSchema:
                - dict / bytes / pl.DataFrame — endpoint 별.
            Prerequisites:
                - 인터넷 + SEC EDGAR public API.
            Freshness:
                - SEC EDGAR 실시간.
            Dataflow:
                - 인자 → httpx → SEC API → 정규화 → 본 함수.
            TargetMarkets:
                - US (SEC EDGAR).
        """
        return {"User-Agent": self.userAgent}

    def _wait(self) -> None:
        if self.minInterval <= 0:
            return
        now = time.monotonic()
        elapsed = now - self._lastRequestAt
        if elapsed < self.minInterval:
            time.sleep(self.minInterval - elapsed)

    def getJson(self, url: str) -> dict[str, Any]:
        """URL 에서 JSON 을 가져오고, 속도 제한과 재시도를 자동 처리.

        Args:
            url: SEC endpoint URL.

        Returns:
            JSON dict.

        Raises:
            EdgarApiError: API 호출 실패 또는 JSON object 아님.

        Example:
            >>> EdgarClient().getJson("https://data.sec.gov/...")

        SeeAlso:
            - ``AsyncEdgarClient`` — 비동기 버전.
            - ``OpenEdgar`` — facade.

        Requires:
            - httpx
            - time

        Capabilities:
            - SEC EDGAR public API 호출 + User-Agent 자동 주입 + polite pacing.

        Guide:
            - 사용자 facade 는 ``OpenEdgar()`` — 본 클래스 직접 호출 X.

        AIContext:
            internal SEC client — AI 직접 호출 X.

        LLM Specifications:
            AntiPatterns:
                - User-Agent 미설정 → 403. _buildUserAgent 가 기본 주입.
                - minInterval 너무 짧음 (< 0.1) → rate limit. 0.2 권장.
            OutputSchema:
                - dict / bytes / pl.DataFrame — endpoint 별.
            Prerequisites:
                - 인터넷 + SEC EDGAR public API.
            Freshness:
                - SEC EDGAR 실시간.
            Dataflow:
                - 인자 → httpx → SEC API → 정규화 → 본 함수.
            TargetMarkets:
                - US (SEC EDGAR).
        """
        lastErr: Exception | None = None
        for attempt in range(self.maxRetries):
            self._wait()
            try:
                resp = self._session.get(url, headers=self.headers, timeout=self.timeout)
                self._lastRequestAt = time.monotonic()
                resp.raise_for_status()
                data = resp.json()
                if not isinstance(data, dict):
                    raise EdgarApiError(f"JSON object expected: {url}")
                return data
            except httpx.HTTPStatusError as exc:
                lastErr = exc
                status = exc.response.status_code
                if status not in (429, 500, 502, 503, 504) or attempt == self.maxRetries - 1:
                    raise EdgarApiError(f"SEC API 요청 실패 ({status}): {url}") from exc
                time.sleep(2**attempt)
            except httpx.HTTPError as exc:
                lastErr = exc
                if attempt == self.maxRetries - 1:
                    raise EdgarApiError(f"SEC API 네트워크 오류: {url}") from exc
                time.sleep(2**attempt)
        if lastErr is not None:
            raise EdgarApiError(f"SEC API 요청 실패: {url}") from lastErr
        raise EdgarApiError(f"SEC API 요청 실패: {url}")
