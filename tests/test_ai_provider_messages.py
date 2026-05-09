"""Provider neutral schema → native message 변환 단위 검증.

각 어댑터가 anthropic 친화 neutral schema 의 assistant tool_use / tool role tool_result
블록을 자기 SDK 형식으로 올바르게 변환하는지 본다. 실제 SDK 호출은 하지 않는다.
"""

from __future__ import annotations

import json

import pytest

pytestmark = pytest.mark.unit


_NEUTRAL_CONVO = [
    {"role": "system", "content": "분석가 정체성"},
    {"role": "user", "content": "삼성전자 ROE"},
    {
        "role": "assistant",
        "content": [
            {"type": "text", "text": "Company.show 호출"},
            {
                "type": "tool_use",
                "id": "tu_1",
                "name": "run_python",
                "input": {"code": "show('005930', topic='IS')"},
            },
        ],
    },
    {
        "role": "tool",
        "content": [
            {
                "type": "tool_result",
                "tool_use_id": "tu_1",
                "content": {"summary": "OPM 18.5%"},
                "is_error": False,
            }
        ],
    },
    {"role": "user", "content": "ROE 도 보여줘"},
]


# ── OpenAI / xAI ────────────────────────────────────────────────────────────


def test_openai_messages_translation_shape():
    from dartlab.ai.providers.openai import _toOpenAIMessages

    out = _toOpenAIMessages(_NEUTRAL_CONVO)

    roles = [m["role"] for m in out]
    assert roles == ["system", "user", "assistant", "tool", "user"]

    assistant = out[2]
    assert assistant["content"] == "Company.show 호출"
    assert len(assistant["tool_calls"]) == 1
    tc = assistant["tool_calls"][0]
    assert tc["id"] == "tu_1"
    assert tc["type"] == "function"
    assert tc["function"]["name"] == "run_python"
    assert json.loads(tc["function"]["arguments"]) == {"code": "show('005930', topic='IS')"}

    tool = out[3]
    assert tool["tool_call_id"] == "tu_1"
    assert "OPM 18.5" in tool["content"]


def test_openai_assistant_text_only_omits_tool_calls():
    from dartlab.ai.providers.openai import _toOpenAIMessages

    out = _toOpenAIMessages([{"role": "assistant", "content": [{"type": "text", "text": "hi"}]}])
    assert "tool_calls" not in out[0]
    assert out[0]["content"] == "hi"


# ── Google ──────────────────────────────────────────────────────────────────


def test_google_contents_translation_shape():
    from dartlab.ai.providers.google import _toGenaiContents

    out = _toGenaiContents(_NEUTRAL_CONVO)

    # system 은 google contents 에 안 들어간다 (config 로 빠짐)
    roles = [m["role"] for m in out]
    assert "system" not in roles
    assert roles[0] == "user"  # 원래 user
    assert roles[1] == "model"  # 원래 assistant
    assert roles[2] == "user"  # tool result (google 은 tool 도 user 로)
    assert roles[3] == "user"  # 원래 user

    model_turn = out[1]
    fn_call_part = next((p for p in model_turn["parts"] if "function_call" in p), None)
    assert fn_call_part is not None
    assert fn_call_part["function_call"]["name"] == "run_python"
    assert "code" in fn_call_part["function_call"]["args"]

    tool_turn = out[2]
    fn_resp_part = next((p for p in tool_turn["parts"] if "function_response" in p), None)
    assert fn_resp_part is not None
    assert fn_resp_part["function_response"]["name"] == "tu_1"


# ── Ollama ──────────────────────────────────────────────────────────────────


def test_ollama_messages_translation_shape():
    from dartlab.ai.providers.ollama import _toOllamaMessages

    out = _toOllamaMessages(_NEUTRAL_CONVO)

    roles = [m["role"] for m in out]
    assert roles == ["system", "user", "assistant", "tool", "user"]

    assistant = out[2]
    assert assistant["content"] == "Company.show 호출"
    assert len(assistant["tool_calls"]) == 1
    tc = assistant["tool_calls"][0]
    assert tc["function"]["name"] == "run_python"
    assert tc["function"]["arguments"] == {"code": "show('005930', topic='IS')"}

    tool = out[3]
    assert "OPM 18.5" in tool["content"]
