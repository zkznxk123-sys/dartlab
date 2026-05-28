"""L5 — scanNarrativeRegime 단위 테스트 (Pettitt change-point + regime label)."""

from __future__ import annotations

import importlib
from datetime import date, timedelta

import numpy as np
import polars as pl
import pytest

pytestmark = pytest.mark.unit


def _mk_pulse(dates: list[date], scores: list[float], topics: list[str] | None = None) -> pl.DataFrame:
    """간이 pulse DataFrame (date × topic × sentiment_mean × volume)."""
    if topics is None:
        topics = ["topic_a"] * len(dates)
    return pl.DataFrame(
        {
            "date": dates,
            "topic_id": list(range(len(dates))),
            "topic_label": topics,
            "sentiment_mean": scores,
            "sentiment_std": [0.1] * len(dates),
            "volume": [10] * len(dates),
        }
    )


def test_smoke_import() -> None:
    importlib.import_module("dartlab.scan.narrativeRegime")


def test_regime_label_positive() -> None:
    """daily score 모두 +0.4 → 긍정 label."""
    nr = importlib.import_module("dartlab.scan.narrativeRegime")
    n = 30
    dates = [date(2026, 4, 1) + timedelta(days=i) for i in range(n)]
    scores = [0.4] * n
    pulse = _mk_pulse(dates, scores)

    r = nr.scanNarrativeRegime(
        market="KR",
        asOf=date(2026, 4, 30),
        lookbackDays=30,
        pulseLoader=lambda s, e, m: pulse,
    )
    assert r["regime_label"] == "긍정"
    assert r["regime_score"] > 0.3
    assert r["n_days"] == n


def test_pettitt_detects_shift() -> None:
    """전반 50 일 = -0.3, 후반 50 일 = +0.3 → Pettitt significant shift."""
    nr = importlib.import_module("dartlab.scan.narrativeRegime")
    n_half = 50
    dates = [date(2026, 1, 1) + timedelta(days=i) for i in range(n_half * 2)]
    scores = [-0.3] * n_half + [0.3] * n_half
    pulse = _mk_pulse(dates, scores)

    r = nr.scanNarrativeRegime(
        market="KR",
        asOf=date(2026, 4, 10),
        lookbackDays=100,
        pulseLoader=lambda s, e, m: pulse,
    )
    assert r["regime_shift_significant"] is True
    assert r["pettitt_pvalue"] < 0.05
    # shift 일자가 중간 근처 (idx 49 ~ 50 부근)
    assert r["regime_shift_date"] is not None


def test_no_shift_when_flat() -> None:
    """평평한 시계열 → shift 비유의."""
    nr = importlib.import_module("dartlab.scan.narrativeRegime")
    n = 60
    dates = [date(2026, 2, 1) + timedelta(days=i) for i in range(n)]
    scores = [0.0] * n
    pulse = _mk_pulse(dates, scores)

    r = nr.scanNarrativeRegime(
        market="KR",
        asOf=date(2026, 4, 1),
        lookbackDays=60,
        pulseLoader=lambda s, e, m: pulse,
    )
    assert r["regime_shift_significant"] is False
    assert r["regime_label"] == "혼조"


def test_topics_hot_ordering() -> None:
    """volume_total desc 정렬 + topTopics 컷."""
    nr = importlib.import_module("dartlab.scan.narrativeRegime")
    # 3 topic, volume 다름
    dates = [date(2026, 3, 1) + timedelta(days=i) for i in range(15)]
    rng = np.random.default_rng(0)
    topics = ["반도체"] * 5 + ["배터리"] * 5 + ["바이오"] * 5  # volume sum 동일 — 정렬 안정성 확인
    pulse = pl.DataFrame(
        {
            "date": dates,
            "topic_id": list(range(15)),
            "topic_label": topics,
            "sentiment_mean": rng.normal(0, 0.1, 15).tolist(),
            "volume": [20, 20, 20, 20, 20, 10, 10, 10, 10, 10, 30, 30, 30, 30, 30],
        }
    )

    r = nr.scanNarrativeRegime(
        market="KR",
        asOf=date(2026, 3, 15),
        lookbackDays=15,
        topTopics=3,
        pulseLoader=lambda s, e, m: pulse,
    )
    assert len(r["topics_hot"]) == 3
    # 바이오 = 150 > 반도체 = 100 > 배터리 = 50
    assert r["topics_hot"][0]["topic_label"] == "바이오"
    assert r["topics_hot"][-1]["topic_label"] == "배터리"


def test_empty_pulse_graceful() -> None:
    """빈 pulse → 중립 label + n_days 0."""
    nr = importlib.import_module("dartlab.scan.narrativeRegime")
    r = nr.scanNarrativeRegime(
        market="KR",
        asOf=date(2026, 5, 1),
        lookbackDays=30,
        pulseLoader=lambda s, e, m: pl.DataFrame(),
    )
    assert r["regime_label"] == "중립"
    assert r["n_days"] == 0
    assert r["regime_shift_significant"] is False
