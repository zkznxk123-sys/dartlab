"""classifyCategory 3분류기 단위 테스트 — P8 구현 검증."""

from __future__ import annotations

import pytest

from dartlab.ai.context.intent import Category, classifyCategory


@pytest.mark.unit
class TestClassifyCategoryOutOfScope:
    def test_weather(self):
        assert classifyCategory("오늘 날씨 어때") == Category.OUT_OF_SCOPE

    def test_python_generic(self):
        assert classifyCategory("파이썬 리스트 정렬 방법") == Category.OUT_OF_SCOPE

    def test_greeting(self):
        assert classifyCategory("안녕, 반가워") == Category.OUT_OF_SCOPE

    def test_recipe(self):
        assert classifyCategory("된장찌개 레시피 알려줘") == Category.OUT_OF_SCOPE


@pytest.mark.unit
class TestClassifyCategoryMeta:
    def test_what_is(self):
        assert classifyCategory("dartlab 이 뭐야") == Category.META

    def test_how_to_use(self):
        assert classifyCategory("dartlab 어떻게 쓰는거야") == Category.META

    def test_capabilities(self):
        assert classifyCategory("어떤 기능 있어") == Category.META

    def test_usage(self):
        assert classifyCategory("사용법 알려줘") == Category.META

    def test_meta_even_with_korean_particle(self):
        assert classifyCategory("dartlab 어떻게 설치해") == Category.META


@pytest.mark.unit
class TestClassifyCategoryFinance:
    def test_explicit_company(self):
        assert classifyCategory("삼성전자 수익성 분석") == Category.FINANCE

    def test_credit(self):
        assert classifyCategory("대우건설 부채") == Category.FINANCE

    def test_macro_ambiguous(self):
        # 사용자 결정: 애매한 금융 주변 질문도 FINANCE
        assert classifyCategory("최근 경제 어때") == Category.FINANCE

    def test_market_flow(self):
        assert classifyCategory("시장 흐름 어때") == Category.FINANCE

    def test_rate_trend(self):
        assert classifyCategory("금리 동향") == Category.FINANCE

    def test_cycle(self):
        assert classifyCategory("반도체 사이클 어디쯤") == Category.FINANCE

    def test_ambiguous_defaults_finance(self):
        # 모호하면 FINANCE (경유 강제)
        assert classifyCategory("이 회사 어때") == Category.FINANCE

    def test_empty_defaults_finance(self):
        # 빈 질문도 FINANCE fallback
        assert classifyCategory("") == Category.FINANCE

    def test_stock_code_hint_forces_finance(self):
        # stockCode 힌트 있으면 질문 내용 무관하게 FINANCE
        assert classifyCategory("날씨 어때", stockCode="005930") == Category.FINANCE

    def test_company_context_wins_over_meta_word(self):
        # 금융 강키워드가 있으면 "dartlab" 이 있어도 FINANCE 로 복귀
        assert classifyCategory("dartlab 으로 삼성전자 수익성 분석해줘") == Category.FINANCE
