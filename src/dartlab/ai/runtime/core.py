"""AI runtime compatibility shim.

Production Ask execution is owned by `dartlab.ai.kernel.runAsk`.  This module
keeps older imports working without running a second workspace-agent loop.
"""

from __future__ import annotations

from typing import Any, Generator

from dartlab.ai.runtime.events import AnalysisEvent


def _extract_data_date(company: Any) -> str | None:
    """Company에서 최신 데이터 기준일을 추출한다."""
    try:
        filings = company.filings() if callable(getattr(company, "filings", None)) else None
        if filings is not None and hasattr(filings, "columns") and "date" in filings.columns:
            dates = filings["date"].drop_nulls()
            if len(dates) > 0:
                return str(dates.max())
    except (AttributeError, TypeError, KeyError):
        pass
    return None


def _classify_error(e: Exception) -> dict[str, str]:
    """예외 → {error: str, action: str} 매핑."""
    err_type = type(e).__name__
    err_str = str(e)
    err_low = err_str.lower()

    if isinstance(e, FileNotFoundError):
        return {"error": err_str, "action": "install"}
    if isinstance(e, PermissionError):
        return {"error": err_str, "action": "login"}
    if err_type == "ChatGPTOAuthError":
        if any(kw in err_low for kw in ("token", "expire", "login")):
            return {"error": "ChatGPT 인증이 만료되었습니다. 다시 로그인해주세요.", "action": "relogin"}
        if any(kw in err_low for kw in ("rate", "limit")):
            return {"error": "ChatGPT 요청 한도에 도달했습니다. 잠시 후 다시 시도해주세요.", "action": "rate_limit"}
        return {"error": f"ChatGPT 연결 오류: {err_str}", "action": "relogin"}
    if err_type == "OpenAIError" or "api_key" in err_low:
        return {"error": "AI 설정이 필요합니다. API 키를 확인하거나 다른 provider를 선택해주세요.", "action": "config"}
    if (
        err_type in ("ServerError", "ClientError", "APIError")
        or "google" in err_type.lower()
        or "genai" in err_type.lower()
    ):
        if "503" in err_str or "unavailable" in err_low or "high demand" in err_low:
            return {"error": "Gemini 서버가 일시적으로 혼잡합니다. 잠시 후 다시 시도해주세요.", "action": "retry"}
        if "429" in err_str or "rate" in err_low or "quota" in err_low or "resource_exhausted" in err_low:
            return {"error": "Gemini 요청 한도에 도달했습니다. 잠시 후 다시 시도해주세요.", "action": "rate_limit"}
        if "401" in err_str or "403" in err_str or "unauthenticated" in err_low or "permission" in err_low:
            return {"error": "Gemini API 키가 유효하지 않습니다. 설정에서 확인해주세요.", "action": "config"}
        if "400" in err_str or "invalid" in err_low:
            return {"error": f"Gemini 요청 오류: {err_str}", "action": ""}
        return {"error": f"Gemini 연결 오류: {err_str}", "action": "retry"}
    if "connection" in err_low and ("refused" in err_low or "11434" in err_low):
        return {"error": "Ollama가 실행 중이지 않습니다. ollama serve로 시작해주세요.", "action": "config"}
    if isinstance(e, (ConnectionError, TimeoutError)):
        return {
            "error": "AI 서버에 연결할 수 없습니다. 네트워크를 확인하거나 잠시 후 다시 시도해주세요.",
            "action": "retry",
        }
    return {"error": err_str, "action": ""}


def _enrich_with_guide(result: dict[str, str], error: Exception | None = None) -> dict[str, str]:
    """에러에 guide 안내 데스크 메시지를 추가."""
    try:
        from dartlab.core.desk import guide

        result["guide"] = guide.handleError(error or RuntimeError(result.get("error", "")), feature="ai")
    except ImportError:
        if result.get("action") in ("config", "install", "login", "relogin"):
            try:
                from dartlab.core.ai.aiSetup import no_provider_message

                result["guide"] = no_provider_message()
            except ImportError:
                pass
    return result


def runAsk(
    question: str,
    *,
    stockCode: str | None = None,
    provider: str | None = None,
    role: str | None = None,
    model: str | None = None,
    api_key: str | None = None,
    base_url: str | None = None,
    history: list | None = None,
    history_messages: list[dict] | None = None,
    conversation_meta: dict | None = None,
    emit_system_prompt: bool = True,
    reflect: bool = False,
    _templateName: str | None = None,
    _templateText: str | None = None,
    **kwargs: Any,
) -> Generator[AnalysisEvent, None, None]:
    """호환용 runAsk — kernel 이벤트를 AnalysisEvent로 그대로 전달한다."""
    from dartlab.ai.kernel import runAsk as kernel_runAsk

    kernel_kwargs = dict(kwargs)
    for key, value in {
        "stockCode": stockCode,
        "provider": provider,
        "role": role,
        "model": model,
        "api_key": api_key,
        "base_url": base_url,
        "history": history,
        "history_messages": history_messages,
        "conversation_meta": conversation_meta,
        "emit_system_prompt": emit_system_prompt,
        "reflect": reflect,
        "_templateName": _templateName,
        "_templateText": _templateText,
    }.items():
        if value is not None:
            kernel_kwargs[key] = value
    try:
        for event in kernel_runAsk(question, **kernel_kwargs):
            yield AnalysisEvent(event.kind, event.data)
    except Exception as exc:  # noqa: BLE001
        yield AnalysisEvent("error", _enrich_with_guide(_classify_error(exc), error=exc))
