"""ChatGPT OAuth transport for Ask Workbench providers."""

from __future__ import annotations

import json
import os
import time
from typing import Any

import httpx

from dartlab.ai.settings.model_resolver import fallback_models, sort_openai_models

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


def availableModels(*, allow_fetch: bool = True) -> list[str]:
    """사용 가능한 OAuth 모델 목록 — 원격 모델 우선, 공식 fallback 사용.

    allow_fetch=False → cache 만 조회 (없으면 빈 list). profile 화면 표시처럼
    cold HTTP 비용 (DNS/TLS cold init 누적 ~40s) 을 절대 감당 못하는 경로용.
    """
    configured = os.environ.get("DARTLAB_OAUTH_MODELS")
    if configured:
        return sort_openai_models([item.strip() for item in configured.split(",") if item.strip()])

    global _MODELS_CACHE, _MODELS_CACHE_TS
    now = time.time()
    if _MODELS_CACHE and (now - _MODELS_CACHE_TS) < _MODELS_CACHE_TTL:
        return _MODELS_CACHE.copy()

    if not allow_fetch:
        return []

    token = _valid_token_or_none()
    if os.environ.get("DARTLAB_OAUTH_TOKEN") and os.environ.get("DARTLAB_OAUTH_FETCH_MODELS") != "1":
        token = None
    remote = _fetch_remote_models(token) if token else None
    # fallback 도 allow_fetch=False — 재귀 (latest_openai_model→_resolveBackendLatest→
    # availableModels) 막기. 정적 fallback `gpt-5.5` 가 종착.
    _MODELS_CACHE = sort_openai_models(remote) if remote else fallback_models("oauth-codex", allow_fetch=False)
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
        if models:
            return models[0]
        # fallback 도 allow_fetch=False — fallback path 안에서 또 cold HTTP 트리거 X.
        fallback = fallback_models("oauth-codex", allow_fetch=False)
        return fallback[0] if fallback else "gpt-5.2"

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

    def _get_token_or_raise(self) -> str:
        return _valid_token_or_raise()

    def _build_body(self, messages: list[dict[str, Any]]) -> dict[str, Any]:
        return _build_body(messages, [], model=self.resolved_model)

    def _request_with_retry(self, token: str, body: dict[str, Any], stream: bool = False) -> Any:
        if stream:
            headers = _headers(token)
            return httpx.post(f"{CODEX_API_BASE}{CODEX_RESPONSES_PATH}", headers=headers, json=body, timeout=90)
        return _request_with_retry(token, body)

    def stream(self, messages: list[dict[str, Any]]):
        token = self._get_token_or_raise()
        body = self._build_body(messages)
        response = self._request_with_retry(token, body, stream=True)
        for line in response.iter_lines(decode_unicode=True):
            if not isinstance(line, str) or not line.startswith("data: "):
                continue
            data = line[6:]
            if data == "[DONE]":
                break
            try:
                event = json.loads(data)
            except json.JSONDecodeError:
                continue
            if event.get("type") == "response.output_text.delta":
                delta = event.get("delta")
                if isinstance(delta, str):
                    yield delta


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
    snippet = _extract_error_snippet(body)
    suffix = f" — {snippet}" if snippet else ""
    if status == 401:
        raise OAuthCodexError("relogin", "ChatGPT OAuth 인증이 만료되었습니다.", detail=detail)
    if status == 403:
        raise OAuthCodexError("forbidden", "ChatGPT OAuth backend 접근이 거부되었습니다.", detail=detail)
    if status == 404:
        raise OAuthCodexError("endpoint", "ChatGPT OAuth backend 엔드포인트를 찾지 못했습니다.", detail=detail)
    if status == 429:
        from .base import RateLimitError

        raise RateLimitError("oauth-codex", "ChatGPT OAuth backend 요청 한도를 초과했습니다.")
    raise OAuthCodexError("http_error", f"ChatGPT OAuth backend HTTP {status}{suffix}", detail=detail)


_SNIPPET_MAX = 160


def _extract_error_snippet(body: str) -> str:
    """응답 본문에서 사용자에게 보여줄 짧은 사유 추출. 보통 OpenAI 식 {error:{message:...}}."""
    if not body:
        return ""
    try:
        data = json.loads(body)
    except (json.JSONDecodeError, ValueError):
        return body.strip()[:_SNIPPET_MAX]
    if isinstance(data, dict):
        err = data.get("error")
        if isinstance(err, dict):
            msg = err.get("message") or err.get("code") or err.get("type")
            if msg:
                return str(msg)[:_SNIPPET_MAX]
        if data.get("message"):
            return str(data["message"])[:_SNIPPET_MAX]
    return body.strip()[:_SNIPPET_MAX]


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
