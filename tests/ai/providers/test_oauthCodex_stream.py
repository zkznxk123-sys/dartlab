"""OAuth Codex provider streaming SSE 단위 테스트 — PR-L1.

마스터 플랜 v2 트랙 6 PR-L1 (cryptic-discovering-kettle.md). httpx.stream 의 SSE
event 를 직접 yield 하는 _iterSseRawEvents / _streamProviderTurnFromSse 핵심
helper 검증. 외부 backend 호출 0 — _iterSseRawEvents 를 monkeypatch 로 대체.
"""

from __future__ import annotations

from typing import Any

import pytest

from dartlab.ai.providers import oauthCodex
from dartlab.ai.providers.oauthCodex import (
    _SSE_DONE_MARK,
    _parseSseLine,
    _streamProviderTurnFromSse,
)

pytestmark = pytest.mark.unit


def test_parseSseLine_data_event_parses_json() -> None:
    """data: {...} 양식 → dict."""
    line = 'data: {"type": "response.output_text.delta", "delta": "안녕"}'
    parsed = _parseSseLine(line)
    assert parsed is not None
    assert parsed["type"] == "response.output_text.delta"
    assert parsed["delta"] == "안녕"


def test_parseSseLine_done_returns_mark() -> None:
    """data: [DONE] → 종료 마커."""
    parsed = _parseSseLine("data: [DONE]")
    assert parsed is _SSE_DONE_MARK


def test_parseSseLine_non_data_returns_none() -> None:
    """data: prefix 없는 line → None (skip)."""
    assert _parseSseLine("event: foo") is None
    assert _parseSseLine("") is None
    assert _parseSseLine(":heartbeat") is None


def test_parseSseLine_invalid_json_returns_none() -> None:
    """data: <invalid json> → None (skip)."""
    assert _parseSseLine("data: not-a-json") is None


def test_streamProviderTurnFromSse_text_delta_yields_chunks_then_final(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """text delta 3 회 + response.completed → 3 text chunk + 1 final."""
    events = [
        {"type": "response.output_text.delta", "delta": "삼"},
        {"type": "response.output_text.delta", "delta": "성"},
        {"type": "response.output_text.delta", "delta": "전자"},
        {
            "type": "response.completed",
            "response": {
                "output": [
                    {
                        "type": "message",
                        "content": [{"type": "output_text", "text": "삼성전자 분석"}],
                    }
                ]
            },
        },
    ]
    monkeypatch.setattr(oauthCodex, "_iterSseRawEvents", lambda token, body: iter(events))

    chunks = list(_streamProviderTurnFromSse("token", {"model": "x"}))
    text_chunks = [c for c in chunks if not c.final]
    final = [c for c in chunks if c.final]
    assert len(text_chunks) == 3
    assert [c.text for c in text_chunks] == ["삼", "성", "전자"]
    assert len(final) == 1
    assert final[0].turn is not None
    # completed_text 가 있으면 그것을 우선 사용 (delta 누적보다 정확)
    assert final[0].turn.content == "삼성전자 분석"


def test_streamProviderTurnFromSse_tool_call_streaming(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """function_call_arguments delta → final.toolCalls 누적."""
    events = [
        {
            "type": "response.output_item.added",
            "item": {
                "type": "function_call",
                "id": "fc_1",
                "call_id": "call_abc",
                "name": "EngineCall",
            },
        },
        {"type": "response.function_call_arguments.delta", "item_id": "fc_1", "delta": '{"scan":'},
        {"type": "response.function_call_arguments.delta", "item_id": "fc_1", "delta": '"roe"}'},
        {
            "type": "response.function_call_arguments.done",
            "item_id": "fc_1",
            "arguments": '{"scan":"roe"}',
        },
        {"type": "response.completed", "response": {"output": []}},
    ]
    monkeypatch.setattr(oauthCodex, "_iterSseRawEvents", lambda token, body: iter(events))

    chunks = list(_streamProviderTurnFromSse("token", {"model": "x"}))
    final = chunks[-1]
    assert final.final is True
    assert final.turn is not None
    assert len(final.turn.toolCalls) == 1
    tc = final.turn.toolCalls[0]
    assert tc.id == "call_abc"
    assert tc.name == "EngineCall"
    assert tc.args == {"scan": "roe"}


def test_streamProviderTurnFromSse_text_then_tool_call_mixed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """text delta 후 tool call — 양쪽 보존."""
    events = [
        {"type": "response.output_text.delta", "delta": "분석 시작"},
        {
            "type": "response.output_item.added",
            "item": {"type": "function_call", "id": "fc_1", "call_id": "c1", "name": "Read"},
        },
        {
            "type": "response.output_item.done",
            "item": {
                "type": "function_call",
                "id": "fc_1",
                "arguments": '{"path":"/x"}',
            },
        },
        {"type": "response.completed", "response": {"output": []}},
    ]
    monkeypatch.setattr(oauthCodex, "_iterSseRawEvents", lambda token, body: iter(events))

    chunks = list(_streamProviderTurnFromSse("token", {"model": "x"}))
    text_chunks = [c for c in chunks if not c.final]
    final = chunks[-1]
    assert len(text_chunks) == 1
    assert text_chunks[0].text == "분석 시작"
    assert final.turn is not None
    assert len(final.turn.toolCalls) == 1
    assert final.turn.toolCalls[0].name == "Read"
    # message item 없으면 누적 text 가 content 로
    assert final.turn.content == "분석 시작"


def test_streamProviderTurnFromSse_unknown_event_types_ignored(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """모르는 event type → skip, 회귀 가드."""
    events = [
        {"type": "response.created", "id": "resp_1"},
        {"type": "response.in_progress"},
        {"type": "response.output_text.delta", "delta": "OK"},
        {"type": "ping"},
        {"type": "response.completed", "response": {"output": []}},
    ]
    monkeypatch.setattr(oauthCodex, "_iterSseRawEvents", lambda token, body: iter(events))

    chunks = list(_streamProviderTurnFromSse("token", {"model": "x"}))
    text_chunks = [c for c in chunks if not c.final]
    assert len(text_chunks) == 1
    assert text_chunks[0].text == "OK"
    assert chunks[-1].final is True


def test_streamProviderTurnFromSse_empty_delta_does_not_yield(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """delta 빈 문자열 → chunk yield 안 함 (회귀 가드 — UI 가 빈 chunk 처리 부담)."""
    events = [
        {"type": "response.output_text.delta", "delta": ""},
        {"type": "response.output_text.delta", "delta": "안녕"},
        {"type": "response.completed", "response": {"output": []}},
    ]
    monkeypatch.setattr(oauthCodex, "_iterSseRawEvents", lambda token, body: iter(events))

    chunks = list(_streamProviderTurnFromSse("token", {"model": "x"}))
    text_chunks = [c for c in chunks if not c.final]
    assert len(text_chunks) == 1
    assert text_chunks[0].text == "안녕"


def test_provider_has_generateStream_method() -> None:
    """OAuthCodexProvider.generateStream 메서드 존재 + callable.

    streamProvider 추상화의 hasattr 분기 진입 조건 — 본 메서드 없으면 fake-typing
    fallback path 진입 회귀.
    """
    from dartlab.ai.providers import ProviderConfig
    from dartlab.ai.providers.oauthCodex import OAuthCodexProvider

    cfg = ProviderConfig(provider="oauth-codex", model="x")
    p = OAuthCodexProvider(cfg)
    assert hasattr(p, "generateStream")
    assert callable(p.generateStream)
