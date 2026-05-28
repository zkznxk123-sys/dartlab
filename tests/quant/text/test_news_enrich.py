"""Phase B — news sentiment + topic + narrativePulse 단위 테스트.

LM-dict fallback 단독 동작 (의존성 0) + schema 회귀 가드 + pulse aggregate.
"""

from __future__ import annotations

from datetime import date, datetime, timezone

import polars as pl
import pytest

pytestmark = pytest.mark.unit


@pytest.fixture
def headlinesDf() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "date": [date(2026, 5, 27), date(2026, 5, 28), date(2026, 5, 28)],
            "title": ["반도체 호황 가속화 매출 증가", "기업 부도 손실 적자 채무불이행", "코스피 등락 중립"],
            "source": ["s1", "s2", "s3"],
            "url": ["u1", "u2", "u3"],
            "market": ["KR", "KR", "KR"],
            "query": ["반도체", "금리", "코스피"],
            "captured_at": [datetime(2026, 5, 28, 0, 0, tzinfo=timezone.utc)] * 3,
        }
    )


def test_lm_dict_fallback_no_model(headlinesDf: pl.DataFrame) -> None:
    """transformers 미설치 시 LM-dict fallback 자동 — 3 sentiment 컬럼 부착."""
    from dartlab.quant.text.newsSentiment import scoreNewsBatch

    out = scoreNewsBatch(headlinesDf, market="KR", model="lm_dict")
    assert out.height == 3
    assert "sentiment_score" in out.columns
    assert "sentiment_label" in out.columns
    assert "model_version" in out.columns
    assert out["model_version"][0] == "lm_dict_v1"
    # "매출 증가" → POSITIVE_KR hit, "손실" → NEGATIVE_KR hit
    scores = out["sentiment_score"].to_list()
    assert scores[0] > 0  # 반도체 호황
    assert scores[1] < 0  # 금리 우려 손실


def test_lm_dict_empty_df_schema() -> None:
    """빈 df → 3 컬럼 (null) 부착 + schema 유지."""
    from dartlab.quant.text.newsSentiment import scoreNewsBatch

    empty = pl.DataFrame(schema={"title": pl.Utf8, "url": pl.Utf8, "market": pl.Utf8, "query": pl.Utf8})
    out = scoreNewsBatch(empty, market="KR")
    assert "sentiment_score" in out.columns
    assert out.height == 0


def test_topic_clustering_fallback_proxy(headlinesDf: pl.DataFrame) -> None:
    """BERTopic 미설치 시 query proxy — 3 query 분포 → 3 topic_id unique."""
    from dartlab.quant.text.newsTopic import clusterNewsTopics

    out = clusterNewsTopics(headlinesDf, market="KR")
    assert "topic_id" in out.columns
    assert "topic_label" in out.columns
    # query 가 각각 다르면 topic_id 도 다름 (proxy 분기)
    topicIds = out["topic_id"].to_list()
    assert len(set(topicIds)) == 3


def test_narrative_pulse_aggregate(monkeypatch: pytest.MonkeyPatch, headlinesDf: pl.DataFrame) -> None:
    """buildNarrativePulse — (date × topic_id) 격자 + sentiment_mean + volume."""
    from dartlab.quant.text import narrativePulse

    monkeypatch.setattr(narrativePulse, "loadNewsArchive", lambda *a, **kw: headlinesDf, raising=False)
    # narrativePulse 가 from dartlab.gather.bulkData.newsHeadlines import loadNewsArchive — module-level
    # patch 가 안 잡혀서, 함수가 부른 후 가져오는 path 가 같은 모듈에 있어야 함.
    # 위 monkeypatch 가 효과 0 일 수 있으므로 직접 patch 도 진행:
    from dartlab.gather.bulkData import newsHeadlines as nh

    monkeypatch.setattr(nh, "loadNewsArchive", lambda *a, **kw: headlinesDf)

    pulse = narrativePulse.buildNarrativePulse("2026-05-27", "2026-05-28", "KR", sentimentModel="lm_dict")
    assert pulse.height >= 1
    assert set(pulse.columns) == {
        "date",
        "topic_id",
        "topic_label",
        "sentiment_mean",
        "sentiment_std",
        "volume",
        "headlines_sample",
    }
    # volume 합 = 3 (전체 row)
    assert pulse["volume"].sum() == 3


def test_narrative_pulse_empty_input(monkeypatch: pytest.MonkeyPatch) -> None:
    """archive 0 → 빈 pulse DataFrame + 7 컬럼 schema."""
    from dartlab.gather.bulkData import newsHeadlines as nh
    from dartlab.quant.text import narrativePulse

    monkeypatch.setattr(
        nh,
        "loadNewsArchive",
        lambda *a, **kw: pl.DataFrame(
            schema={
                "date": pl.Date,
                "title": pl.Utf8,
                "source": pl.Utf8,
                "url": pl.Utf8,
                "market": pl.Utf8,
                "query": pl.Utf8,
            }
        ),
    )

    pulse = narrativePulse.buildNarrativePulse("2026-05-01", "2026-05-02", "KR")
    assert pulse.height == 0
    assert "sentiment_mean" in pulse.columns
