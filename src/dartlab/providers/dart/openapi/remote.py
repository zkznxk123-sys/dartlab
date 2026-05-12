"""원격 dartlab 서버를 통한 OpenDART 프록시 클라이언트.

DART API 키가 없을 때 DartClient 대신 사용.
서버(HF Spaces 등)에 DART_API_KEY가 있으므로 사용자는 키 없이 사용 가능.
"""

from __future__ import annotations

import logging
import os

import httpx
import polars as pl

_log = logging.getLogger(__name__)

_DEFAULT_SERVER = "https://eddmpython-dartlab.hf.space"


def _serverUrl() -> str:
    return os.environ.get("DARTLAB_SERVER_URL", _DEFAULT_SERVER)


class RemoteDartClient:
    """원격 dartlab 서버 프록시. DartClient의 핵심 인터페이스 호환."""

    def __init__(self):
        self._base = _serverUrl().rstrip("/")
        self._session = httpx.Client(timeout=30.0, follow_redirects=True)
        _log.info("RemoteDartClient: %s", self._base)

    def getJson(self, endpoint: str, params: dict, *, emptyOn013: bool = False) -> dict:
        """서버 프록시를 통한 JSON 조회.

        Args:
            endpoint: 인자.
            params: 인자.
            emptyOn013: 인자.

        Raises:
            없음.

        Example:
            >>> getJson(...)

        Returns:
            dict — DART API JSON 응답 (프록시).

        SeeAlso:
            - ``DartClient`` — 로컬 키 사용 클라이언트 (본 모듈의 대안).
            - ``DARTLAB_SERVER_URL`` 환경변수.

        Requires:
            - httpx
            - logging
            - polars

        Capabilities:
            - DART API 키 없는 사용자용 — dartlab HF Spaces 서버를 프록시로 사용. DartClient 인터페이스 호환.

        Guide:
            - "DART 키 없이 사용" → 본 client.

        AIContext:
            internal proxy — AI 직접 호출 X.

        LLM Specifications:
            AntiPatterns:
                - 서버 다운 시 fallback X — caller 가 RuntimeError 분기 의무.
                - 프록시 latency (네트워크 hop 추가).
            OutputSchema:
                - dict / pl.DataFrame / bytes — endpoint 별.
            Prerequisites:
                - 인터넷 + dartlab 서버 (HF Spaces) 접근.
            Freshness:
                - DART OpenAPI 실시간 (프록시 hop 추가).
            Dataflow:
                - 사용자 인자 → dartlab 서버 → DART API → 응답 → 본 함수.
            TargetMarkets:
                - KR (DART) — 프록시 client.
        """
        url = f"{self._base}/api/dart{endpoint}"
        resp = self._session.get(url, params=params)
        resp.raise_for_status()
        return resp.json()

    def getDf(self, endpoint: str, params: dict, listKey: str = "list") -> pl.DataFrame:
        """서버 프록시를 통한 DataFrame 조회.

        Args:
            endpoint: 인자.
            params: 인자.
            listKey: 인자.

        Raises:
            없음.

        Example:
            >>> getDf(...)

        Returns:
            pl.DataFrame — DART API 응답 정규화 (프록시).

        SeeAlso:
            - ``DartClient`` — 로컬 키 사용 클라이언트 (본 모듈의 대안).
            - ``DARTLAB_SERVER_URL`` 환경변수.

        Requires:
            - httpx
            - logging
            - polars

        Capabilities:
            - DART API 키 없는 사용자용 — dartlab HF Spaces 서버를 프록시로 사용. DartClient 인터페이스 호환.

        Guide:
            - "DART 키 없이 사용" → 본 client.

        AIContext:
            internal proxy — AI 직접 호출 X.

        LLM Specifications:
            AntiPatterns:
                - 서버 다운 시 fallback X — caller 가 RuntimeError 분기 의무.
                - 프록시 latency (네트워크 hop 추가).
            OutputSchema:
                - dict / pl.DataFrame / bytes — endpoint 별.
            Prerequisites:
                - 인터넷 + dartlab 서버 (HF Spaces) 접근.
            Freshness:
                - DART OpenAPI 실시간 (프록시 hop 추가).
            Dataflow:
                - 사용자 인자 → dartlab 서버 → DART API → 응답 → 본 함수.
            TargetMarkets:
                - KR (DART) — 프록시 client.
        """
        data = self.getJson(endpoint, params)
        rows = data.get("rows", data.get(listKey, []))
        if not rows:
            return pl.DataFrame()
        return pl.DataFrame(rows)

    def getDfAll(self, endpoint: str, params: dict, listKey: str = "list", pageSize: int = 100) -> pl.DataFrame:
        """getDf와 동일 (서버가 페이지네이션 처리).

        Args:
            endpoint: 인자.
            params: 인자.
            listKey: 인자.
            pageSize: 인자.

        Raises:
            없음.

        Example:
            >>> getDfAll(...)

        Returns:
            pl.DataFrame — DART API 응답 정규화 (프록시).

        LLM Specifications:
            AntiPatterns:
                - 서버 다운 시 fallback X — caller RuntimeError 분기.
            OutputSchema:
                - dict / pl.DataFrame / bytes — endpoint 별.
            Prerequisites:
                - 인터넷 + dartlab 서버.
            Freshness:
                - DART OpenAPI 실시간 (프록시 hop).
            Dataflow:
                - 사용자 인자 → dartlab 서버 → DART API → 본 함수.
            TargetMarkets:
                - KR (DART) — 프록시.
        """
        return self.getDf(endpoint, params, listKey=listKey)
