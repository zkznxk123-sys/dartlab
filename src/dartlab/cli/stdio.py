"""`dartlab chat --stdio` -- JSON Lines protocol for VSCode extension.

stdin: JSON line requests
stdout: JSON line events
Claude Code / Codex pattern: child process spawn + stdio.

Protocol:
    -> {"id":"1","type":"ask","question":"000660 실적","company":"000660"}
    <- {"id":"1","event":"meta","data":{"company":"SK하이닉스","stockCode":"000660"}}
    <- {"id":"1","event":"chunk","data":{"text":"..."}}
    <- {"id":"1","event":"done","data":{}}
    -> {"type":"status"}
    <- {"event":"status","data":{"provider":"oauth-codex","model":"gpt-5.3","ready":true}}
    -> {"type":"ping"}
    <- {"event":"pong","data":{}}
    -> {"type":"setProvider","provider":"gemini","model":"gemini-2.5-flash"}
    <- {"event":"providerChanged","data":{"provider":"gemini","model":"gemini-2.5-flash"}}
    -> {"type":"listTemplates"}
    <- {"event":"templates","data":{"templates":[{"name":"가치투자","description":"...","source":"builtin"}]}}
    -> {"type":"ask","question":"분석","modules":["가치투자","리스크점검"]}
    -> {"type":"exit"}
"""

from __future__ import annotations

import json
import re
import sys
from typing import Any

_CLI_SETUP_PATTERN = re.compile(r"\n?\s*dartlab\.setup\([^)]*\)[^\n]*", re.IGNORECASE)

# Session state
_sessionProvider: str | None = None
_sessionModel: str | None = None


def _emit(obj: dict[str, Any]) -> None:
    """Write one JSON line to stdout."""
    try:
        line = json.dumps(obj, ensure_ascii=False)
    except (UnicodeEncodeError, UnicodeDecodeError):
        # Surrogate 등 인코딩 문제 시 ensure_ascii=True로 fallback
        line = json.dumps(obj, ensure_ascii=True)
    sys.stdout.write(line + "\n")
    sys.stdout.flush()


def _handleAsk(msg: dict[str, Any]) -> None:
    """Process ask message -- stream ask events as JSON lines."""
    from dartlab.ai.kernel import _ask_events

    reqId = msg.get("id", "")
    question = msg.get("question", "")
    company = msg.get("company")
    history = msg.get("history")

    if not question:
        _emit({"id": reqId, "event": "error", "data": {"error": "No question provided"}})
        return

    # AI가 종목을 자율 판단 — 서버/CLI가 resolve하지 않는다
    kwargs: dict[str, Any] = {}
    if company:
        kwargs["stockCode"] = company
    if history:
        kwargs["history"] = history

    # 모듈 프롬프트
    modules = msg.get("modules")  # list[str] | None
    template = msg.get("template")  # str | None (하위호환)
    if modules:
        kwargs["_templateText"] = "\n\n".join(str(item) for item in modules)
    elif template:
        try:
            from dartlab.ai import templates

            kwargs["_templateText"] = templates(template)
        except (FileNotFoundError, ValueError):
            kwargs["_templateText"] = str(template)

    emittedDone = False
    try:
        for event in _ask_events(question, **kwargs):
            if event.kind == "error" and isinstance(event.data, dict):
                _emit({"id": reqId, "event": "error", "data": _sanitizeErrorForUi(event.data)})
            else:
                _emit({"id": reqId, "event": event.kind, "data": event.data})
            if event.kind == "done":
                emittedDone = True
    except KeyboardInterrupt:
        _emit({"id": reqId, "event": "error", "data": {"error": "Interrupted"}})
    except Exception as exc:  # noqa: BLE001
        _emit({"id": reqId, "event": "error", "data": {"error": str(exc)}})

    if not emittedDone:
        _emit({"id": reqId, "event": "done", "data": {}})


def _handleWarmup(_msg: dict[str, Any]) -> None:
    """첫 ask 의 cold-start 비용을 사전 지불.

    extension activate 직후 호출되도록 설계. 다음을 미리 수행:
    - dartlab.ai.kernel 모듈 import (lazy 비용)
    - dartlab.viz.extract import

    실패 항목은 무시 — 워밍업은 best-effort.
    """
    diag: dict[str, Any] = {"warmed": [], "skipped": []}

    def _try(name: str, fn) -> None:
        try:
            fn()
            diag["warmed"].append(name)
        except (ImportError, OSError, RuntimeError) as exc:
            diag["skipped"].append(f"{name}: {exc.__class__.__name__}")

    _try("kernel", lambda: __import__("dartlab.ai.kernel", fromlist=["ask"]))
    _try("viz_extract", lambda: __import__("dartlab.viz.extract", fromlist=["extract_viz_specs"]))

    _emit({"event": "warmup_done", "data": diag})


def _handleStatus(_msg: dict[str, Any]) -> None:
    """Return provider status with available providers list."""
    try:
        from dartlab.ai.settings.profile import get_profile_manager
        from dartlab.ai.settings.provider_catalog import _PROVIDERS

        profile = get_profile_manager().load()
        provider = _sessionProvider or profile.default_provider or "none"
        model = _sessionModel or getattr(profile, "model", None) or ""

        providers = []
        for pid, spec in _PROVIDERS.items():
            if not spec.public:
                continue
            providers.append(
                {
                    "id": spec.id,
                    "label": spec.label,
                    "description": spec.description,
                    "authKind": spec.auth_kind,
                    "signupUrl": spec.signupUrl or "",
                }
            )

        _emit(
            {
                "event": "status",
                "data": {"provider": provider, "model": model, "ready": True, "providers": providers},
            }
        )
    except Exception as exc:  # noqa: BLE001
        _emit(
            {
                "event": "status",
                "data": {"provider": "none", "model": "", "ready": False, "providers": [], "error": str(exc)},
            }
        )


def _handleListTemplates(_msg: dict[str, Any]) -> None:
    """Return available analysis templates/modules."""
    try:
        from dartlab.ai.patterns import list_templates

        templates = list_templates()
        _emit({"event": "templates", "data": {"templates": templates}})
    except Exception as exc:  # noqa: BLE001
        _emit({"event": "templates", "data": {"templates": [], "error": str(exc)}})


def _handleSetProvider(msg: dict[str, Any]) -> None:
    """Change provider/model for this session. Optionally save API key."""
    global _sessionProvider, _sessionModel
    provider = msg.get("provider")
    apiKey = msg.get("apiKey")

    # API 키가 왔으면 저장
    if provider and apiKey:
        try:
            from dartlab.core.credentials import CredentialManager

            CredentialManager().saveKey(f"{provider}_api_key", apiKey)
        except Exception as exc:  # noqa: BLE001
            _emit({"event": "error", "data": {"error": f"키 저장 실패: {exc}"}})
            return

    # provider 인증 확인
    if provider and not apiKey:
        try:
            from dartlab.ai.settings.provider_catalog import get_provider_spec

            spec = get_provider_spec(provider)
            if spec:
                # OAuth provider → 바로 로그인 시작
                if spec.auth_kind == "oauth":
                    _handleOAuthLogin({"provider": provider})
                    return
                # API 키 provider → 키 없으면 needCredential
                if spec.auth_kind == "api_key":
                    from dartlab.core.credentials import CredentialManager

                    cred = CredentialManager().getCredential(f"{provider}_api_key")
                    if not cred.configured:
                        _emit(
                            {
                                "event": "needCredential",
                                "data": {
                                    "provider": provider,
                                    "signupUrl": spec.signupUrl,
                                    "envKey": spec.env_key,
                                    "label": spec.label,
                                },
                            }
                        )
                        return
        except ImportError:
            pass
        except Exception as exc:  # noqa: BLE001
            _emit({"event": "error", "data": {"error": f"provider 확인 실패: {exc}"}})

    _sessionProvider = provider or _sessionProvider
    _sessionModel = msg.get("model") or _sessionModel
    _emit(
        {
            "event": "providerChanged",
            "data": {"provider": _sessionProvider, "model": _sessionModel},
        }
    )


def _handleOAuthPasteToken(msg: dict[str, Any]) -> None:
    """수동 OAuth 토큰 입력 (방화벽 환경용). ~/.dartlab/oauth_token.json 내용을 받아 저장."""
    global _sessionProvider
    tokenJson = msg.get("tokenJson", "")
    provider = msg.get("provider", "oauth-codex")
    if not tokenJson:
        _emit({"event": "error", "data": {"error": "토큰이 비어있습니다."}})
        return
    try:
        data = json.loads(tokenJson)
    except json.JSONDecodeError:
        _emit({"event": "error", "data": {"error": "유효한 JSON이 아닙니다."}})
        return
    if not isinstance(data, dict) or "access_token" not in data:
        _emit({"event": "error", "data": {"error": "access_token이 없습니다."}})
        return
    try:
        from dartlab.ai.providers.support.oauth_token import _save_token

        _save_token(data)
        _sessionProvider = provider
        _emit({"event": "providerChanged", "data": {"provider": provider, "model": ""}})
    except Exception as exc:  # noqa: BLE001
        _emit({"event": "error", "data": {"error": f"토큰 저장 실패: {exc}"}})


def _handleOAuthPasteCode(msg: dict[str, Any]) -> None:
    """방화벽 환경: 사용자가 callback URL 또는 code를 붙여넣음."""
    from urllib.parse import parse_qs, urlparse

    global _sessionProvider
    raw = msg.get("codeOrUrl", "").strip()
    verifier = msg.get("verifier", "")
    expected_state = msg.get("state", "")
    provider = msg.get("provider", "oauth-codex")

    if not raw:
        _emit({"event": "error", "data": {"error": "코드가 비어있습니다."}})
        return
    if not verifier:
        _emit({"event": "error", "data": {"error": "verifier가 없습니다. 로그인을 다시 시작하세요."}})
        return

    # URL이면 code/state 추출
    code = raw
    if raw.startswith("http"):
        params = parse_qs(urlparse(raw).query)
        code = (params.get("code") or [None])[0]  # type: ignore[assignment]
        pasted_state = (params.get("state") or [None])[0]
        if not code:
            _emit({"event": "error", "data": {"error": "URL에서 code를 찾을 수 없습니다."}})
            return
        if expected_state and pasted_state != expected_state:
            _emit({"event": "error", "data": {"error": "state 불일치 (보안 검증 실패). 로그인을 다시 시작하세요."}})
            return

    try:
        from dartlab.ai.providers.support.oauth_token import exchange_code

        exchange_code(code, verifier)
        _sessionProvider = provider
        _emit({"event": "providerChanged", "data": {"provider": provider, "model": ""}})
    except Exception as exc:  # noqa: BLE001
        _emit({"event": "error", "data": {"error": f"토큰 교환 실패: {exc}"}})


def _sanitizeErrorForUi(data: dict[str, Any]) -> dict[str, Any]:
    """에러 데이터에서 CLI 전용 안내(dartlab.setup(...))를 제거."""
    result = dict(data)
    for key in ("error", "guide"):
        if key in result and isinstance(result[key], str):
            result[key] = _CLI_SETUP_PATTERN.sub("", result[key]).strip()
    action = result.get("action", "")
    if action in ("relogin", "config", "login"):
        result["switchProvider"] = True
    return result


def _handleOAuthLogin(msg: dict[str, Any]) -> None:
    """OAuth 브라우저 로그인. callback 서버 + auth URL emit."""
    import threading
    from http.server import BaseHTTPRequestHandler, HTTPServer
    from urllib.parse import parse_qs, urlparse

    provider = msg.get("provider", "oauth-codex")
    try:
        from dartlab.ai.providers.support.oauth_token import (
            OAUTH_REDIRECT_PORT,
            build_auth_url,
            exchange_code,
        )
    except ImportError:
        _emit({"event": "oauthResult", "data": {"success": False, "error": "OAuth 모듈 없음"}})
        return

    auth_url, verifier, state = build_auth_url()
    result: dict[str, Any] = {"done": False, "error": None}

    class _Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            parsed = urlparse(self.path)
            if parsed.path != "/auth/callback":
                self.send_response(404)
                self.end_headers()
                return
            params = parse_qs(parsed.query)
            code = (params.get("code") or [None])[0]
            cb_state = (params.get("state") or [None])[0]
            error = (params.get("error") or [None])[0]
            if error:
                result["error"] = error
            elif cb_state != state:
                result["error"] = "state_mismatch"
            elif not code:
                result["error"] = "no_code"
            else:
                try:
                    exchange_code(code, verifier)
                except (ConnectionError, OSError, RuntimeError, ValueError) as exc:
                    result["error"] = str(exc)
            result["done"] = True
            title = "인증 실패" if result["error"] else "인증 성공"
            body = result["error"] or "DartLab 인증 완료. 이 창을 닫으세요."
            markup = (
                f"<!DOCTYPE html><html><head><meta charset='utf-8'><title>{title}</title>"
                "<style>body{font-family:system-ui;display:flex;align-items:center;"
                "justify-content:center;min-height:100vh;margin:0;background:#050811;color:#e5e5e5}"
                "</style></head><body>"
                f"<div><h1>{title}</h1><p>{body}</p></div>"
                "<script>setTimeout(()=>window.close(),3000)</script>"
                "</body></html>"
            )
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(markup.encode("utf-8"))

        def log_message(self, *_args):
            pass

    server = HTTPServer(("127.0.0.1", OAUTH_REDIRECT_PORT), _Handler)
    server.timeout = 120

    def _serve():
        server.handle_request()
        server.server_close()

    thread = threading.Thread(target=_serve, daemon=True)
    thread.start()

    # auth URL + verifier/state를 extension에 보냄
    _emit(
        {
            "event": "oauthStart",
            "data": {
                "authUrl": auth_url,
                "provider": provider,
                "verifier": verifier,
                "state": state,
            },
        }
    )

    def _wait():
        thread.join(timeout=120)
        global _sessionProvider
        if result.get("error"):
            _emit({"event": "oauthResult", "data": {"success": False, "error": result["error"]}})
        elif result["done"]:
            _sessionProvider = provider
            _emit({"event": "providerChanged", "data": {"provider": provider, "model": ""}})
        else:
            _emit({"event": "oauthResult", "data": {"success": False, "error": "시간 초과 (120초)"}})

    threading.Thread(target=_wait, daemon=True).start()


def run() -> None:
    """stdio REPL loop. Exits on stdin EOF or exit message."""
    import io

    import dartlab

    # Force UTF-8 on Windows cp949 environments
    if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    if sys.stdin.encoding and sys.stdin.encoding.lower() not in ("utf-8", "utf8"):
        sys.stdin = io.TextIOWrapper(sys.stdin.buffer, encoding="utf-8", errors="replace")

    dartlab.verbose = False

    _emit({"event": "ready", "data": _buildReadyDiag()})

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue

        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            _emit({"event": "error", "data": {"error": f"Invalid JSON: {line[:100]}"}})
            continue

        msgType = msg.get("type", "")

        if msgType == "ask":
            _handleAsk(msg)
        elif msgType == "warmup":
            _handleWarmup(msg)
        elif msgType == "status":
            _handleStatus(msg)
        elif msgType == "ping":
            _emit({"event": "pong", "data": {}})
        elif msgType == "setProvider":
            _handleSetProvider(msg)
        elif msgType == "oauthLogin":
            _handleOAuthLogin(msg)
        elif msgType == "oauthPasteToken":
            _handleOAuthPasteToken(msg)
        elif msgType == "oauthPasteCode":
            _handleOAuthPasteCode(msg)
        elif msgType == "listTemplates":
            _handleListTemplates(msg)
        elif msgType == "exit":
            break
        else:
            _emit({"event": "error", "data": {"error": f"Unknown type: {msgType}"}})


def _getVersion() -> str:
    try:
        import dartlab

        return dartlab.__version__
    except Exception:  # noqa: BLE001
        return "unknown"


def _buildReadyDiag() -> dict[str, Any]:
    """시작 시 기본 진단 정보 — VSCode 확장에서 상태 표시용."""
    diag: dict[str, Any] = {"version": _getVersion()}
    diag["python"] = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    try:
        from dartlab.ai.settings.profile import get_profile_manager

        profile = get_profile_manager().load()
        diag["aiProvider"] = profile.default_provider or "none"
    except (ImportError, AttributeError, OSError):
        diag["aiProvider"] = "none"
    try:
        from dartlab import config

        diag["dataDir"] = str(config.dataDir)
    except (ImportError, AttributeError):
        pass
    try:
        import os

        diag["dartKey"] = bool(os.environ.get("DART_API_KEY") or os.environ.get("DART_API_KEYS"))
    except Exception:  # noqa: BLE001
        diag["dartKey"] = False
    return diag
