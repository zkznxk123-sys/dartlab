"""dartlab.{ask,templates,saveTemplate} entry — F6 ai cycle root 우회.

이 모듈은 dartlab/__init__.py 에서 PEP 562 lazy `__getattr__` 으로만 접근.
import dartlab 시점에는 evaluate 되지 않아 dartlab → ai 정적 chain 차단 (정공법 D).

호출 사례:
    dartlab.ask("question")          → __getattr__("ask") → ai 모듈 lazy load
    dartlab.templates()              → __getattr__("templates")
    dartlab.saveTemplate("name", ...)→ __getattr__("saveTemplate")
"""

from __future__ import annotations

from typing import Any


def ask(question: str, **kwargs: Any) -> Any:
    """LLM 에게 dartlab 컨텍스트로 질문 — dartlab.ai.kernel.ask wrapper."""
    from dartlab.ai.kernel import ask as _ask

    if not question or not question.strip():
        print("\n  질문을 입력해 주세요.")
        print("  예: dartlab.ask('삼성전자 재무건전성 분석해줘')\n")
        return None

    stream = kwargs.pop("stream", True)
    raw = kwargs.pop("raw", False)

    if raw:
        return _ask(question, stream=stream, **kwargs)
    if not stream:
        return _ask(question, stream=False, **kwargs)

    gen = _ask(question, stream=True, **kwargs)
    # auto-stream — text consume 후 None 반환
    text_chunks = []
    try:
        for chunk in gen:
            print(chunk, end="", flush=True)
            text_chunks.append(chunk)
        print()
    except Exception:  # noqa: BLE001
        pass
    return "".join(text_chunks) or None


def templates(name: str | None = None) -> Any:
    """분석 템플릿 목록 또는 특정 템플릿 내용."""
    from dartlab.ai import templates as _templates

    return _templates(name)


def saveTemplate(name: str, *, content: str | None = None, file: str | None = None) -> Any:
    """사용자 분석 템플릿 저장."""
    from dartlab.ai import saveTemplate as _save

    return _save(name, content=content, file=file)
