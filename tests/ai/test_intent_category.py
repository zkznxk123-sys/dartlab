"""질문 분류는 고정 카테고리가 아니라 Workbench profile로 표현한다."""

from __future__ import annotations

import pytest

from dartlab.ai.workbench.loop import _buildQuestionProfile

pytestmark = pytest.mark.unit


def test_company_question_gets_company_profile():
    profile = _buildQuestionProfile("삼성전자 재무상태표 확인")

    assert profile["taskType"] == "companyResearch"
    assert profile["targets"] == ["삼성전자"]
    assert profile["showTopic"] == "BS"


def test_stock_code_hint_sets_target():
    profile = _buildQuestionProfile("날씨 어때", stockCode="005930")

    assert profile["taskType"] == "companyResearch"
    assert profile["targets"] == ["005930"]


def test_capability_question_stays_research_without_hard_category():
    profile = _buildQuestionProfile("dartlab 뭐 할 수 있니")

    assert profile["taskType"] == "research"
    assert profile["targets"] == []


def test_comparison_profile_detects_multiple_targets():
    profile = _buildQuestionProfile("삼성전자와 SK하이닉스 재무상태표 비교")

    assert profile["comparison"] is True
    assert profile["targets"] == ["삼성전자", "SK하이닉스"]
