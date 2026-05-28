"""Point-in-Time (PIT) 필터 — bitemporal 시계열 as-of 조회 SSOT.

look-ahead bias 차단의 본질. backtest 신뢰성 95→99% 진입.

Bitemporal 데이터:
- ``business_time`` — 실제 발생일 (예: 2024-03-15 종가)
- ``knowledge_time`` — 우리가 알게 된 일 (예: 2024-03-16 04:00 수집)

as-of T 조회 = (business_time ≤ T) AND (knowledge_time ≤ T).
restatement (정정공시) 후에도 *옛 T 시점에 알려진 값* 만 사용.

기존 단일 시간 컬럼 (``date``) 만 있는 데이터는 자동 fallback —
business_time 만 있다고 가정 (knowledge_time 누락 시 무한 작은 값으로 처리).
"""

from __future__ import annotations

import logging

import polars as pl

log = logging.getLogger(__name__)


def applyAsOf(
    df: pl.DataFrame,
    asof: str | None,
    *,
    businessCol: str = "business_time",
    knowledgeCol: str = "knowledge_time",
    fallbackCol: str = "date",
) -> pl.DataFrame:
    """as-of 시점 PIT 필터링 — bitemporal 우선, 단일 컬럼 fallback.

    Sig: ``applyAsOf(df, asof, *, businessCol='business_time', knowledgeCol='knowledge_time', fallbackCol='date') -> pl.DataFrame``

    Capabilities: business_time + knowledge_time 동시 필터, 미존재 시 fallbackCol.
    AIContext: backtest 호출 시 look-ahead bias 차단의 단일 진입. 모든 시계열 fetch 호출 의 마지막 stage.
    Guide: asof 가 None 이면 df 그대로 반환. 컬럼 자동 감지 — bitemporal 우선, 없으면 fallback.
    When: gather (price/macro/etc.) 결과를 as_of 시점으로 잘라야 할 때.
    How: 컬럼 존재 분기 → polars filter (date ≤ asof) → 결과 DataFrame.

    Args:
        df: 입력 DataFrame (date 또는 business_time/knowledge_time 컬럼 보유).
        asof: ISO 날짜 ``"YYYY-MM-DD"`` 또는 None (no-op).
        businessCol: bitemporal business time 컬럼 이름.
        knowledgeCol: bitemporal knowledge time 컬럼 이름.
        fallbackCol: bitemporal 컬럼 없을 때 사용할 단일 시간 컬럼.

    Returns:
        필터된 DataFrame. asof None 시 원본.

    Raises:
        없음 — 컬럼 누락 시 logger.debug + 원본 반환.

    Example:
        >>> applyAsOf(df, "2020-12-31")  # 그 시점 알 수 있었던 데이터만

    See Also:
        ``dartlab.gather.macroProvider.applyAsOf`` — date 단일 컬럼 한정 (legacy, 본 함수가 일반화).
    """
    if asof is None or df is None or df.is_empty():
        return df

    # polars date 컬럼은 string 비교 못 함 — 명시 cast.
    from datetime import date as _date

    if isinstance(asof, str):
        try:
            cutoff = _date.fromisoformat(asof[:10])
        except ValueError:
            log.warning("applyAsOf: asof 파싱 실패 (%s) — 원본 반환", asof)
            return df
    else:
        cutoff = asof

    cols = set(df.columns)
    if businessCol in cols and knowledgeCol in cols:
        return df.filter((pl.col(businessCol) <= cutoff) & (pl.col(knowledgeCol) <= cutoff))
    if businessCol in cols:
        return df.filter(pl.col(businessCol) <= cutoff)
    if fallbackCol in cols:
        return df.filter(pl.col(fallbackCol) <= cutoff)
    log.debug("applyAsOf: 시간 컬럼 없음 (%s/%s/%s) — 원본 반환", businessCol, knowledgeCol, fallbackCol)
    return df


def hasBitemporal(df: pl.DataFrame) -> bool:
    """DataFrame 이 bitemporal (business_time + knowledge_time) 스키마인지 확인.

    Sig: ``hasBitemporal(df) -> bool``

    Capabilities: 두 컬럼 동시 존재 여부 boolean.
    AIContext: 다운스트림 (factor/scan) 이 PIT 활성 여부 판단.
    Guide: 둘 다 있어야 True.
    When: 컬럼 분기 직전.
    How: set membership.

    Args:
        df: 검사 대상.

    Returns:
        True 면 bitemporal, False 면 legacy (date 또는 business_time 만).

    Raises:
        없음.

    Example:
        >>> hasBitemporal(df)

    See Also:
        ``applyAsOf``.
    """
    if df is None:
        return False
    cols = set(df.columns)
    return "business_time" in cols and "knowledge_time" in cols
