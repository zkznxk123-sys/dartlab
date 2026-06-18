"""횡단 테마 — 공개 호출계약(엔진 verb)으로 검증.

공개 진입: ``Industry().theme(themeId)`` (테마 스코프) · ``Company(code).themes()`` (회사 스코프).
themes.py 백엔드 함수(``_``)는 private — 직접 호출 대상 아님. 순수 atom 단위테스트만 private 인용.
"""

from __future__ import annotations

import pytest

from dartlab.industry.themes import _loadThemes, _matchTheme, _themeExposure


def test_load_themes_flat_cross_industry():
    """themes.json 로드 — flat cross-industry, secondaryBattery 등급가능."""
    themes = _loadThemes()
    assert "secondaryBattery" in themes
    bat = themes["secondaryBattery"]
    assert bat.name == "2차전지/배터리"
    assert "양극활물질" in bat.keywords  # E8 held-out 갭 수정 박제
    assert bat.segmentKeywords  # 등급 가능
    assert not themes["robotics"].segmentKeywords  # 등급 미정의(정직)


def test_match_theme_negative_guard():
    """_matchTheme — substring 매칭 + negative 제거(거짓양성 가드)."""
    bat = _loadThemes()["secondaryBattery"]
    assert "2차전지" in _matchTheme(bat, "2차전지, 양극재 제조")
    assert "양극활물질" in _matchTheme(bat, "양극활물질")  # 에코프로비엠 케이스
    assert _matchTheme(bat, "건전지 제조") == []  # negative 제거 → 비멤버
    assert _matchTheme(bat, "") == []


def test_theme_exposure_unregistered():
    """미등록 테마 = None. (인자 관례: themeId 먼저, code 다음)"""
    assert _themeExposure("nonexistentTheme", "051910") is None


@pytest.mark.requires_data
def test_theme_exposure_branches():
    """노출% 정직 분기 — graded / pure_play / no_segment_keywords. 허울 정정 가드(None≠100%)."""
    lg = _themeExposure("secondaryBattery", "051910")  # LG화학 희석
    assert lg["basis"] == "graded" and 40 < lg["exposurePct"] < 60
    eco = _themeExposure("secondaryBattery", "247540")  # 에코프로비엠 pure-play
    assert eco["exposurePct"] is None and eco["basis"] == "pure_play_candidate"
    rob = _themeExposure("robotics", "000660")  # segmentKeywords 미정의
    assert rob["exposurePct"] is None and rob["basis"] == "theme_no_segment_keywords"


@pytest.mark.requires_data
def test_theme_is_industry_engine_method():
    """theme 은 *industry 엔진의 메서드* (별도 엔진 아님) — Industry().theme() 단일 진입.

    테마→멤버(themeId), 종목→소속 테마(stockCode), 목록(무인자). edges/map 과 동일 industry 메서드.
    """
    from dartlab.industry import Industry

    ind = Industry()
    assert ind.theme().height == 3  # 무인자 = 목록
    members = ind.theme("secondaryBattery")  # 테마 스코프
    assert members.height > 50 and "051910" in members["종목코드"].to_list()
    dossier = ind.theme(stockCode="051910")  # 종목 스코프 (LG화학)
    bat = dossier.filter(dossier["themeId"] == "secondaryBattery").to_dicts()[0]
    assert bat["근거"] and 40 < bat["노출%"] < 60 and bat["등급근거"] == "graded"


def test_themes_not_a_separate_engine_or_tool():
    """themes 는 엔진 아님 — Company.themes accessor·ThemeExposure 도구·Company.themes apiRef 모두 없음."""
    from dartlab.ai.tools import registry as rg
    from dartlab.company import Company
    from dartlab.reference.capability import loadCapabilities

    assert not hasattr(Company("005930"), "themes")  # 회사급 엔진 accessor 아님
    assert "ThemeExposure" not in rg._TOOLS  # 별도 도구 아님
    assert "Company.themes" not in loadCapabilities()  # 회사급 apiRef 아님
