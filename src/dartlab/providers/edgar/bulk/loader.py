"""edgar/bulk LoaderProvider 구현 (정공법 B — DIP).

`core/dataLoader.py` 가 직접 ensureFinanceParquet 호출 대신 registry dispatch.
import 시점에 registerLoader 호출하여 자동 등록.
"""

from __future__ import annotations

from dartlab.providers.edgar.bulk.companyfactsBulk import ensureFinanceParquet


class EdgarBulkLoader:
    """edgar 카테고리의 LoaderProvider 구현 (SEC 벌크 finance)."""

    category = "edgar"

    def ensure(self, stockCode, path, *, sinceYear=None, asOf=None, refresh="auto"):
        """SEC 벌크 finance parquet 보장 — ``ensureFinanceParquet`` 위임.

        Args:
            stockCode: 종목 ticker.
            path: 결과 parquet 경로.
            sinceYear: 시작 연도 (현재 미사용).
            asOf: 신선도 기준 시점 (현재 미사용).
            refresh: ``"auto"`` 외 truthy 면 강제 재변환.

        Raises:
            FileNotFoundError: 변환 후에도 CIK parquet 부재.

        Example:
            >>> EdgarBulkLoader().ensure("AAPL", Path("..."))

        SeeAlso:
            - <TODO: 관련 함수/엔진>

        Requires:
            - dartlab

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
        ensureFinanceParquet(stockCode, path, refresh=bool(refresh and refresh != "auto"))


def registerEdgarBulkLoader() -> None:
    """edgar/bulk LoaderProvider 등록 — circular import 회피용 함수 lazy import.

    Raises:
        없음.

    Example:
        >>> registerEdgarBulkLoader()

    SeeAlso:
        - <TODO: 관련 함수/엔진>

    Requires:
        - dartlab

    Capabilities:
        - <TODO: 함수 핵심 책임 요약>

    Guide:
        - <TODO: 사용 시나리오>

    AIContext:
        <TODO: AI 호출 컨텍스트>
    """
    from dartlab.frame.loaders import registerLoader

    registerLoader(EdgarBulkLoader())
