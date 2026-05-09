"""agent._microcompact — 옛 assistant reasoning 트리밍, tool_calls 보존."""

from __future__ import annotations

from typing import Any

import pytest

from dartlab.ai.agent import _microcompact


def _ai(content: str | None, *, tool_calls: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    msg: dict[str, Any] = {"role": "assistant", "content": content}
    if tool_calls is not None:
        msg["tool_calls"] = tool_calls
    return msg


def _tc(call_id: str, name: str = "RunPython") -> dict[str, Any]:
    return {"id": call_id, "type": "function", "function": {"name": name, "arguments": "{}"}}


@pytest.mark.unit
def test_keeps_last_two_assistant_messages_intact() -> None:
    messages = [
        {"role": "system", "content": "sys"},
        {"role": "user", "content": "q"},
        _ai("reasoning A", tool_calls=[_tc("a")]),
        {"role": "tool", "tool_call_id": "a", "content": "result"},
        _ai("reasoning B", tool_calls=[_tc("b")]),
        {"role": "tool", "tool_call_id": "b", "content": "result"},
        _ai("reasoning C", tool_calls=[_tc("c")]),
        {"role": "tool", "tool_call_id": "c", "content": "result"},
    ]

    _microcompact(messages, keep_last=2)

    # A 는 트리밍, B/C 는 보존
    assert messages[2]["content"] is None
    assert messages[4]["content"] == "reasoning B"
    assert messages[6]["content"] == "reasoning C"


@pytest.mark.unit
def test_preserves_tool_calls_structure() -> None:
    tc_a = _tc("a")
    messages = [
        _ai("old reasoning", tool_calls=[tc_a]),
        _ai("mid", tool_calls=[_tc("b")]),
        _ai("new", tool_calls=[_tc("c")]),
    ]

    _microcompact(messages, keep_last=2)

    # 옛 message 의 content 는 None, tool_calls 는 동일 객체
    assert messages[0]["content"] is None
    assert messages[0]["tool_calls"] == [tc_a]


@pytest.mark.unit
def test_noop_when_few_assistant_messages() -> None:
    messages = [
        {"role": "user", "content": "q"},
        _ai("only one", tool_calls=[_tc("a")]),
    ]

    _microcompact(messages, keep_last=2)

    assert messages[1]["content"] == "only one"


@pytest.mark.unit
def test_noop_when_exactly_keep_last() -> None:
    messages = [
        _ai("first", tool_calls=[_tc("a")]),
        _ai("second", tool_calls=[_tc("b")]),
    ]

    _microcompact(messages, keep_last=2)

    assert messages[0]["content"] == "first"
    assert messages[1]["content"] == "second"


@pytest.mark.unit
def test_does_not_strip_assistant_without_tool_calls() -> None:
    # 최종 답변 (tool_calls 없는 assistant) 은 reasoning 이 본문 — 트리밍하면 답이 사라짐
    messages = [
        _ai("final answer 1"),
        _ai("mid", tool_calls=[_tc("b")]),
        _ai("mid 2", tool_calls=[_tc("c")]),
        _ai("final answer 2"),
    ]

    _microcompact(messages, keep_last=2)

    # tool_calls 없는 assistant 는 항상 보존 (조건: tool_calls and content)
    assert messages[0]["content"] == "final answer 1"
    assert messages[3]["content"] == "final answer 2"


@pytest.mark.unit
def test_does_not_touch_user_or_system_messages() -> None:
    messages = [
        {"role": "system", "content": "sys"},
        {"role": "user", "content": "u1"},
        _ai("a1", tool_calls=[_tc("a")]),
        {"role": "user", "content": "u2"},
        _ai("a2", tool_calls=[_tc("b")]),
        _ai("a3", tool_calls=[_tc("c")]),
    ]

    _microcompact(messages, keep_last=2)

    assert messages[0]["content"] == "sys"
    assert messages[1]["content"] == "u1"
    assert messages[3]["content"] == "u2"
    # a1 만 트리밍 (마지막 2 = a2, a3)
    assert messages[2]["content"] is None
    assert messages[4]["content"] == "a2"
    assert messages[5]["content"] == "a3"


@pytest.mark.unit
def test_preserves_none_content() -> None:
    # 이미 None 인 content 는 그대로
    messages = [
        _ai(None, tool_calls=[_tc("a")]),
        _ai("b", tool_calls=[_tc("b")]),
        _ai("c", tool_calls=[_tc("c")]),
    ]

    _microcompact(messages, keep_last=2)

    assert messages[0]["content"] is None
