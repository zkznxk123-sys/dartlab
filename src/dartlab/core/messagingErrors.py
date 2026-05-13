"""Exception-to-guidance conversion for DartLab messaging.

Capabilities:
    - Infers feature areas from exceptions.
    - Converts common runtime exceptions into user-friendly Korean guidance.

Args:
    Helpers accept exception objects and optional feature hints.

Returns:
    Feature ids or formatted guidance strings.

Example:
    >>> inferFeature(FileNotFoundError("missing"))
    'data'

Guide:
    Keep domain-specific recovery copy in handler modules and route to it from here.

SeeAlso:
    ``messagingHandlers`` and ``messagingShare``.

Requires:
    No external services; optional platform detection for share errors.

AIContext:
    Gives CLI and server a shared error language without importing CLI from server.

LLM Specifications:
    AntiPatterns: Do not raise from this module; return guidance.
    OutputSchema: ``str`` or ``None`` for feature inference.
    Prerequisites: Caller passes the original exception.
    Freshness: Provider-specific error strings should be reviewed when SDKs change.
    Dataflow: exception -> classifier -> guidance text.
    TargetMarkets: CLI, server, notebook, and share flows.
"""

from __future__ import annotations

from dartlab.core.messagingShare import (
    onCloudflaredMissing,
    onCloudflareLoginRequired,
    onTunnelStartFailed,
)


def inferFeature(error: Exception) -> str | None:
    """Infer the related feature from an exception.

    Args:
        error: Original exception.

    Returns:
        Feature id such as ``"ai"``, ``"finance"``, ``"data"``, or ``None``.

    Raises:
        None.

    Example:
        >>> inferFeature(FileNotFoundError("missing"))
        'data'
    """
    errStr = str(error).lower()

    if any(kw in errStr for kw in ("api_key", "apikey", "provider", "oauth", "openai", "gemini", "ollama")):
        return "ai"

    if any(kw in errStr for kw in ("finance", "parquet", "재무", "financial")):
        return "finance"

    if isinstance(error, FileNotFoundError):
        return "data"

    if isinstance(error, (ConnectionError, TimeoutError)):
        return "ai"

    return None


def handleError(error: Exception, *, feature: str | None = None) -> str:
    """Convert an exception to user-friendly guidance.

    Args:
        error: Original exception.
        feature: Optional feature id supplied by caller.

    Returns:
        Korean guidance text.

    Raises:
        None.

    Example:
        >>> "파일을 찾을 수 없습니다" in handleError(FileNotFoundError("x"))
        True
    """
    errType = type(error).__name__
    errStr = str(error)
    errLow = errStr.lower()

    if feature == "share" or "cloudflared" in errLow or "tunnel" in errLow:
        if "cloudflared" in errLow and ("not found" in errLow or "missing" in errLow or "찾을" in errStr):
            import platform

            return onCloudflaredMissing(platform.system())
        if "cert" in errLow or "login" in errLow or "unauthenticated" in errLow:
            return onCloudflareLoginRequired()
        return onTunnelStartFailed(errStr[-500:])

    if isinstance(error, FileNotFoundError):
        return (
            f"파일을 찾을 수 없습니다: {errStr}\n  dartlab.downloadAll() 또는 dartlab.collect()로 데이터를 준비하세요."
        )

    if isinstance(error, PermissionError):
        return f"권한 오류: {errStr}\n  dartlab.setup()으로 인증을 확인하세요."

    if errType == "ChatGPTOAuthError":
        if any(kw in errLow for kw in ("token", "expire", "login")):
            return 'ChatGPT 인증이 만료되었습니다.\n  dartlab.setup("chatgpt")으로 다시 로그인하세요.'
        if any(kw in errLow for kw in ("rate", "limit")):
            return "ChatGPT 요청 한도에 도달했습니다. 잠시 후 다시 시도해주세요."
        return f'ChatGPT 연결 오류: {errStr}\n  dartlab.setup("chatgpt")으로 재인증하세요.'

    if errType == "OpenAIError" or "api_key" in errLow or "apikey" in errLow:
        return "AI 설정이 필요합니다.\n  dartlab.setup()으로 API 키를 확인하거나 다른 provider를 선택하세요."

    if (
        errType in ("ServerError", "ClientError", "APIError")
        or "google" in errType.lower()
        or "genai" in errType.lower()
    ):
        if "503" in errStr or "unavailable" in errLow or "high demand" in errLow:
            return "Gemini 서버가 일시적으로 혼잡합니다. 잠시 후 다시 시도해주세요."
        if "429" in errStr or "rate" in errLow or "quota" in errLow or "resource_exhausted" in errLow:
            return "Gemini 요청 한도에 도달했습니다. 잠시 후 다시 시도해주세요."
        if "401" in errStr or "403" in errStr or "unauthenticated" in errLow or "permission" in errLow:
            return 'Gemini API 키가 유효하지 않습니다.\n  dartlab.setup("gemini")으로 키를 확인하세요.'
        if "400" in errStr or "invalid" in errLow:
            return f"Gemini 요청 오류: {errStr}"
        return f"Gemini 연결 오류: {errStr}\n  잠시 후 다시 시도해주세요."

    if "connection" in errLow and ("refused" in errLow or "11434" in errLow):
        return (
            "Ollama가 실행 중이지 않습니다.\n"
            "  ollama serve로 시작한 뒤 다시 시도하세요.\n"
            '  미설치: dartlab.setup("ollama")'
        )

    if isinstance(error, (ConnectionError, TimeoutError)):
        return (
            "AI 서버에 연결할 수 없습니다.\n"
            "  네트워크를 확인하거나 잠시 후 다시 시도해주세요.\n"
            "  다른 provider 시도: dartlab.setup()"
        )

    if any(kw in errLow for kw in ("context", "token limit", "too long", "max_tokens")):
        return f"입력이 너무 깁니다: {errStr}\n  --exclude 옵션으로 컨텍스트를 줄여보세요."

    if feature:
        return (
            f"[{feature}] {errType}: {errStr}\n"
            f"  dartlab.capabilities(search='{feature}') 로 사용 가능한 기능을 확인하세요."
        )
    return f"{errType}: {errStr}"


__all__ = ["handleError", "inferFeature"]
