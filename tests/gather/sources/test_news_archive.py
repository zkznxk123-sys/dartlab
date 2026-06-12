"""Phase A — news archive 진입점 (fetchHeadlinesForArchive) 단위 테스트.

dedup + captured_at + multi-query fan-out + empty 결과 schema 회귀 가드.
"""

from __future__ import annotations

import polars as pl
import pytest

from dartlab.gather.sources import news as newsMod
from dartlab.gather.sources.newsSchema import NEWS_ARCHIVE_SCHEMA
from dartlab.gather.types import NewsItem

pytestmark = pytest.mark.unit


def test_archive_schema_columns() -> None:
    """빈 쿼리 → 빈 DataFrame canonical 17 컬럼 schema 유지."""
    df = newsMod.fetchHeadlinesForArchive([])
    assert df.height == 0
    assert set(df.columns) == set(NEWS_ARCHIVE_SCHEMA.keys())
    assert "description" in df.columns  # 신규 canonical 컬럼


def test_archive_dedup_by_url(monkeypatch: pytest.MonkeyPatch) -> None:
    """동일 url 이 다른 query 결과에 중복 등장 → 1 행만 유지 (첫 query)."""

    shared = NewsItem(date="2026-05-28", title="t1", source="s1", url="https://x.com/a")
    other = NewsItem(date="2026-05-28", title="t2", source="s2", url="https://x.com/b")

    calls: list[str] = []

    async def _stub(query: str, *, market: str = "KR", days: int = 30, client=None):
        calls.append(query)
        return [shared, other] if query == "q1" else [shared]

    monkeypatch.setattr(newsMod, "_fetchAsync", _stub)
    df = newsMod.fetchHeadlinesForArchive(["q1", "q2"], market="KR", days=1)

    assert df.height == 2
    urls = set(df["url"].to_list())
    assert urls == {"https://x.com/a", "https://x.com/b"}
    queries_for_shared = df.filter(pl.col("url") == "https://x.com/a")["query"].to_list()
    assert queries_for_shared == ["q1"]
    assert set(calls) == {"q1", "q2"}


def test_archive_captured_at_utc(monkeypatch: pytest.MonkeyPatch) -> None:
    """captured_at 컬럼은 UTC tz-aware datetime + 모든 row 동일."""
    item = NewsItem(date="2026-05-28", title="t", source="s", url="https://x.com/a")

    async def _stub(query: str, *, market: str = "KR", days: int = 30, client=None):
        return [item]

    monkeypatch.setattr(newsMod, "_fetchAsync", _stub)
    df = newsMod.fetchHeadlinesForArchive(["q1"], market="KR", days=1)
    assert df.height == 1
    capCol = df.schema["captured_at"]
    assert capCol.time_zone == "UTC"
    assert df["market"][0] == "KR"
    assert df["query"][0] == "q1"


def test_archive_market_upper(monkeypatch: pytest.MonkeyPatch) -> None:
    """market 인자 lowercase → DataFrame 컬럼 upper-case 정규화."""
    item = NewsItem(date="2026-05-28", title="t", source="s", url="https://x.com/a")

    async def _stub(query: str, *, market: str = "KR", days: int = 30, client=None):
        return [item]

    monkeypatch.setattr(newsMod, "_fetchAsync", _stub)
    df = newsMod.fetchHeadlinesForArchive(["q1"], market="us", days=1)
    assert df["market"][0] == "US"


def test_archive_skip_empty_url(monkeypatch: pytest.MonkeyPatch) -> None:
    """url 빈 NewsItem 은 dedup 전에 drop."""
    bad = NewsItem(date="2026-05-28", title="t", source="s", url="")
    good = NewsItem(date="2026-05-28", title="g", source="s", url="https://x.com/a")

    async def _stub(query: str, *, market: str = "KR", days: int = 30, client=None):
        return [bad, good]

    monkeypatch.setattr(newsMod, "_fetchAsync", _stub)
    df = newsMod.fetchHeadlinesForArchive(["q1"], market="KR", days=1)
    assert df.height == 1
    assert df["url"][0] == "https://x.com/a"
