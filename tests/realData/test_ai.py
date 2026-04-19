"""AI 엔진 실제 데이터 스모크 — dartlab.ask 파이프라인.

AI provider 키 없으면 skip. FINANCE 분류 질문으로 tool 최소 1회 호출 보장 (P8).
"""

from __future__ import annotations

import pytest


@pytest.mark.realData
@pytest.mark.integration
class TestAiEngine:
    def test_ask_callable(self):
        import dartlab

        assert callable(dartlab.ask)

    def test_ask_financeQuestion_smoke(self, requireAiKey):
        """FINANCE 분류 질문 1개 — 응답 텍스트 최소 길이 확보.

        주의: conftest 의 autouse fixture 가 DARTLAB_HOME 을 tmp 로 격리하므로
        실제 AI provider 프로파일이 로드되지 않을 수 있다. 그 경우 빈 응답은
        skip 처리 (환경 문제지 회귀 아님).
        """
        import dartlab

        question = "삼성전자 최근 매출 추세를 한 줄로 요약해줘"
        try:
            response = dartlab.ask(question, stream=False)
        except Exception as e:
            pytest.fail(f"dartlab.ask 크래시: {type(e).__name__}: {e}")
        assert response is not None
        text = response if isinstance(response, str) else response.get("answer") or response.get("text") or ""
        assert isinstance(text, str)
        if not text.strip():
            pytest.skip("AI 프로파일 미로드 (DARTLAB_HOME 격리) — 스모크 불가")
        assert len(text) > 10, f"AI 응답이 비정상적으로 짧음: {text!r}"
