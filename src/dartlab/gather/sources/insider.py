"""내부자 거래 facade -- KR(DART)."""

from __future__ import annotations

import logging

from dartlab.core.insiderRawProvider import getInsiderRawProvider

from ..types import InsiderTrade, MajorHolder

log = logging.getLogger(__name__)


async def fetchInsiderTrading(
    stockCode: str,
    *,
    market: str = "KR",
    limit: int | None = None,
    **_kwargs,
) -> list[InsiderTrade]:
    """내부자(임원/주요주주) 거래 내역 -- KR만 지원.

    Capabilities:
        - DART OpenAPI elestock raw → ``InsiderTrade`` dataclass 변환.
        - KR 외 시장은 빈 list (provider 부재).
        - DIP — ``core.insiderRawProvider`` 통해 ``providers/dart/ops/insiderTrades``
          호출. gather → providers 직접 의존 0.

    Args:
        stockCode: 종목코드 (예: "005930").
        market: 시장 코드. "KR" 외엔 빈 리스트.
        limit: 반환 행수 상한 (가장 최근 N건). None 이면 전체.
        **_kwargs: 미사용 — facade signature 일관성.

    Returns:
        list[InsiderTrade] — 거래 내역. 필드 (date / name / position / tradeType /
        changeShares / afterShares / reason). KR 외 시장이거나 provider 부재 / 조회
        실패 시 빈 리스트 [].

    Raises:
        없음 — provider 내부 예외 (OSError/TypeError) 는 흡수.

    Example:
        >>> trades = await fetchInsiderTrading("005930", market="KR", limit=10)

    Guide:
        - "삼성전자 내부자 매매" → ``await fetchInsiderTrading("005930", limit=20)``.
        - DART API key 부재 환경 (CI / pyodide) 에서는 silent 빈 list.

    When:
        - gather pipeline 의 internal-trades axis 호출 시점.

    How:
        - ``getInsiderRawProvider()`` lookup → raw fetch → ``InsiderTrade(**row)`` 변환.

    SeeAlso:
        - ``fetchMajorShareholders`` — 5% 이상 대량보유 변동 별도 endpoint.
        - ``dartlab.core.insiderRawProvider`` — DIP Protocol.
        - ``dartlab.providers.dart.ops.insiderTrades`` — DART OpenAPI 본체.

    Requires:
        - KR: DART_API_KEY env (DART OpenAPI 키).

    AIContext:
        Ask Workbench 의 "내부자 거래" / "임원 매매" 토픽 추론 시 호출. KR 한정이라
        US (Form 4) 회사는 빈 list — caller 가 evidence 부재 메시지 준비.

    LLM Specifications:
        AntiPatterns:
            - market 미지정 호출 → KR 기본 — US 종목은 빈 list 반환. caller 가 market
              명시 권장.
            - 무제한 limit (limit=None) 으로 분석 파이프라인에서 호출 → 룰 8 위반.
        OutputSchema:
            - list[InsiderTrade] — 빈 list 가능.
        Prerequisites:
            - ``DART_API_KEY`` 등록 + ``providers/dart/ops/insiderTrades`` 모듈 import 가능.
        Freshness:
            - DART OpenAPI 실시간 (접수 후 5 영업일 이내).
        Dataflow:
            - InsiderRawProvider → raw dict → InsiderTrade.
        TargetMarkets:
            - KR (DART). US (Form 4) 은 별도 트랙.
    """
    if market != "KR":
        return []
    provider = getInsiderRawProvider()
    if provider is None:
        return []
    try:
        rawRows = await provider.fetchInsiderTradingRaw(stockCode)
        rows = [InsiderTrade(**row) for row in rawRows]
        if limit is not None and limit > 0:
            return rows[:limit]
        return rows
    except (OSError, TypeError) as exc:
        log.warning("insider KR 실패 (%s): %s", stockCode, exc)
        return []


async def fetchMajorShareholders(
    stockCode: str,
    *,
    market: str = "KR",
    limit: int | None = None,
    **_kwargs,
) -> list[MajorHolder]:
    """5% 이상 대량보유 변동 -- KR(DART).

    Capabilities:
        - DART OpenAPI majorstock raw → ``MajorHolder`` dataclass 변환.
        - 5% 이상 보유 변동 (취득/처분/변동) 사건 추적.
        - DIP — ``core.insiderRawProvider`` 통해 호출. gather → providers 직접 의존 0.

    Args:
        stockCode: 종목코드 (예: "005930").
        market: 시장 코드. "KR" 외엔 빈 리스트.
        limit: 반환 행수 상한 (가장 최근 N건). None 이면 전체.
        **_kwargs: 미사용 — facade signature 일관성.

    Returns:
        list[MajorHolder] — 보유 변동. 필드 (holderName / shares / ratio /
        changeDate / changeType). KR 외 시장이거나 provider 부재 / 조회 실패
        시 빈 리스트 [].

    Raises:
        없음 — provider 내부 예외 (OSError/TypeError) 는 흡수.

    Example:
        >>> holders = await fetchMajorShareholders("005930", market="KR", limit=10)

    Guide:
        - "삼성전자 외국인/대주주 변동" → ``await fetchMajorShareholders("005930")``.
        - DART API key 부재 시 silent 빈 list.

    When:
        - gather pipeline 의 major-holders axis 호출 시점.

    How:
        - ``getInsiderRawProvider()`` lookup → raw fetch → ``MajorHolder(**row)`` 변환.

    SeeAlso:
        - ``fetchInsiderTrading`` — 임원 거래 별도 endpoint.
        - ``dartlab.core.insiderRawProvider`` — DIP Protocol.

    Requires:
        - KR: DART_API_KEY env.

    AIContext:
        외국인 지분 / M&A 시그널 탐지 파이프라인 호출. ratio 급변 (예 5% → 15%) =
        M&A 가능성 시그널.

    LLM Specifications:
        AntiPatterns:
            - ratio 의 절대값을 "현재 지분율" 로 해석 금지 — 변동 시점 snapshot.
            - 매우 작은 limit (1~2) 으로 trend 분석 시도 → 데이터 부족.
        OutputSchema:
            - list[MajorHolder] — 빈 list 가능.
        Prerequisites:
            - ``DART_API_KEY`` 등록.
        Freshness:
            - 변동 발생 후 5 영업일 이내 보고 의무.
        Dataflow:
            - InsiderRawProvider → raw dict → MajorHolder.
        TargetMarkets:
            - KR (DART). US SC 13D/G 는 별도 트랙.
    """
    if market != "KR":
        return []
    provider = getInsiderRawProvider()
    if provider is None:
        return []
    try:
        rawRows = await provider.fetchMajorShareholdersRaw(stockCode)
        rows = [MajorHolder(**row) for row in rawRows]
        if limit is not None and limit > 0:
            return rows[:limit]
        return rows
    except (OSError, TypeError) as exc:
        log.warning("majorShareholders 실패 (%s): %s", stockCode, exc)
        return []


def iterFetchInsiderTrading(
    stockCode: str,
    *,
    market: str = "KR",
    batchSize: int = 100,
):
    """fetchInsiderTrading 의 streaming pair — list 를 batchSize 단위 yield (A 트랙 I2).

    Capabilities: list[InsiderTrade] 를 batchSize slice yield.
    AIContext: informed trading 흐름의 chunk 처리.
    Guide: fetch 가 빈 list 면 yield 없음.
    When: 내부자 거래가 많은 회사의 chunk 처리 시.
    How: runAsync(fetchInsiderTrading) → list slice iterate.

    Args:
        stockCode: 종목코드.
        market: 시장. "KR"만 지원.
        batchSize: batch 크기.

    Yields:
        list[InsiderTrade] — 각 batch.

    Raises:
        없음.

    Example::

        for batch in iterFetchInsiderTrading("005930", batchSize=50): process(batch)

    Requires: KR DART_API_KEY env.
    See Also: ``fetchInsiderTrading``.
    """
    from ..infra.http import runAsync

    trades = runAsync(fetchInsiderTrading(stockCode, market=market))
    if not trades:
        return
    for i in range(0, len(trades), batchSize):
        yield trades[i : i + batchSize]


def iterFetchMajorShareholders(
    stockCode: str,
    *,
    market: str = "KR",
    batchSize: int = 100,
):
    """fetchMajorShareholders 의 streaming pair — list 를 batchSize 단위 yield (A 트랙 I2).

    Capabilities: list[MajorHolder] 를 batchSize slice yield.
    AIContext: 5% 보유 변동의 chunk 처리 — 시계열 활동 timeline.
    Guide: fetch 가 빈 list 면 yield 없음.
    When: 대량보유 변동이 많은 회사의 chunk 처리 시.
    How: runAsync(fetchMajorShareholders) → list slice iterate.

    Args:
        stockCode: 종목코드.
        market: 시장. "KR"만 지원.
        batchSize: batch 크기.

    Yields:
        list[MajorHolder] — 각 batch.

    Raises:
        없음.

    Example::

        for batch in iterFetchMajorShareholders("005930"): process(batch)

    Requires: KR DART_API_KEY env.
    See Also: ``fetchMajorShareholders``.
    """
    from ..infra.http import runAsync

    holders = runAsync(fetchMajorShareholders(stockCode, market=market))
    if not holders:
        return
    for i in range(0, len(holders), batchSize):
        yield holders[i : i + batchSize]
