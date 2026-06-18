"""industry 횡단 테마 — 로드·태깅·매출노출 등급 테스트.

순수(데이터 불요): themes.json 로드·키워드 매칭·negative 가드.
requires_data: panel 주석 기반 노출% 등급 정직 분기(허울 정정 가드).
"""

from __future__ import annotations

import pytest

from dartlab.industry.themes import (
    listThemes,
    loadThemes,
    matchThemeText,
    themeRevenueExposure,
)


def test_load_themes_flat_cross_industry():
    """themes.json 로드 — flat cross-industry, secondaryBattery 등급가능."""
    themes = loadThemes()
    assert "secondaryBattery" in themes
    bat = themes["secondaryBattery"]
    assert bat.name == "2차전지/배터리"
    assert "양극활물질" in bat.keywords  # E8 held-out 갭 수정 박제
    assert bat.segmentKeywords  # 등급 가능
    # 등급 미정의 테마는 segmentKeywords 비어있음(정직 — 등급 미산출).
    assert not themes["robotics"].segmentKeywords


def test_list_themes_gradeable_flag():
    """listThemes — gradeable 플래그가 segmentKeywords 유무 반영."""
    by = {t["themeId"]: t for t in listThemes()}
    assert by["secondaryBattery"]["gradeable"] is True
    assert by["robotics"]["gradeable"] is False


def test_match_theme_text_negative_guard():
    """matchThemeText — substring 매칭 + negative 제거(거짓양성 가드)."""
    bat = loadThemes()["secondaryBattery"]
    assert "2차전지" in matchThemeText(bat, "2차전지, 양극재 제조")
    assert "양극활물질" in matchThemeText(bat, "양극활물질")  # 에코프로비엠 케이스
    assert matchThemeText(bat, "건전지 제조") == []  # negative 제거 → 비멤버
    assert matchThemeText(bat, "") == []


def test_theme_exposure_unregistered():
    """미등록 테마 = None."""
    assert themeRevenueExposure("051910", "nonexistentTheme") is None


@pytest.mark.requires_data
def test_theme_exposure_branches():
    """테마-인지 노출% 정직 분기 — graded / pure_play / no_segment_keywords. 허울 정정 가드."""
    # 희석 대형 → graded, 노출% 산출.
    lg = themeRevenueExposure("051910", "secondaryBattery")  # LG화학
    assert lg["basis"] == "graded"
    assert 40 < lg["exposurePct"] < 60  # LG에너지솔루션 부문 ~48%

    # pure-play 단일사업 → None(100% 등치 금지).
    eco = themeRevenueExposure("247540", "secondaryBattery")  # 에코프로비엠
    assert eco["exposurePct"] is None
    assert eco["basis"] == "pure_play_candidate"

    # segmentKeywords 미정의 테마 → None(등급 미산출).
    rob = themeRevenueExposure("000660", "robotics")
    assert rob["exposurePct"] is None
    assert rob["basis"] == "theme_no_segment_keywords"


@pytest.mark.requires_data
def test_theme_verb_members_and_grade():
    """Industry.theme verb — 목록·멤버 태깅·테마-인지 등급 컬럼."""
    from dartlab.industry import Industry

    ind = Industry()
    assert ind.theme().height == 3  # 시드 3테마
    members = ind.theme("secondaryBattery")
    assert members.height > 50
    assert "051910" in members["종목코드"].to_list()  # LG화학
    assert set(members.columns) >= {"종목코드", "회사명", "근거", "발견"}
