"""L5 narrativeRegime — 시장 narrative regime + Pettitt change-point.

buildNarrativePulse (Phase B) 결과의 daily sentiment_mean 시계열에 Pettitt
non-parametric change-point test 적용. regime shift 일자 자동 검출 + hot
topics top N + regime label (긍정/부정/혼조).

진입점:
    scanNarrativeRegime(market, *, lookbackDays, changePointThreshold,
                        pulseLoader=None)
    → dict — regime_label/regime_score/regime_shift_date/topics_hot (list)/
             pettitt_U/pettitt_pvalue

Pettitt 1979 — Mann-Whitney 형태 두 부분군 평균 차이 검정. p<0.05 = 유의 shift.

메모리 가드:
    @withMemoryBudget(800) — 시장 90 일 grid <800MB.
"""

from __future__ import annotations

import logging
from datetime import date as _date
from datetime import datetime, timedelta
from typing import Callable

import numpy as np
import polars as pl

from dartlab.core.memory import withMemoryBudget

log = logging.getLogger(__name__)


def _pettittTest(x: np.ndarray) -> tuple[int, float, float]:
    """Pettitt change-point test (one-sided U_k statistic).

    Args:
        x: 시계열 1D array (NaN 없음).

    Returns:
        (k, U_k, p_value) — k = shift index (0-based), U_k = test statistic,
        p_value = Mann-Whitney approximation. n < 10 이면 (-1, 0.0, 1.0).
    """
    n = len(x)
    if n < 10:
        return -1, 0.0, 1.0
    # U_k = sum over i<=k, j>k of sign(x_i - x_j)
    Uk = np.zeros(n)
    for k in range(n):
        # rank-based pettitt — sum of sign differences
        head = x[: k + 1]
        tail = x[k + 1 :]
        if tail.size == 0:
            continue
        # broadcast
        diff = head[:, None] - tail[None, :]
        Uk[k] = float(np.sign(diff).sum())
    K = int(np.argmax(np.abs(Uk)))
    Ustat = float(np.abs(Uk[K]))
    # Pettitt p-value approximation (Pettitt 1979)
    p = 2.0 * np.exp(-6.0 * Ustat * Ustat / (n * n * n + n * n))
    p = float(min(1.0, p))
    return K, Ustat, p


def _scoreToLabel(score: float) -> str:
    """평균 sentiment_mean 점수 → 한글 regime label."""
    if score >= 0.15:
        return "긍정"
    if score >= 0.05:
        return "약긍정"
    if score <= -0.15:
        return "부정"
    if score <= -0.05:
        return "약부정"
    return "혼조"


@withMemoryBudget(800)
def scanNarrativeRegime(
    market: str = "KR",
    asOf: str | _date | datetime | None = None,
    *,
    lookbackDays: int = 90,
    changePointThreshold: float = 0.05,
    topTopics: int = 5,
    pulseLoader: Callable[[str, str, str], pl.DataFrame] | None = None,
) -> dict:
    """시장 narrative regime 분석 + Pettitt change-point.

    Capabilities:
        - lookback 일 buildNarrativePulse 로드 → daily sentiment_mean 평균
        - Pettitt change-point → regime shift 일자 + p-value
        - topic group_by → hot topics top N (volume + sentiment_mean)
        - regime_label = score 평균 분위 (긍정/약긍정/혼조/약부정/부정)

    Args:
        market: "KR" | "US".
        asOf: 기준일 (None 이면 today).
        lookbackDays: 분석 기간.
        changePointThreshold: Pettitt p-value 유의 임계 (기본 0.05).
        topTopics: hot topics 상한.
        pulseLoader: DI mock (callable(start, end, market) → pulse DataFrame).

    Returns:
        dict — market/asOf/lookbackDays/regime_label/regime_score/
        regime_shift_date/regime_shift_significant/topics_hot (list)/
        pettitt_U/pettitt_pvalue/n_days.
    """
    asOfDate = (
        _date.today()
        if asOf is None
        else (
            asOf if isinstance(asOf, _date) and not isinstance(asOf, datetime) else _date.fromisoformat(str(asOf)[:10])
        )
    )
    startDate = asOfDate - timedelta(days=lookbackDays)

    if pulseLoader is None:
        return {
            "market": market,
            "asOf": asOfDate.isoformat(),
            "lookbackDays": lookbackDays,
            "regime_label": "중립",
            "regime_score": 0.0,
            "regime_shift_date": None,
            "regime_shift_significant": False,
            "topics_hot": [],
            "pettitt_U": 0.0,
            "pettitt_pvalue": 1.0,
            "n_days": 0,
            "available": False,
            "reason": "pulseLoaderRequired",
        }

    pulse = pulseLoader(startDate.isoformat(), asOfDate.isoformat(), market)

    if pulse.is_empty() or "date" not in pulse.columns or "sentiment_mean" not in pulse.columns:
        return {
            "market": market,
            "asOf": asOfDate.isoformat(),
            "lookbackDays": lookbackDays,
            "regime_label": "중립",
            "regime_score": 0.0,
            "regime_shift_date": None,
            "regime_shift_significant": False,
            "topics_hot": [],
            "pettitt_U": 0.0,
            "pettitt_pvalue": 1.0,
            "n_days": 0,
        }

    # daily aggregate (volume-weighted mean)
    if "volume" in pulse.columns:
        daily = (
            pulse.group_by("date")
            .agg(
                ((pl.col("sentiment_mean") * pl.col("volume")).sum() / pl.col("volume").sum().clip(1)).alias("score"),
                pl.col("volume").sum().alias("volume_total"),
            )
            .sort("date")
        )
    else:
        daily = pulse.group_by("date").agg(pl.col("sentiment_mean").mean().alias("score")).sort("date")

    scores = daily["score"].to_numpy().astype(np.float64)
    scores = scores[~np.isnan(scores)]
    if scores.size == 0:
        return {
            "market": market,
            "asOf": asOfDate.isoformat(),
            "lookbackDays": lookbackDays,
            "regime_label": "중립",
            "regime_score": 0.0,
            "regime_shift_date": None,
            "regime_shift_significant": False,
            "topics_hot": [],
            "pettitt_U": 0.0,
            "pettitt_pvalue": 1.0,
            "n_days": int(daily.height),
        }

    meanScore = float(np.mean(scores))
    k, Ustat, pVal = _pettittTest(scores)
    dates = daily["date"].to_list()
    shiftDate = (
        dates[k].isoformat()
        if 0 <= k < len(dates) and hasattr(dates[k], "isoformat")
        else (str(dates[k]) if 0 <= k < len(dates) else None)
    )

    # hot topics
    topics_hot: list[dict] = []
    topic_col = (
        "topic_label" if "topic_label" in pulse.columns else ("topic_id" if "topic_id" in pulse.columns else None)
    )
    if topic_col:
        if "volume" in pulse.columns:
            agg = (
                pulse.group_by(topic_col)
                .agg(
                    pl.col("volume").sum().alias("volume_total"),
                    pl.col("sentiment_mean").mean().alias("sentiment_mean"),
                )
                .sort("volume_total", descending=True)
                .head(topTopics)
            )
        else:
            agg = (
                pulse.group_by(topic_col)
                .agg(
                    pl.len().alias("volume_total"),
                    pl.col("sentiment_mean").mean().alias("sentiment_mean"),
                )
                .sort("volume_total", descending=True)
                .head(topTopics)
            )
        topics_hot = agg.to_dicts()

    return {
        "market": market,
        "asOf": asOfDate.isoformat(),
        "lookbackDays": lookbackDays,
        "regime_label": _scoreToLabel(meanScore),
        "regime_score": round(meanScore, 4),
        "regime_shift_date": shiftDate,
        "regime_shift_significant": bool(pVal < changePointThreshold),
        "topics_hot": topics_hot,
        "pettitt_U": round(Ustat, 2),
        "pettitt_pvalue": round(pVal, 4),
        "n_days": int(scores.size),
    }
