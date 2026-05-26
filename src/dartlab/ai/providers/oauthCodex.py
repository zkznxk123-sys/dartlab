"""ChatGPT OAuth transport for Ask Workbench providers."""

from __future__ import annotations

import json
import os
import time
from typing import Any

import httpx

from dartlab.ai.settings.modelResolver import fallbackModels, sortOpenaiModels

from . import ProviderConfig, ProviderTurn, ToolCall
from .support import oauthToken
from .support.oauthToken import TokenRefreshError

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


def availableModels(*, allowFetch: bool = True) -> list[str]:
    """사용 가능한 OAuth 모델 목록 — 원격 모델 우선, 공식 fallback 사용.

    allow_fetch=False → cache 만 조회 (없으면 빈 list). profile 화면 표시처럼
    cold HTTP 비용 (DNS/TLS cold init 누적 ~40s) 을 절대 감당 못하는 경로용.
    """
    configured = os.environ.get("DARTLAB_OAUTH_MODELS")
    if configured:
        return sortOpenaiModels([item.strip() for item in configured.split(",") if item.strip()])

    global _MODELS_CACHE, _MODELS_CACHE_TS
    now = time.time()
    if _MODELS_CACHE and (now - _MODELS_CACHE_TS) < _MODELS_CACHE_TTL:
        return _MODELS_CACHE.copy()

    if not allowFetch:
        return []

    token = _validTokenOrNone()
    if os.environ.get("DARTLAB_OAUTH_TOKEN") and os.environ.get("DARTLAB_OAUTH_FETCH_MODELS") != "1":
        token = None
    remote = _fetchRemoteModels(token) if token else None
    # fallback 도 allow_fetch=False — 재귀 (latest_openai_model→_resolveBackendLatest→
    # availableModels) 막기. 정적 fallback `gpt-5.5` 가 종착.
    _MODELS_CACHE = sortOpenaiModels(remote) if remote else fallbackModels("oauth-codex", allowFetch=False)
    _MODELS_CACHE_TS = now
    return _MODELS_CACHE.copy()


class OAuthCodexProvider:
    """ChatGPT OAuth provider for the Ask Workbench tool loop."""

    def __init__(self, config: ProviderConfig | Any) -> None:
        self.config = _normalizeConfig(config)
        self.resolvedModel = self.config.model or self.defaultModel

    @property
    def defaultModel(self) -> str:
        """OAuth 인증 모델 목록 첫 항목 또는 gpt-5.2 폴백."""
        models = availableModels()
        if models:
            return models[0]
        # fallback 도 allow_fetch=False — fallback path 안에서 또 cold HTTP 트리거 X.
        fallback = fallbackModels("oauth-codex", allowFetch=False)
        return fallback[0] if fallback else "gpt-5.2"

    def checkAvailable(self) -> bool:
        """OAuth 토큰 유효성 검증 — 인증 안 됐으면 False."""
        try:
            return bool(oauthToken.isAuthenticated())
        except (OSError, RuntimeError, TokenRefreshError, ValueError):
            return False

    def generate(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> ProviderTurn:
        """OAuth 토큰 → ChatGPT backend POST → SSE 파싱 → ProviderTurn."""
        token = _validTokenOrRaise()
        body = _buildBody(messages, tools, model=self.resolvedModel)
        response_text = _requestWithRetry(token, body)
        return _parseSseResponse(response_text)

    def _getTokenOrRaise(self) -> str:
        return _validTokenOrRaise()

    def _buildBody(self, messages: list[dict[str, Any]]) -> dict[str, Any]:
        return _buildBody(messages, [], model=self.resolvedModel)

    def _requestWithRetry(self, token: str, body: dict[str, Any], stream: bool = False) -> Any:
        if stream:
            headers = _headers(token)
            return httpx.post(f"{CODEX_API_BASE}{CODEX_RESPONSES_PATH}", headers=headers, json=body, timeout=90)
        return _requestWithRetry(token, body)

    def stream(self, messages: list[dict[str, Any]]):
        """OAuth 토큰 → ChatGPT backend POST → SSE iter_lines → text delta yield."""
        token = self._getTokenOrRaise()
        body = self._buildBody(messages)
        response = self._requestWithRetry(token, body, stream=True)
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


def _normalizeConfig(config: ProviderConfig | Any) -> ProviderConfig:
    if isinstance(config, ProviderConfig):
        return config
    return ProviderConfig(
        provider=getattr(config, "provider", None) or "oauth-codex",
        model=getattr(config, "model", None),
        baseUrl=getattr(config, "base_url", None) or getattr(config, "baseUrl", None),
        apiKey=getattr(config, "api_key", None) or getattr(config, "apiKey", None),
        temperature=getattr(config, "temperature", None),
    )


def _validTokenOrNone() -> str | None:
    try:
        return oauthToken.getValidToken()
    except (OSError, RuntimeError, TokenRefreshError, ValueError):
        return None


def _validTokenOrRaise() -> str:
    try:
        token = oauthToken.getValidToken()
    except TokenRefreshError as exc:
        raise OAuthCodexError("relogin", f"ChatGPT OAuth 토큰 갱신 실패: {exc}") from exc
    except (OSError, RuntimeError, ValueError) as exc:
        raise OAuthCodexError("login", f"ChatGPT OAuth 토큰을 읽지 못했습니다: {exc}") from exc
    if not token:
        raise OAuthCodexError("login", "ChatGPT OAuth 인증이 필요합니다.")
    return token


def _fetchRemoteModels(token: str) -> list[str] | None:
    headers = _headers(token, acceptJson=True)
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
            modelId = item.get("id") or item.get("model")
        else:
            modelId = str(item)
        if isinstance(modelId, str) and modelId:
            models.append(modelId)
    return models or None


def _requestWithRetry(token: str, body: dict[str, Any]) -> str:
    headers = _headers(token)

    def post(activeHeaders: dict[str, str]) -> httpx.Response:
        """POST 호출 헬퍼 — 401 재시도 시 새 토큰 헤더로 재호출."""
        return httpx.post(f"{CODEX_API_BASE}{CODEX_RESPONSES_PATH}", headers=activeHeaders, json=body, timeout=90)

    try:
        response = post(headers)
    except httpx.TimeoutException as exc:
        # 1회 재시도 — 백엔드 일시 슬로다운 흡수. timeout 한 번에 끝나던 회귀 가드.
        time.sleep(2)
        try:
            response = post(headers)
        except httpx.TimeoutException as exc2:
            raise OAuthCodexError(
                "network", "ChatGPT OAuth backend 응답 시간이 초과되었습니다 (1회 재시도 후)."
            ) from exc2
        except httpx.HTTPError as exc2:
            raise OAuthCodexError("network", f"ChatGPT OAuth backend 연결 실패: {exc2}") from exc2
    except httpx.HTTPError as exc:
        raise OAuthCodexError("network", f"ChatGPT OAuth backend 연결 실패: {exc}") from exc

    if response.status_code == 401:
        try:
            refreshed = oauthToken.refreshAccessToken()
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
        _raiseHttpError(response.status_code, response.text)
    return response.text


def _headers(token: str, *, acceptJson: bool = False) -> dict[str, str]:
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "originator": "codex_cli_rs",
        "accept": "application/json" if acceptJson else "text/event-stream",
    }
    account_id = oauthToken.getAccountId()
    if account_id:
        headers["chatgpt-account-id"] = account_id
    return headers


def _raiseHttpError(status: int, body: str) -> None:
    detail = body[:500]
    snippet = _extractErrorSnippet(body)
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


def _extractErrorSnippet(body: str) -> str:
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


def _buildBody(messages: list[dict[str, Any]], tools: list[dict[str, Any]], *, model: str) -> dict[str, Any]:
    instructions: list[str] = []
    input_items: list[dict[str, Any]] = []
    for message in messages:
        role = str(message.get("role") or "user")
        content = _messageText(message.get("content"))
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
            toolCalls = message.get("tool_calls") or []
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
    response_tools = _responseTools(tools)
    if response_tools:
        body["tools"] = response_tools
    return body


def _messageText(content: Any) -> str:
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict):
                parts.append(str(item.get("text") or ""))
            elif item is not None:
                parts.append(str(item))
        return "\n\n".join(part for part in parts if part)
    return "" if content is None else str(content)


def _responseTools(tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
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


def _parseSseResponse(raw: str) -> ProviderTurn:
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
        eventType = event.get("type")
        if eventType == "response.output_text.delta":
            delta = event.get("delta")
            if isinstance(delta, str):
                text_parts.append(delta)
        elif eventType == "response.output_item.added":
            item = event.get("item") if isinstance(event.get("item"), dict) else {}
            if item.get("type") == "function_call":
                item_id = str(item.get("id") or f"fc_{len(buffers)}")
                buffers[item_id] = {
                    "id": str(item.get("call_id") or item_id),
                    "name": str(item.get("name") or ""),
                    "args": "",
                }
        elif eventType == "response.function_call_arguments.delta":
            item_id = str(event.get("item_id") or "")
            if item_id in buffers:
                buffers[item_id]["args"] += str(event.get("delta") or "")
        elif eventType == "response.function_call_arguments.done":
            item_id = str(event.get("item_id") or "")
            buffer = buffers.pop(item_id, None)
            if buffer is not None:
                final_args = event.get("arguments") if isinstance(event.get("arguments"), str) else None
                if final_args is not None:
                    buffer["args"] = final_args
                finished.append(buffer)
        elif eventType == "response.output_item.done":
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
                completed_text.extend(_textFromMessageItem(item))
        elif eventType == "response.completed":
            response = event.get("response") if isinstance(event.get("response"), dict) else {}
            for item in response.get("output") or []:
                if not isinstance(item, dict):
                    continue
                if item.get("type") == "message":
                    completed_text.extend(_textFromMessageItem(item))
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
        calls.append(ToolCall(id=item["id"], name=item["name"], args=_parseArgs(item.get("args") or "{}")))
    return ProviderTurn(content="".join(completed_text) or "".join(text_parts), toolCalls=calls)


def _textFromMessageItem(item: dict[str, Any]) -> list[str]:
    out: list[str] = []
    for content in item.get("content") or []:
        if isinstance(content, dict) and content.get("type") == "output_text" and isinstance(content.get("text"), str):
            out.append(content["text"])
    return out


def _parseArgs(raw: str) -> dict[str, Any]:
    try:
        parsed = json.loads(raw or "{}")
    except json.JSONDecodeError:
        return {"_raw": raw}
    return parsed if isinstance(parsed, dict) else {}
