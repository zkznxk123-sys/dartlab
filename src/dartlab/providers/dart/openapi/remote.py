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
            <TODO: return desc> (dict)

        SeeAlso:
            - <TODO: 관련 함수/엔진>

        Requires:
            - httpx
            - logging
            - polars

        Capabilities:
            - <TODO: 함수 핵심 책임 요약>

        Guide:
            - <TODO: 사용 시나리오>

        AIContext:
            <TODO: AI 호출 컨텍스트>

        LLM Specifications:
            AntiPatterns:
                - <TODO: 안티패턴>
            OutputSchema:
                - <TODO: 출력 형태>
            Prerequisites:
                - <TODO: 사전조건>
            Freshness:
                - <TODO: 데이터 freshness>
            Dataflow:
                - <TODO: 데이터 흐름>
            TargetMarkets:
                - <TODO: 대상 시장>
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
            <TODO: return desc> (pl.DataFrame)

        SeeAlso:
            - <TODO: 관련 함수/엔진>

        Requires:
            - httpx
            - logging
            - polars

        Capabilities:
            - <TODO: 함수 핵심 책임 요약>

        Guide:
            - <TODO: 사용 시나리오>

        AIContext:
            <TODO: AI 호출 컨텍스트>

        LLM Specifications:
            AntiPatterns:
                - <TODO: 안티패턴>
            OutputSchema:
                - <TODO: 출력 형태>
            Prerequisites:
                - <TODO: 사전조건>
            Freshness:
                - <TODO: 데이터 freshness>
            Dataflow:
                - <TODO: 데이터 흐름>
            TargetMarkets:
                - <TODO: 대상 시장>
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
            <TODO: return desc> (pl.DataFrame)

        LLM Specifications:
            AntiPatterns:
                - <TODO: 안티패턴>
            OutputSchema:
                - <TODO: 출력 형태>
            Prerequisites:
                - <TODO: 사전조건>
            Freshness:
                - <TODO: 데이터 freshness>
            Dataflow:
                - <TODO: 데이터 흐름>
            TargetMarkets:
                - <TODO: 대상 시장>
        """
        return self.getDf(endpoint, params, listKey=listKey)
