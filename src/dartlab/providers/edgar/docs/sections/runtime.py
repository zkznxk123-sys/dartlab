from __future__ import annotations

FALLBACK_TOPIC_ID = "fullDocument"
SUPPORTED_FORM_TYPES = ("10-K", "10-Q", "20-F")


def topicNamespace(formType: str, topicId: str) -> str:
    """topicNamespace — TODO 한국어 동작 설명."""
    return f"{formType}::{topicId}"


def fallbackTopic(formType: str) -> str:
    """fallbackTopic — TODO 한국어 동작 설명."""
    return topicNamespace(formType, FALLBACK_TOPIC_ID)
