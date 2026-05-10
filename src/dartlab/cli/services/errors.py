"""CLI error types and user-facing wrapper.

CLI 가 모든 사용자 접점 (cli/commands/*, cli/main) 에서 호출하는 에러 변환기
``wrapError`` 와 feature 추론기 ``inferFeature`` 를 제공한다. 원본 에러 메시지
뒤에 ``core.messaging.handleError`` 가 만든 친절 안내를 덧붙여 반환한다.
"""

from __future__ import annotations

from dartlab.cli.context import EXIT_RUNTIME


class CLIError(RuntimeError):
    """User-facing CLI error with an explicit exit code."""

    def __init__(self, message: str, exitCode: int = EXIT_RUNTIME):
        super().__init__(message)
        self.exitCode = exitCode


def wrapError(error: Exception, *, feature: str | None = None, stockCode: str | None = None) -> str:
    """에러 → 안내 포함 메시지. CLI 의 모든 명령이 try/except 에서 이것만 호출.

    Parameters
    ----------
    error : Exception
        발생한 예외.
    feature : str, optional
        "data", "ai", "finance" 등. None 이면 자동 추론.
    stockCode : str, optional
        관련 종목코드 (있으면 readiness 단계에서 활용).

    Returns
    -------
    str — 원본 에러 메시지 + 친절 안내가 합쳐진 문자열.
    """
    try:
        from dartlab.core.messaging import handleError

        resolvedFeature = feature or inferFeature(error)
        guideMsg = handleError(error, feature=resolvedFeature)
        if guideMsg and guideMsg != f"오류: {error}":
            return f"{error}\n\n{guideMsg}"
    except ImportError:
        pass
    return str(error)


def inferFeature(error: Exception) -> str | None:
    """에러 타입/메시지에서 관련 feature 자동 추론."""
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
