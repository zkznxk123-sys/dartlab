from __future__ import annotations

FALLBACK_TOPIC_ID = "fullDocument"
SUPPORTED_FORM_TYPES = ("10-K", "10-Q", "20-F")


def topicNamespace(formType: str, topicId: str) -> str:
    """``"formType::topicId"`` 네임스페이스 문자열 생성.

    Args:
        formType: ``"10-K"``/``"10-Q"``/``"20-F"``.
        topicId: topic 식별자 (예: ``"item1Business"``).

    Returns:
        ``"10-K::item1Business"`` 형식 문자열.

    Raises:
        없음.

    Example:
        >>> topicNamespace("10-K", "item1Business")
        '10-K::item1Business'

    LLM Specifications:
        AntiPatterns:
            - <TODO: 안티패턴>
        OutputSchema:
            - <TODO: 출력 형태>
        Prerequisites:
            - <TODO: 사전조건>
        Freshness:
            - <TODO: 데이터 freshness>
        Dataflow:
            - <TODO: 데이터 흐름>
        TargetMarkets:
            - <TODO: 대상 시장>
    """
    return f"{formType}::{topicId}"


def fallbackTopic(formType: str) -> str:
    """매핑 실패 시 사용할 fallback topic 문자열.

    Args:
        formType: ``"10-K"``/``"10-Q"``/``"20-F"``.

    Returns:
        ``"10-K::fullDocument"`` 형식 문자열.

    Raises:
        없음.

    Example:
        >>> fallbackTopic("10-K")
        '10-K::fullDocument'

    LLM Specifications:
        AntiPatterns:
            - <TODO: 안티패턴>
        OutputSchema:
            - <TODO: 출력 형태>
        Prerequisites:
            - <TODO: 사전조건>
        Freshness:
            - <TODO: 데이터 freshness>
        Dataflow:
            - <TODO: 데이터 흐름>
        TargetMarkets:
            - <TODO: 대상 시장>
    """
    return topicNamespace(formType, FALLBACK_TOPIC_ID)
