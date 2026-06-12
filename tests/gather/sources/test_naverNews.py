"""네이버 뉴스 소스 (naverNews) 단위 테스트.

market 가드 · 무키 graceful · <b>태그/엔티티 정리 · 응답 파싱 · archive canonical.
네트워크 미사용 (getKey/_fetchAsync stub + _parseItems 직접).
"""

from __future__ import annotations

import asyncio

import pytest

from dartlab.gather.sources import naverNews
from dartlab.gather.sources.naverNews import _clean, _parseItems
from dartlab.gather.sources.newsSchema import NEWS_ARCHIVE_SCHEMA
from dartlab.gather.types import NewsItem

pytestmark = pytest.mark.unit


def test_clean_strips_tags_and_entities() -> None:
    """<b> 등 태그 제거 + HTML 엔티티 unescape + strip."""
    assert _clean("<b>삼성</b>전자 &amp; SK") == "삼성전자 & SK"
    assert _clean(None) == ""
    assert _clean("  plain  ") == "plain"


def test_fetch_non_kr_market_empty() -> None:
    """market != KR → 빈 리스트 (네이버=국내 전용, 네트워크 미접근)."""
    assert asyncio.run(naverNews._fetchAsync("query", market="US")) == []


def test_fetch_missing_credentials_graceful(monkeypatch: pytest.MonkeyPatch) -> None:
    """자격증명 미설정 → 빈 리스트 (네트워크 미접근)."""
    monkeypatch.setattr(naverNews, "getKey", lambda *a, **k: None)
    assert asyncio.run(naverNews._fetchAsync("query", market="KR")) == []


def test_parse_items() -> None:
    """검색 응답 JSON → NewsItem (url=originallink, source=도메인, description=스니펫)."""
    data = {
        "items": [
            {
                "title": "<b>삼성</b>전자 &amp; SK",
                "description": "<b>스니펫</b> 내용",
                "originallink": "https://www.yna.co.kr/view/1",
                "link": "https://n.news.naver.com/x",
                "pubDate": "Mon, 08 Jun 2026 12:34:56 +0900",
            },
            {"title": "링크없음", "description": "d", "pubDate": "Mon, 08 Jun 2026 00:00:00 +0900"},
        ]
    }
    items = _parseItems(data)
    assert len(items) == 1  # 링크 없는 항목 skip
    it = items[0]
    assert it.title == "삼성전자 & SK"
    assert it.description == "스니펫 내용"
    assert it.url == "https://www.yna.co.kr/view/1"  # originallink 우선
    assert it.source == "yna.co.kr"  # www. 제거
    assert it.date == "2026-06-08"


def test_archive_canonical_columns(monkeypatch: pytest.MonkeyPatch) -> None:
    """fetchHeadlinesForArchive → canonical 17컬럼 + description 채움."""
    item = NewsItem(
        date="2026-06-08",
        title="t",
        source="yna.co.kr",
        url="https://x/a",
        description="snippet",
    )

    async def _stub(query, *, market="KR", **kw):
        return [item]

    monkeypatch.setattr(naverNews, "_fetchAsync", _stub)
    df = naverNews.fetchHeadlinesForArchive(["삼성전자"], market="KR", days=3650)
    assert set(df.columns) == set(NEWS_ARCHIVE_SCHEMA.keys())
    assert df.height == 1
    assert df["description"][0] == "snippet"
    assert df["market"][0] == "KR"


def test_archive_non_kr_empty_canonical() -> None:
    """market != KR → 빈 canonical DataFrame (17컬럼)."""
    df = naverNews.fetchHeadlinesForArchive(["q"], market="US")
    assert df.height == 0
    assert set(df.columns) == set(NEWS_ARCHIVE_SCHEMA.keys())
