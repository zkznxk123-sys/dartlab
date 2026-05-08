"""LLM 본체 흐름 — DartLab 정체성 system prompt + 직통 답변. 5 패스 graph 폐기.

어떤 LLM (GPT / Claude / Gemini / Local) 이 연결되어도 DARTLAB_CHAT_SYSTEM 이 본체.
분석 의도 (종목코드 / 분석 키워드 / 명시적 모드) 일 때만 loop.stream() 가 streamLLMPasses
로 라우팅한다. 그 외 메타 질문 / chitchat / 일반 대화는 본 함수가 처리.

provider.generate_stream 지원 시 token 단위 streaming → UI typing 효과.
미지원 provider 는 stream_provider helper 가 generate() wrap fallback.

agent_gateway 이벤트 어휘: chunk / done. (graph_node 없음 — chat 흐름은 phase 없음.)
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from dartlab.ai.contracts import TraceEvent
from dartlab.ai.providers import stream_provider

from .prompts import DARTLAB_CHAT_SYSTEM


def streamChatNative(question: str, provider: Any, **kwargs: Any) -> Iterator[TraceEvent]:
    history = list(kwargs.get("history") or kwargs.get("messages") or [])
    messages: list[dict[str, Any]] = [{"role": "system", "content": DARTLAB_CHAT_SYSTEM}]
    for entry in history:
        if not isinstance(entry, dict):
            continue
        role = entry.get("role")
        content = entry.get("content") or entry.get("text") or ""
        if role in {"user", "assistant"} and content:
            messages.append({"role": role, "content": str(content)})
    user_text = str(question or "").strip()
    if user_text:
        messages.append({"role": "user", "content": user_text})

    # chat-native 흐름은 phase 라벨 없음. message.loading + chunk streaming 이 진행 표현 전담.
    accumulated = ""
    try:
        for chunk in stream_provider(provider, messages, []):
            if chunk.text:
                accumulated += chunk.text
                yield TraceEvent("chunk", {"text": chunk.text})
            if chunk.final:
                break
    except Exception as exc:  # noqa: BLE001
        yield TraceEvent("error", {"error": str(exc)})
        return

    if not accumulated.strip():
        yield TraceEvent("error", {"error": "empty_response"})
        return

    yield TraceEvent(
        "done",
        {
            "refs": [],
            "artifacts": [],
            "verification": {"ok": True, "issues": [], "refId": "verify:answer"},
            "responseMeta": {
                "finalEvent": "answer",
                "responseStatus": "ok",
                "refCount": 0,
                "passes": ["chat"],
                "mode": "chat-native",
            },
        },
    )
