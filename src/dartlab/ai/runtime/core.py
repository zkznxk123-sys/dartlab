"""AI 분석 통합 오케스트레이터 — tool calling 기반 순수 스트리밍.

dartlab.ask(), server UI, CLI가 모두 이 코어를 소비한다.
동기 제너레이터로 AnalysisEvent를 생산하며, 소비자가 형식(SSE/텍스트/제너레이터)을 결정.

구조::

    질문 → ContextBuilder → 시스템 프롬프트 조립
         → streamWithTools (LLM tool call ↔ 엔진 실행 루프) → 최종 텍스트
"""

from __future__ import annotations

import dataclasses
import logging
from typing import Any, Generator

log = logging.getLogger(__name__)

from dartlab.ai.runtime.events import AnalysisEvent
from dartlab.ai.runtime.postResponse import runPostResponse
from dartlab.ai.runtime.prompts import buildSystemPromptParts

# ── 데이터 신선도 추출 ────────────────────────────────────


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


# ── 에러 분류 ─────────────────────────────────────────────


def _classify_error(e: Exception) -> dict[str, str]:
    """예외 → {error: str, action: str} 매핑."""
    err_type = type(e).__name__
    err_str = str(e)
    err_low = err_str.lower()

    if isinstance(e, FileNotFoundError):
        return {"error": err_str, "action": "install"}
    if isinstance(e, PermissionError):
        return {"error": err_str, "action": "login"}

    # ChatGPT OAuth
    if err_type == "ChatGPTOAuthError":
        if any(kw in err_low for kw in ("token", "expire", "login")):
            return {"error": "ChatGPT 인증이 만료되었습니다. 다시 로그인해주세요.", "action": "relogin"}
        if any(kw in err_low for kw in ("rate", "limit")):
            return {"error": "ChatGPT 요청 한도에 도달했습니다. 잠시 후 다시 시도해주세요.", "action": "rate_limit"}
        return {"error": f"ChatGPT 연결 오류: {err_str}", "action": "relogin"}

    # OpenAI
    if err_type == "OpenAIError" or "api_key" in err_low:
        return {"error": "AI 설정이 필요합니다. API 키를 확인하거나 다른 provider를 선택해주세요.", "action": "config"}

    # Google Gemini 에러
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

    # Ollama / 로컬 모델
    if "connection" in err_low and ("refused" in err_low or "11434" in err_low):
        return {"error": "Ollama가 실행 중이지 않습니다. ollama serve로 시작해주세요.", "action": "config"}

    # 일반 네트워크/서버 에러
    if isinstance(e, (ConnectionError, TimeoutError)):
        return {
            "error": "AI 서버에 연결할 수 없습니다. 네트워크를 확인하거나 잠시 후 다시 시도해주세요.",
            "action": "retry",
        }

    return {"error": err_str, "action": ""}


def _enrich_with_guide(result: dict[str, str], error: Exception | None = None) -> dict[str, str]:
    """에러에 guide 안내 데스크 메시지를 추가."""
    try:
        from dartlab.guide import guide

        guideMsg = guide.handleError(
            error or RuntimeError(result.get("error", "")),
            feature="ai",
        )
        result["guide"] = guideMsg
    except ImportError:
        if result.get("action") in ("config", "install", "login", "relogin"):
            try:
                from dartlab.guide.aiSetup import no_provider_message

                result["guide"] = no_provider_message()
            except ImportError:
                pass
    return result


# ── Config 해석 ──────────────────────────────────────────


def _resolveAnalysisConfig(
    provider: str | None,
    role: str | None,
    model: str | None,
    api_key: str | None,
    base_url: str | None,
    **kwargs: Any,
) -> Any:
    """Config 해석 — free provider chain, get_config, merge overrides."""
    from dartlab.ai import get_config

    config_ = get_config(role=role)

    # LLMConfig 필드만 통과 — deprecated 파라미터(use_tools 등)가 kwargs로
    # 흘러들어와도 LLMConfig.merge()에 전달되지 않도록 필터링
    _LLMCONFIG_FIELDS = frozenset(f.name for f in dataclasses.fields(config_))
    llm_kwargs = {k: v for k, v in kwargs.items() if k in _LLMCONFIG_FIELDS}

    overrides = {
        k: v
        for k, v in {
            "provider": provider,
            "model": model,
            "api_key": api_key,
            "base_url": base_url,
            **llm_kwargs,
        }.items()
        if v is not None
    }
    if overrides:
        config_ = config_.merge(overrides)

    return config_


# ── 대화 상태 빌드 (history만 유지) ─────────────────────────


def _buildHistoryMessages(
    history: list | None,
    history_messages: list[dict] | None,
) -> list[dict] | None:
    """히스토리 messages 자동 빌드."""
    if history_messages is not None:
        return history_messages

    if history is None:
        return None

    from dartlab.ai.conversation.history import build_history_messages, compress_history
    from dartlab.ai.types import history_from_dicts

    light_history = history_from_dicts(history)
    compressed = compress_history(light_history)
    return build_history_messages(compressed)


# 시스템 프롬프트 조립 + 범주 블록 → runtime/prompts.py
# post-response 훅 → runtime/postResponse.py


# ── 통합 오케스트레이터 ──────────────────────────────────


def runAsk(
    question: str,
    *,
    # LLM 설정
    provider: str | None = None,
    role: str | None = None,
    model: str | None = None,
    api_key: str | None = None,
    base_url: str | None = None,
    # UI/서버가 현재 화면의 종목코드를 힌트로 전달 (선택)
    stockCode: str | None = None,
    # 대화/히스토리
    history: list | None = None,
    history_messages: list[dict] | None = None,
    conversation_meta: dict | None = None,
    emit_system_prompt: bool = True,
    reflect: bool = False,
    # 템플릿
    _templateName: str | None = None,
    _templateText: str | None = None,
    # 추가 LLMConfig overrides (kwargs 로 흡수)
    **kwargs: Any,
) -> Generator[AnalysisEvent, None, None]:
    """AI 분석 이벤트 스트림. AI 가 모든 엔진을 tool 로 자율 호출 (src/dartlab/ai/README.md)."""
    _logFile = None
    try:
        from dartlab import config as _cfg

        if getattr(_cfg, "askLog", False):
            import datetime
            import json
            from pathlib import Path

            logDir = Path(_cfg.dataDir) / "ask_logs"
            logDir.mkdir(parents=True, exist_ok=True)
            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            _logPath = logDir / f"{ts}_{stockCode or 'none'}.jsonl"
            _logFile = open(_logPath, "w", encoding="utf-8")  # noqa: SIM115
            _logFile.write(json.dumps({"kind": "question", "data": {"question": question}}, ensure_ascii=False) + "\n")
    except (ImportError, OSError):
        _logFile = None

    def _emit(event: AnalysisEvent) -> AnalysisEvent:
        if _logFile is not None:
            import json

            try:
                _logFile.write(
                    json.dumps({"kind": event.kind, "data": event.data}, ensure_ascii=False, default=str) + "\n"
                )
                _logFile.flush()
            except (OSError, TypeError):
                pass
        return event

    try:
        full_response_parts: list[str] = []
        done_payload: dict[str, Any] = {}

        try:
            for ev in _runAskInner(
                question,
                provider=provider,
                role=role,
                model=model,
                api_key=api_key,
                base_url=base_url,
                stockCode=stockCode,
                history=history,
                history_messages=history_messages,
                conversation_meta=conversation_meta,
                emit_system_prompt=emit_system_prompt,
                _full_response_parts=full_response_parts,
                _templateName=_templateName,
                _templateText=_templateText,
                **kwargs,
            ):
                yield _emit(ev)
        except Exception as e:  # noqa: BLE001 — top-level error boundary for the entire AI pipeline (LLM network/auth/parse/provider errors are unpredictable)
            yield _emit(AnalysisEvent("error", _enrich_with_guide(_classify_error(e), error=e)))

        # ── 후처리: plugin hints ──
        if question:
            from dartlab.ai.runtime.plugin_hints import (
                detect_plugin_hints,
                format_plugin_hints,
            )
            from dartlab.core.plugins import get_loaded_plugins

            loaded_names = [p.name for p in get_loaded_plugins()]
            hints = detect_plugin_hints(question, loaded_names)
            if hints:
                done_payload["pluginHints"] = hints
                hint_text = format_plugin_hints(hints)
                if hint_text:
                    done_payload["pluginHintsText"] = hint_text

        # ── Done 이벤트 ──
        yield _emit(AnalysisEvent("done", done_payload))
    finally:
        if _logFile is not None:
            _logFile.close()


def _runAskInner(
    question: str,
    *,
    provider: str | None,
    role: str | None,
    model: str | None,
    api_key: str | None,
    base_url: str | None,
    stockCode: str | None = None,
    history: list | None,
    history_messages: list[dict] | None,
    conversation_meta: dict | None,
    emit_system_prompt: bool,
    _full_response_parts: list[str],
    _templateName: str | None = None,
    _templateText: str | None = None,
    **kwargs: Any,
) -> Generator[AnalysisEvent, None, None]:
    """runAsk() 본체 — tool calling 단일 경로.

    사상 (src/dartlab/ai/README.md): AI 가 모든 엔진을 tool 로 자율 호출. 종목 감지 · 원본 검증 · override 전부 AI 판단.
    사용자 API 에 Company 파라미터 노출 안 함. Pre-grounding · ContextBuilder 떠먹이기 전부 제거.
    """
    config_ = _resolveAnalysisConfig(provider, role, model, api_key, base_url, **kwargs)

    corp_name: str | None = None
    company: Any | None = None
    if stockCode:
        try:
            import dartlab as _dl

            company = _dl.Company(stockCode)
            corp_name = getattr(company, "corpName", None)
        except (ImportError, AttributeError, ValueError, RuntimeError):
            company = None

    meta = conversation_meta or {}
    if corp_name:
        meta.setdefault("company", corp_name)
    if stockCode:
        meta.setdefault("stockCode", stockCode)
    if company is not None:
        _dataDate = _extract_data_date(company)
        if _dataDate:
            meta.setdefault("dataDate", _dataDate)
    yield AnalysisEvent("meta", meta)

    from dartlab.ai.providers import create_provider

    llm = create_provider(config_)

    company_market = getattr(company, "market", "KR") if company else "KR"
    if _templateText is None and _templateName:
        from dartlab.ai.patterns import get_template

        _templateText = get_template(_templateName)

    # category + intent 산출 — 시스템 프롬프트와 toolLoop 가드 모두에 전달
    from dartlab.ai.context.intent import classifyCategory, classifyIntent

    category = classifyCategory(question, stockCode=stockCode).value
    intent = classifyIntent(question, hasCompany=company is not None).intent.value

    static_prompt, dynamic_prompt = buildSystemPromptParts(
        config_,
        question=question,
        category=category,
        intent=intent,
        market=company_market,
        hasCompany=company is not None,
        stockCode=stockCode,
        corpName=corp_name,
        templateText=_templateText,
    )

    if llm.supports_cache_control and static_prompt:
        system_content: str | list[dict] = [
            {"type": "text", "text": static_prompt, "cache_control": {"type": "ephemeral"}},
        ]
        if dynamic_prompt:
            system_content.append({"type": "text", "text": dynamic_prompt})
    else:
        system_content = static_prompt + dynamic_prompt

    system_prompt = static_prompt + dynamic_prompt

    if emit_system_prompt:
        yield AnalysisEvent("system_prompt", {"text": system_prompt})

    messages: list[dict] = [{"role": "system", "content": system_content}]

    effective_history = _buildHistoryMessages(history, history_messages)
    if effective_history:
        messages.extend(effective_history)

    # user 메시지 — 떠먹이기 없이 질문만 (+ stockCode 힌트 있으면 표시)
    userParts: list[str] = []
    if corp_name and stockCode:
        userParts.append(f"분석 대상: {corp_name} (종목코드: {stockCode})")
    userParts.append(f"질문: {question}")
    messages.append({"role": "user", "content": "\n\n---\n\n".join(userParts)})

    # ── 4. LLM tool calling 루프 (Claude Code 방식) ──
    # legacy exec 루프 대체 — 스키마 enum 으로 KeyError 구조적 제거.
    from dartlab.ai.runtime.toolLoop import streamWithTools

    for item in streamWithTools(llm, messages, category=category):
        if isinstance(item, AnalysisEvent):
            yield item
        else:
            _full_response_parts.append(item)
            yield AnalysisEvent("chunk", {"text": item})

    # ── post-response 학습 훅 (3 훅 통합: runtime/postResponse.py) ──
    if _full_response_parts:
        runPostResponse(
            question=question,
            stockCode=stockCode,
            company=company,
            response_text="".join(_full_response_parts),
        )
