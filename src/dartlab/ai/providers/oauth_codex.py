"""ChatGPT OAuth transport for Ask Workbench providers."""

from __future__ import annotations

import json
import os
import time
from typing import Any

import httpx

from dartlab.core.ai.model_resolver import fallback_models, sort_openai_models

from . import ProviderConfig, ProviderTurn, ToolCall
from .support import oauth_token as oauthToken
from .support.oauth_token import TokenRefreshError

CODEX_API_BASE = "https://chatgpt.com/backend-api"
CODEX_RESPONSES_PATH = "/codex/responses"
_MODELS_CACHE: list[str] | None = None
_MODELS_CACHE_TS = 0.0
_MODELS_CACHE_TTL = 300.0


class OAuthCodexError(RuntimeError):
    """OAuth transport error with a stable action code."""

    def __init__(self, action: str, message: str, *, detail: str = "") -> None:
        self.action = action
        self.detail = detail
        super().__init__(message)


def availableModels() -> list[str]:
    """사용 가능한 OAuth 모델 목록 — 원격 모델 우선, 공식 fallback 사용.

    Description
    -----------
    ChatGPT OAuth backend 의 모델 목록을 조회하고 짧게 캐시한다. 토큰이 없거나
    원격 조회가 실패하면 중앙 모델 resolver 의 OpenAI-family fallback 만 반환한다.

    Parameters
    ----------
    없음
        환경변수 `DARTLAB_OAUTH_MODELS`가 있으면 해당 목록을 우선 사용한다.

    Returns
    -------
    list[str]
        model_id : str — provider 에 전달할 모델 식별자

    Raises
    ------
    없음
        원격 조회 실패는 fallback 으로 처리한다.

    Examples
    --------
    >>> availableModels()[0]
    'gpt-5.2'

    Notes
    -----
    이 함수는 모델 선택 SSOT 가 아니라 provider runtime discovery 다.

    Guide
    -----
    UI 는 저장된 profile 모델보다 이 함수와 중앙 resolver 의 최신값을 우선 표시한다.

    See Also
    --------
    OAuthCodexProvider : OAuth workbench provider.
    """

    configured = os.environ.get("DARTLAB_OAUTH_MODELS")
    if configured:
        return sort_openai_models([item.strip() for item in configured.split(",") if item.strip()])

    global _MODELS_CACHE, _MODELS_CACHE_TS
    now = time.time()
    if _MODELS_CACHE and (now - _MODELS_CACHE_TS) < _MODELS_CACHE_TTL:
        return _MODELS_CACHE.copy()

    token = _valid_token_or_none()
    if os.environ.get("DARTLAB_OAUTH_TOKEN") and os.environ.get("DARTLAB_OAUTH_FETCH_MODELS") != "1":
        token = None
    remote = _fetch_remote_models(token) if token else None
    _MODELS_CACHE = sort_openai_models(remote) if remote else fallback_models("oauth-codex")
    _MODELS_CACHE_TS = now
    return _MODELS_CACHE.copy()


class OAuthCodexProvider:
    """ChatGPT OAuth provider for the Ask Workbench tool loop."""

    def __init__(self, config: ProviderConfig | Any) -> None:
        self.config = _normalize_config(config)
        self.resolved_model = self.config.model or self.default_model

    @property
    def default_model(self) -> str:
        models = availableModels()
        return (
            models[0]
            if models
            else (fallback_models("oauth-codex")[0] if fallback_models("oauth-codex") else "gpt-5.2")
        )

    def check_available(self) -> bool:
        try:
            return bool(oauthToken.is_authenticated())
        except (OSError, RuntimeError, TokenRefreshError, ValueError):
            return False

    def generate(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> ProviderTurn:
        token = _valid_token_or_raise()
        body = _build_body(messages, tools, model=self.resolved_model)
        response_text = _request_with_retry(token, body)
        return _parse_sse_response(response_text)


def _normalize_config(config: ProviderConfig | Any) -> ProviderConfig:
    if isinstance(config, ProviderConfig):
        return config
    return ProviderConfig(
        provider=getattr(config, "provider", None) or "oauth-codex",
        model=getattr(config, "model", None),
        base_url=getattr(config, "base_url", None) or getattr(config, "baseUrl", None),
        api_key=getattr(config, "api_key", None) or getattr(config, "apiKey", None),
        temperature=getattr(config, "temperature", None),
    )


def _valid_token_or_none() -> str | None:
    try:
        return oauthToken.get_valid_token()
    except (OSError, RuntimeError, TokenRefreshError, ValueError):
        return None


def _valid_token_or_raise() -> str:
    try:
        token = oauthToken.get_valid_token()
    except TokenRefreshError as exc:
        raise OAuthCodexError("relogin", f"ChatGPT OAuth 토큰 갱신 실패: {exc}") from exc
    except (OSError, RuntimeError, ValueError) as exc:
        raise OAuthCodexError("login", f"ChatGPT OAuth 토큰을 읽지 못했습니다: {exc}") from exc
    if not token:
        raise OAuthCodexError("login", "ChatGPT OAuth 인증이 필요합니다.")
    return token


def _fetch_remote_models(token: str) -> list[str] | None:
    headers = _headers(token, accept_json=True)
    try:
        response = httpx.get(f"{CODEX_API_BASE}/codex/models", headers=headers, timeout=10)
        if response.status_code != 200:
            return None
        payload = response.json()
    except (httpx.HTTPError, json.JSONDecodeError, ValueError):
        return None
    raw_items = payload if isinstance(payload, list) else payload.get("models") or payload.get("data") or []
    models: list[str] = []
    for item in raw_items:
        if isinstance(item, dict):
            model_id = item.get("id") or item.get("model")
        else:
            model_id = str(item)
        if isinstance(model_id, str) and model_id:
            models.append(model_id)
    return models or None


def _request_with_retry(token: str, body: dict[str, Any]) -> str:
    headers = _headers(token)

    def post(active_headers: dict[str, str]) -> httpx.Response:
        return httpx.post(f"{CODEX_API_BASE}{CODEX_RESPONSES_PATH}", headers=active_headers, json=body, timeout=90)

    try:
        response = post(headers)
    except httpx.TimeoutException as exc:
        raise OAuthCodexError("network", "ChatGPT OAuth backend 응답 시간이 초과되었습니다.") from exc
    except httpx.HTTPError as exc:
        raise OAuthCodexError("network", f"ChatGPT OAuth backend 연결 실패: {exc}") from exc

    if response.status_code == 401:
        try:
            refreshed = oauthToken.refresh_access_token()
        except (OSError, RuntimeError, TokenRefreshError, ValueError) as exc:
            raise OAuthCodexError("relogin", f"ChatGPT OAuth 재인증이 필요합니다: {exc}") from exc
        token = refreshed.get("access_token") if isinstance(refreshed, dict) else None
        if token:
            response = post(_headers(token))

    if response.status_code in {502, 503, 504}:
        for attempt in range(2):
            time.sleep(1.5 * (attempt + 1))
            response = post(headers)
            if response.status_code not in {502, 503, 504}:
                break

    if response.status_code != 200:
        _raise_http_error(response.status_code, response.text)
    return response.text


def _headers(token: str, *, accept_json: bool = False) -> dict[str, str]:
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "originator": "codex_cli_rs",
        "accept": "application/json" if accept_json else "text/event-stream",
    }
    account_id = oauthToken.get_account_id()
    if account_id:
        headers["chatgpt-account-id"] = account_id
    return headers


def _raise_http_error(status: int, body: str) -> None:
    detail = body[:500]
    if status == 401:
        raise OAuthCodexError("relogin", "ChatGPT OAuth 인증이 만료되었습니다.", detail=detail)
    if status == 403:
        raise OAuthCodexError("forbidden", "ChatGPT OAuth backend 접근이 거부되었습니다.", detail=detail)
    if status == 404:
        raise OAuthCodexError("endpoint", "ChatGPT OAuth backend 엔드포인트를 찾지 못했습니다.", detail=detail)
    if status == 429:
        raise OAuthCodexError("rate_limit", "ChatGPT OAuth backend 요청 한도를 초과했습니다.", detail=detail)
    raise OAuthCodexError("http_error", f"ChatGPT OAuth backend 오류입니다. HTTP {status}", detail=detail)


def _build_body(messages: list[dict[str, Any]], tools: list[dict[str, Any]], *, model: str) -> dict[str, Any]:
    instructions: list[str] = []
    input_items: list[dict[str, Any]] = []
    for message in messages:
        role = str(message.get("role") or "user")
        content = _message_text(message.get("content"))
        if role == "system":
            if content:
                instructions.append(content)
            continue
        if role == "tool":
            input_items.append(
                {
                    "type": "message",
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": f"[tool_result id={message.get('tool_call_id', '')}]\n{content}"}
                    ],
                }
            )
            continue
        if role == "assistant":
            tool_calls = message.get("tool_calls") or []
            if content:
                input_items.append(
                    {"type": "message", "role": "assistant", "content": [{"type": "output_text", "text": content}]}
                )
            continue
        input_items.append({"type": "message", "role": "user", "content": [{"type": "input_text", "text": content}]})

    body: dict[str, Any] = {
        "model": model,
        "stream": True,
        "store": False,
        "input": input_items,
        "include": ["reasoning.encrypted_content"],
    }
    if instructions:
        body["instructions"] = "\n\n".join(instructions)
    response_tools = _response_tools(tools)
    if response_tools:
        body["tools"] = response_tools
    return body


def _message_text(content: Any) -> str:
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict):
                parts.append(str(item.get("text") or ""))
            elif item is not None:
                parts.append(str(item))
        return "\n\n".join(part for part in parts if part)
    return "" if content is None else str(content)


def _append_tool_calls(content: str, tool_calls: list[Any]) -> str:
    lines = []
    for call in tool_calls:
        if not isinstance(call, dict):
            continue
        function = call.get("function") if isinstance(call.get("function"), dict) else {}
        lines.append(f"- {function.get('name', '')} id={call.get('id', '')} args={function.get('arguments', '')}")
    if not lines:
        return content
    return (content + "\n\n" if content else "") + "[tool_calls]\n" + "\n".join(lines)


def _response_tools(tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
    response_tools: list[dict[str, Any]] = []
    for tool in tools:
        function = tool.get("function") if isinstance(tool, dict) else None
        if not isinstance(function, dict):
            continue
        response_tools.append(
            {
                "type": "function",
                "name": function.get("name"),
                "description": function.get("description", ""),
                "parameters": function.get("parameters", {"type": "object", "properties": {}}),
            }
        )
    return response_tools


def _parse_sse_response(raw: str) -> ProviderTurn:
    text_parts: list[str] = []
    completed_text: list[str] = []
    buffers: dict[str, dict[str, str]] = {}
    finished: list[dict[str, str]] = []

    for line in raw.splitlines():
        if not line.startswith("data: "):
            continue
        data = line[6:]
        if data == "[DONE]":
            break
        try:
            event = json.loads(data)
        except json.JSONDecodeError:
            continue
        event_type = event.get("type")
        if event_type == "response.output_text.delta":
            delta = event.get("delta")
            if isinstance(delta, str):
                text_parts.append(delta)
        elif event_type == "response.output_item.added":
            item = event.get("item") if isinstance(event.get("item"), dict) else {}
            if item.get("type") == "function_call":
                item_id = str(item.get("id") or f"fc_{len(buffers)}")
                buffers[item_id] = {
                    "id": str(item.get("call_id") or item_id),
                    "name": str(item.get("name") or ""),
                    "args": "",
                }
        elif event_type == "response.function_call_arguments.delta":
            item_id = str(event.get("item_id") or "")
            if item_id in buffers:
                buffers[item_id]["args"] += str(event.get("delta") or "")
        elif event_type == "response.function_call_arguments.done":
            item_id = str(event.get("item_id") or "")
            buffer = buffers.pop(item_id, None)
            if buffer is not None:
                final_args = event.get("arguments") if isinstance(event.get("arguments"), str) else None
                if final_args is not None:
                    buffer["args"] = final_args
                finished.append(buffer)
        elif event_type == "response.output_item.done":
            item = event.get("item") if isinstance(event.get("item"), dict) else {}
            if item.get("type") == "function_call":
                item_id = str(item.get("id") or "")
                buffer = buffers.pop(item_id, None)
                if buffer is not None:
                    final_args = item.get("arguments") if isinstance(item.get("arguments"), str) else None
                    if final_args is not None:
                        buffer["args"] = final_args
                    finished.append(buffer)
            elif item.get("type") == "message":
                completed_text.extend(_text_from_message_item(item))
        elif event_type == "response.completed":
            response = event.get("response") if isinstance(event.get("response"), dict) else {}
            for item in response.get("output") or []:
                if not isinstance(item, dict):
                    continue
                if item.get("type") == "message":
                    completed_text.extend(_text_from_message_item(item))
                elif item.get("type") == "function_call":
                    finished.append(
                        {
                            "id": str(item.get("call_id") or item.get("id") or f"fc_{len(finished)}"),
                            "name": str(item.get("name") or ""),
                            "args": str(item.get("arguments") or "{}"),
                        }
                    )

    calls: list[ToolCall] = []
    seen: set[tuple[str, str]] = set()
    for item in finished:
        if not item.get("name"):
            continue
        key = (item.get("id") or "", item.get("name") or "")
        if key in seen:
            continue
        seen.add(key)
        calls.append(ToolCall(id=item["id"], name=item["name"], args=_parse_args(item.get("args") or "{}")))
    return ProviderTurn(content="".join(completed_text) or "".join(text_parts), tool_calls=calls)


def _text_from_message_item(item: dict[str, Any]) -> list[str]:
    out: list[str] = []
    for content in item.get("content") or []:
        if isinstance(content, dict) and content.get("type") == "output_text" and isinstance(content.get("text"), str):
            out.append(content["text"])
    return out


def _parse_args(raw: str) -> dict[str, Any]:
    try:
        parsed = json.loads(raw or "{}")
    except json.JSONDecodeError:
        return {"_raw": raw}
    return parsed if isinstance(parsed, dict) else {}
