"""newsSources 레지스트리 단위 + 뉴스 소스 대칭성 회귀 가드.

rss/gdelt/naver 가 fetch→archive→sync→load 대칭을 유지하는지 검증.
핵심 invariant: ① archive 출력 컬럼 통일 ② newsSources.dir == dataConfig.dir
③ private 소스 전용 repo 라우팅 ④ 미등록 id KeyError.
(coerceToCanonical 단위는 test_newsSchema.py.)
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


def test_archive_entrypoints_canonical_columns() -> None:
    """3 소스 archive 진입점 모두 canonical 17컬럼 (출력 데이터 계약 통일)."""
    from dartlab.gather.sources import gdelt, naverNews, news
    from dartlab.gather.sources.newsSchema import NEWS_ARCHIVE_SCHEMA

    expected = set(NEWS_ARCHIVE_SCHEMA.keys())
    assert set(news.fetchHeadlinesForArchive([]).columns) == expected
    assert set(naverNews.fetchHeadlinesForArchive([], market="KR").columns) == expected
    # gdelt 는 동일 canonical 스키마 객체를 import (네트워크 없이 계약 확인).
    assert gdelt.NEWS_ARCHIVE_SCHEMA is NEWS_ARCHIVE_SCHEMA


def test_registry_dir_matches_dataconfig() -> None:
    """newsSources.NewsSourceSpec.dir == dataConfig.DATA_RELEASES[hfCategory].dir (drift 차단)."""
    from dartlab.core.dataConfig import DATA_RELEASES
    from dartlab.gather.sources.newsSources import allNewsSources

    for s in allNewsSources():
        assert s.hfCategory in DATA_RELEASES, f"미등록 카테고리: {s.hfCategory}"
        assert s.dir == DATA_RELEASES[s.hfCategory]["dir"], (s.id, s.dir, DATA_RELEASES[s.hfCategory]["dir"])


def test_private_sources_route_to_private_repo() -> None:
    """private 소스(naver)는 전용 private repo + public=False, public 소스는 기본 repo."""
    from dartlab.core.dataConfig import DATA_RELEASES, HF_REPO, repoFor
    from dartlab.gather.sources.newsSources import allNewsSources

    for s in allNewsSources():
        cfg = DATA_RELEASES[s.hfCategory]
        if s.visibility == "private":
            assert cfg["public"] is False, s.id
            assert repoFor(s.hfCategory) != HF_REPO, s.id  # 전용 private repo
        else:
            assert cfg["public"] is True, s.id
            assert repoFor(s.hfCategory) == HF_REPO, s.id


def test_get_news_source_unknown_raises() -> None:
    """미등록 소스 id → KeyError (등록 목록 안내 포함)."""
    from dartlab.gather.sources.newsSources import getNewsSource

    assert getNewsSource("rss").id == "rss"
    with pytest.raises(KeyError, match="미등록"):
        getNewsSource("nope")
