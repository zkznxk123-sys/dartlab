"""narrative pulse 시계열 빌더 — (date × topic) 격자 (Phase B).

newsHeadlines.loadNewsArchive → scoreNewsBatch → clusterNewsTopics → 일별 aggregate.
analyzeNarrative (Phase C) 의 입력 SSOT.
"""

from __future__ import annotations

import logging
from datetime import date as _date

import polars as pl

log = logging.getLogger(__name__)


def buildNarrativePulse(
    start: str | _date,
    end: str | _date,
    market: str = "KR",
    *,
    asof: str | _date | None = None,
    sentimentModel: str = "auto",
    nrTopics: int | None = 30,
) -> pl.DataFrame:
    """기간 [start..end] news → 일별 topic pulse 시계열.

    Capabilities:
        - loadNewsArchive 위임 (PIT-safe asof 동행)
        - scoreNewsBatch sentiment + clusterNewsTopics topic
        - groupby(date, topic_id) → mean(sentiment), count, top 5 헤드라인 sample
        - 빈 결과는 동일 schema 빈 DataFrame

    AIContext:
        analyzeNarrative (Phase C) 가 직접 호출. scenarios.runScenario 의
        narrative_signal 계산 입력 SSOT.

    Guide:
        7~30 일 lookback 이 narrative 의 의미 단위. 90 일 이상은 regime shift 평균화로
        signal 약해짐.

    When:
        - dartlab.macro("내러티브") 본체 (Phase C)
        - 시나리오 baseline narrative 계산
        - 사용자 직접 분석

    How:
        loadNewsArchive → scoreNewsBatch → clusterNewsTopics → group_by(date, topic_id)
        → agg(mean sentiment, count, std, top 5 sample).

    Args:
        start: 시작일.
        end: 종료일.
        market: "KR" | "US".
        asof: PIT 시점. None 이면 필터 0.
        sentimentModel: "auto" (최강 자동) | "lm_dict" (강제 사전).
        nrTopics: BERTopic 강제 topic 수.

    Returns:
        pl.DataFrame — (date, topic_id, topic_label, sentiment_mean, sentiment_std,
        volume, headlines_sample). date asc + topic_id asc 정렬.

    Raises:
        없음 — 빈 결과는 동일 schema.

    Example::

        pulse = buildNarrativePulse("2026-04-28","2026-05-28","KR")
        # → (date, topic_id, topic_label, sentiment_mean, sentiment_std, volume, headlines_sample)

    Requires:
        Phase A archive (newsHeadlines.loadNewsArchive). 모델 가용 시 optional 그룹 narrative.

    See Also:
        ``dartlab.gather.bulkData.newsHeadlines.loadNewsArchive``: archive 입력.
        ``dartlab.quant.text.newsSentiment.scoreNewsBatch``: sentiment 위임.
        ``dartlab.quant.text.newsTopic.clusterNewsTopics``: topic 위임.
        ``dartlab.macro.narrative.narrative.analyzeNarrative``: Phase C caller.
    """
    from dartlab.gather.bulkData.newsHeadlines import loadNewsArchive

    from .newsSentiment import scoreNewsBatch
    from .newsTopic import clusterNewsTopics

    df = loadNewsArchive(start, end, market, asof=asof)
    if df.is_empty():
        return pl.DataFrame(
            schema={
                "date": pl.Date,
                "topic_id": pl.Int32,
                "topic_label": pl.Utf8,
                "sentiment_mean": pl.Float64,
                "sentiment_std": pl.Float64,
                "volume": pl.UInt32,
                "headlines_sample": pl.List(pl.Utf8),
            }
        )

    df = scoreNewsBatch(df, market=market, model=sentimentModel)
    df = clusterNewsTopics(df, market=market, nrTopics=nrTopics)

    pulse = (
        df.group_by(["date", "topic_id"])
        .agg(
            pl.col("topic_label").first(),
            pl.col("sentiment_score").mean().alias("sentiment_mean"),
            pl.col("sentiment_score").std().fill_null(0.0).alias("sentiment_std"),
            pl.len().alias("volume").cast(pl.UInt32),
            pl.col("title").head(5).alias("headlines_sample"),
        )
        .sort(["date", "topic_id"])
    )
    return pulse
