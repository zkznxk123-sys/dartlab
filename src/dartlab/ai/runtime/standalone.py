"""AI 분석 함수 — `dartlab.ask(question)` 단일 진입점.

사상 (ops/ai.md): AI 가 모든 엔진(analysis/scan/macro/credit/gather/search) 을
tool 로 다룬다. 사용자 API 에 Company 파라미터 · chat · reviewer 전부 노출 안 함.
"""

from __future__ import annotations

from typing import Any, Generator


def _collect_text(events) -> str:
    parts: list[str] = []
    hint_text = ""
    for ev in events:
        if ev.kind == "chunk":
            parts.append(ev.data["text"])
        elif ev.kind == "done":
            hint_text = ev.data.get("pluginHintsText", "")
    answer = "".join(parts)
    if hint_text:
        answer += f"\n\n{hint_text}"
    return answer


def _stream_chunks(events) -> Generator[str, None, None]:
    for ev in events:
        if ev.kind == "chunk":
            yield ev.data["text"]
        elif ev.kind == "done":
            hint = ev.data.get("pluginHintsText")
            if hint:
                yield f"\n\n{hint}"


def ask(
    question: str,
    *,
    stockCode: str | None = None,
    provider: str | None = None,
    model: str | None = None,
    stream: bool = True,
    reflect: bool = False,
    pattern: str | None = None,
    template: str | None = None,
    modules: list[str] | None = None,
    history: list[dict[str, str]] | None = None,
    **kwargs: Any,
) -> str | Generator[str, None, None]:
    """AI 에게 질문. AI 가 모든 엔진을 tool 로 자율 호출.

    Args:
        question: 자연어 질문 (한국어/영어). 종목은 질문 안에 적는다.
        stockCode: UI/서버가 현재 화면의 종목코드를 힌트로 전달 (선택).
        stream: True 면 제너레이터 반환 (chunk 단위). False 면 전체 텍스트.
        reflect: True 면 답변 자체 검증 (1회 reflection).
        provider/model: per-call override.
        pattern/template/modules: 분석 템플릿.
        history: 이전 대화 메시지.

    Returns:
        str (stream=False) 또는 Generator[str] (stream=True).
    """
    _templateText = None
    if modules:
        from dartlab.ai.patterns import get_modules

        _templateText = get_modules(modules)
    else:
        tmpl_name = template or pattern
        if tmpl_name:
            from dartlab.ai.patterns import get_template

            _templateText = get_template(tmpl_name)

    from dartlab.ai.runtime.core import analyze

    events = analyze(
        question,
        stockCode=stockCode,
        provider=provider,
        model=model,
        reflect=reflect,
        history=history,
        _templateText=_templateText,
        **kwargs,
    )

    if stream:
        return _stream_chunks(events)

    answer = _collect_text(events)

    if reflect and answer:
        from dartlab.ai import get_config
        from dartlab.ai.providers import create_provider
        from dartlab.ai.runtime.agent import _reflect_on_answer

        config_ = get_config(role=kwargs.get("role"))
        overrides = {k: v for k, v in {"provider": provider, "model": model, **kwargs}.items() if v is not None}
        if overrides:
            config_ = config_.merge(overrides)
        llm = create_provider(config_)
        messages = [{"role": "user", "content": question}]
        answer = _reflect_on_answer(llm, messages, answer)

    return answer
