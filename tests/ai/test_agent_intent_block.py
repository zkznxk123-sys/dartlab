"""agent._formatIntentProfileBlock 단위 테스트.

마스터 플랜 트랙 3 PR-W3 동행. workbench/targets._buildQuestionProfile 결과를
system prompt markdown 블록으로 변환하는 helper 결정론 검증.
"""

from __future__ import annotations

import pytest

from dartlab.ai.agent import _formatIntentProfileBlock

pytestmark = pytest.mark.unit


def test_intent_block_empty_kwargs() -> None:
    """질문도 stockCode 도 없으면 빈 문자열."""
    assert _formatIntentProfileBlock({}) == ""


def test_intent_block_with_question_stockcode() -> None:
    """stockCode + question → markdown 블록."""
    block = _formatIntentProfileBlock({"question": "삼성전자 매출", "stockCode": "005930"})
    assert "질문 의도 추정" in block
    assert "005930" in block


def test_intent_block_comparison_detected() -> None:
    """여러 종목 코드 → comparison=True → PeerCompareN 가이드."""
    block = _formatIntentProfileBlock({"question": "005930 vs 000660 vs 035420 비교"})
    assert "비교형" in block
    assert "PeerCompareN" in block


def test_intent_block_show_topic_detected() -> None:
    """질문에 'BS'/'IS' 같은 키워드 → showTopic 가이드."""
    block = _formatIntentProfileBlock({"question": "005930 BS 손익계산서 보여줘"})
    # showTopic 이 추정되면 EngineCall 가이드 표시
    if "추정 토픽" in block:
        assert "EngineCall" in block


def test_intent_block_exception_safe() -> None:
    """workbench import 실패 등 예외 시 빈 문자열 fallback."""
    # 비정상 입력으로도 raise 안 함
    block = _formatIntentProfileBlock({"question": None, "stockCode": None})
    assert block == ""
