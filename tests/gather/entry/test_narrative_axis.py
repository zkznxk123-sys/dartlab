"""L1 — gather("narrative", ...) axis 5 sub-mode 단위 테스트.

dartlab.gather() 의 11 번째 axis. Phase A/B/C/D archive 통합 진입점.

분기:
    - target=None/"raw"  → loadNewsArchive (raw archive)
    - target="pulse"     → buildNarrativePulse (date × topic 격자)
    - target="score"     → analyzeNarrative (12 번째 macro 축 dict → 1행 DataFrame)
    - target="topics"    → buildNarrativePulse + group_by + top N
    - target=6자리 코드  → codeToName resolve → title contains
    - target=keyword     → title contains literal

NOTE: dartlab.gather 는 GatherEntry() callable 로 shadow 됨 — 서브모듈은 importlib
으로 우회 import.
"""

from __future__ import annotations

import importlib
from datetime import date

import polars as pl
import pytest

pytestmark = pytest.mark.unit


def test_axis_registry_has_narrative() -> None:
    """AXIS_REGISTRY 에 narrative entry + targetRequired=False."""
    dispatch = importlib.import_module("dartlab.gather.entry.dispatch")
    assert "narrative" in dispatch.AXIS_REGISTRY
    entry = dispatch.AXIS_REGISTRY["narrative"]
    assert entry.targetRequired is False
    assert entry.label == "뉴스 내러티브 archive"


def test_axis_aliases_korean() -> None:
    """한글 alias 4 종 → narrative."""
    dispatch = importlib.import_module("dartlab.gather.entry.dispatch")
    assert dispatch.AXIS_ALIASES["내러티브"] == "narrative"
    assert dispatch._resolveAxis("내러티브") == "narrative"
    assert dispatch._resolveAxis("뉴스내러티브") == "narrative"
    assert dispatch._resolveAxis("뉴스심리") == "narrative"
    assert dispatch._resolveAxis("헤드라인") == "narrative"


def test_dispatch_table_has_narrative() -> None:
    """_AXIS_DISPATCH 에 narrative → handleNarrative 등록."""
    handlers = importlib.import_module("dartlab.gather.entry.handlers")
    main = importlib.import_module("dartlab.gather.entry.main")
    assert main._AXIS_DISPATCH["narrative"] is handlers.handleNarrative


def test_handle_narrative_raw_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    """target=None → loadNewsArchive raw 위임."""
    handlers = importlib.import_module("dartlab.gather.entry.handlers")
    news_mod = importlib.import_module("dartlab.gather.bulkData.newsHeadlines")

    captured: dict = {}

    def fake_load(start, end, market, *, asof=None):
        captured["start"] = start
        captured["end"] = end
        captured["market"] = market
        captured["asof"] = asof
        return pl.DataFrame({"date": [date(2026, 5, 27)], "title": ["foo"]})

    monkeypatch.setattr(news_mod, "loadNewsArchive", fake_load)

    df = handlers.handleNarrative(None, None, market="KR", start="2026-05-01", end="2026-05-27", marketExplicit=False)
    assert df.height == 1
    assert captured["start"] == "2026-05-01"
    assert captured["market"] == "KR"


def test_handle_narrative_days_default(monkeypatch: pytest.MonkeyPatch) -> None:
    """start/end 미명시 + days=7 → today-7~today."""
    handlers = importlib.import_module("dartlab.gather.entry.handlers")
    news_mod = importlib.import_module("dartlab.gather.bulkData.newsHeadlines")

    captured: dict = {}

    def fake_load(start, end, market, *, asof=None):
        captured["start"] = start
        captured["end"] = end
        return pl.DataFrame()

    monkeypatch.setattr(news_mod, "loadNewsArchive", fake_load)

    handlers.handleNarrative(None, None, market="KR", start=None, end=None, marketExplicit=False, days=7)
    assert isinstance(captured["start"], str) and len(captured["start"]) == 10
    assert isinstance(captured["end"], str) and len(captured["end"]) == 10
    delta = date.fromisoformat(captured["end"]) - date.fromisoformat(captured["start"])
    assert delta.days == 7


def test_handle_narrative_pulse(monkeypatch: pytest.MonkeyPatch) -> None:
    """target='pulse' → buildNarrativePulse 위임."""
    handlers = importlib.import_module("dartlab.gather.entry.handlers")
    pulse_mod = importlib.import_module("dartlab.quant.text.narrativePulse")

    def fake_pulse(start, end, market, *, asof=None, sentimentModel="auto", nrTopics=30):
        return pl.DataFrame({"date": [date(2026, 5, 1)], "topic_id": [0], "volume": [10]})

    monkeypatch.setattr(pulse_mod, "buildNarrativePulse", fake_pulse)

    df = handlers.handleNarrative(
        None, "pulse", market="KR", start="2026-04-01", end="2026-05-01", marketExplicit=False
    )
    assert df.height == 1
    assert "topic_id" in df.columns


def test_handle_narrative_score(monkeypatch: pytest.MonkeyPatch) -> None:
    """target='score' → analyzeNarrative 결과 1행 DataFrame 변환."""
    handlers = importlib.import_module("dartlab.gather.entry.handlers")
    narr_mod = importlib.import_module("dartlab.macro.narrative.narrative")

    def fake_score(market="KR", asOf=None, *, lookbackDays=30, overrides=None, sentimentModel="auto"):
        return {
            "market": market,
            "asOf": asOf,
            "lookbackDays": lookbackDays,
            "score": -1.2,
            "label": "비관",
            "topicPulse": [],
            "regimeShift": {"score_7d": 0.0, "score_30d": 0.0, "delta": 0.0},
            "similarPastPeriods": [],
            "contributions": {},
        }

    monkeypatch.setattr(narr_mod, "analyzeNarrative", fake_score)

    df = handlers.handleNarrative(None, "score", market="KR", start=None, end=None, marketExplicit=False, days=30)
    assert df.height == 1
    assert df["score"][0] == -1.2
    assert df["label"][0] == "비관"


def test_handle_narrative_keyword_filter(monkeypatch: pytest.MonkeyPatch) -> None:
    """target=keyword → title contains literal 필터."""
    handlers = importlib.import_module("dartlab.gather.entry.handlers")
    news_mod = importlib.import_module("dartlab.gather.bulkData.newsHeadlines")

    def fake_load(start, end, market, *, asof=None):
        return pl.DataFrame(
            {
                "date": [date(2026, 5, 1), date(2026, 5, 2), date(2026, 5, 3)],
                "title": ["삼성전자 신제품 출시", "현대차 SUV 신차", "삼성전자 실적 발표"],
            }
        )

    monkeypatch.setattr(news_mod, "loadNewsArchive", fake_load)

    df = handlers.handleNarrative(
        None, "삼성전자", market="KR", start="2026-05-01", end="2026-05-03", marketExplicit=False
    )
    assert df.height == 2


def test_handle_narrative_stockcode_resolve(monkeypatch: pytest.MonkeyPatch) -> None:
    """target=6자리 → codeToName resolve 후 keyword filter."""
    handlers = importlib.import_module("dartlab.gather.entry.handlers")
    news_mod = importlib.import_module("dartlab.gather.bulkData.newsHeadlines")
    listing_mod = importlib.import_module("dartlab.gather.krx.listing.registry")

    def fake_load(start, end, market, *, asof=None):
        return pl.DataFrame(
            {
                "date": [date(2026, 5, 1), date(2026, 5, 2)],
                "title": ["삼성전자 신제품", "LG화학 배터리"],
            }
        )

    def fake_codeToName(code):
        return "삼성전자" if code == "005930" else None

    monkeypatch.setattr(news_mod, "loadNewsArchive", fake_load)
    monkeypatch.setattr(listing_mod, "codeToName", fake_codeToName)

    df = handlers.handleNarrative(
        None, "005930", market="KR", start="2026-05-01", end="2026-05-02", marketExplicit=False
    )
    assert df.height == 1
    assert "삼성전자" in df["title"][0]


def test_gather_entry_narrative_smoke(monkeypatch: pytest.MonkeyPatch) -> None:
    """GatherEntry.__call__ → narrative axis end-to-end."""
    main = importlib.import_module("dartlab.gather.entry.main")
    news_mod = importlib.import_module("dartlab.gather.bulkData.newsHeadlines")

    monkeypatch.setattr(
        news_mod,
        "loadNewsArchive",
        lambda start, end, market, *, asof=None: pl.DataFrame({"date": [date(2026, 5, 1)], "title": ["x"]}),
    )

    entry = main.GatherEntry()
    df = entry("narrative", market="KR", start="2026-05-01", end="2026-05-01")
    assert df.height == 1
