"""Compatibility helpers from the legacy AI runtime core."""

from __future__ import annotations

from typing import Any


def _extract_data_date(company: Any) -> str | None:
    """Company 객체에서 최신 데이터 기준일을 추출한다."""
    try:
        filings = company.filings() if callable(getattr(company, "filings", None)) else None
        if filings is not None and hasattr(filings, "columns") and "date" in filings.columns:
            dates = filings["date"].drop_nulls()
            if len(dates) > 0:
                return str(dates.max())
    except (AttributeError, TypeError, KeyError):
        pass
    return None


def _classify_error(error: Exception) -> dict[str, str]:
    """예외를 사용자 조치 코드로 분류한다."""
    err_type = type(error).__name__
    err_str = str(error)
    err_low = err_str.lower()

    if isinstance(error, FileNotFoundError):
        return {"error": err_str, "action": "install"}
    if isinstance(error, PermissionError):
        return {"error": err_str, "action": "login"}
    if err_type == "ChatGPTOAuthError":
        if any(keyword in err_low for keyword in ("token", "expire", "login")):
            return {"error": "ChatGPT 인증이 만료되었습니다. 다시 로그인해주세요.", "action": "relogin"}
        if any(keyword in err_low for keyword in ("rate", "limit")):
            return {"error": "ChatGPT 요청 한도에 도달했습니다. 잠시 후 다시 시도해주세요.", "action": "rate_limit"}
        return {"error": f"ChatGPT 연결 오류: {err_str}", "action": "relogin"}
    if err_type == "OpenAIError" or "api_key" in err_low:
        return {"error": "AI 설정이 필요합니다. API 키를 확인하거나 다른 provider를 선택해주세요.", "action": "config"}
    if (
        err_type in {"ServerError", "ClientError", "APIError"}
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
    if isinstance(error, (ConnectionError, TimeoutError)):
        return {
            "error": "AI 서버에 연결할 수 없습니다. 네트워크를 확인하거나 잠시 후 다시 시도해주세요.",
            "action": "retry",
        }
    return {"error": err_str, "action": ""}
