"""뉴스 narrative pulse 시계열 빌더.

macro와 quant 텍스트 축이 함께 쓰는 Phase B pulse 계산을 L1.5 synth에 둔다.
"""

from __future__ import annotations

from datetime import date as _date

import polars as pl


def buildNarrativePulse(
    start: str | _date,
    end: str | _date,
    market: str = "KR",
    *,
    asof: str | _date | None = None,
    sentimentModel: str = "auto",
    nrTopics: int | None = 30,
) -> pl.DataFrame:
    """기간 [start..end] news를 일별 topic pulse 시계열로 집계한다."""
    from dartlab.gather.bulkData.newsHeadlines import loadNewsArchive
    from dartlab.synth.newsSentiment import scoreNewsBatch
    from dartlab.synth.newsTopic import clusterNewsTopics

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

    return (
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
