"""Analysis Calc Selector 공통 헬퍼.

모든 act selector가 사용하는 패턴:
1. _safeCalc(fn, company, basePeriod) → dict | None
2. _calcToContextPart(key, data, priority) → ContextPart | None
3. _resolveBase(company) → basePeriod string

레지스트리 패턴(review/registry.py::buildBlocks)을 참고하되,
selector는 Block이 아닌 ContextPart를 반환한다.
"""

from __future__ import annotations

import logging
from typing import Any, Callable

from dartlab.ai.context.bundle import ContextPart, PartPriority
from dartlab.ai.context.encoder import encodeAuto, estimateTokens

log = logging.getLogger(__name__)

# calc 실패 시 잡아야 하는 예외 — registry.py 패턴 동일
_SAFE_EXCEPTIONS = (
    KeyError,
    TypeError,
    ValueError,
    IndexError,
    AttributeError,
    ZeroDivisionError,
    FileNotFoundError,
    OSError,
    RuntimeError,
    ArithmeticError,
    StopIteration,
    ImportError,
)


def _safeCalc(fn: Callable, *args: Any, **kwargs: Any) -> dict | list | None:
    """calc 함수 안전 호출 — None/에러 시 None."""
    try:
        return fn(*args, **kwargs)
    except _SAFE_EXCEPTIONS:
        return None


def _resolveBase(company: Any) -> str | None:
    """Company에서 basePeriod 해석. 실패 시 None (calc이 자동 결정)."""
    try:
        from dartlab.analysis.financial._helpers import resolveBasePeriod

        pr = resolveBasePeriod(company, None, maxYears=5, maxQuarters=8)
        return pr.basePeriod if pr else None
    except _SAFE_EXCEPTIONS + (Exception,):
        return None


def _calcToContextPart(
    key: str,
    data: dict | list | None,
    priority: PartPriority = PartPriority.HIGH,
    *,
    label: str = "",
    source: str = "",
    company: Any = None,
) -> ContextPart | None:
    """calc 결과(dict/list) → AI 맥락 보강 → TOON 인코딩 → ContextPart. None이면 None."""
    if data is None:
        return None

    # AI 맥락 보강 — 5년 평균, YoY 판단, 핵심 요약 자동 추가
    from dartlab.ai.context.aiview import autoEnrich

    enriched = autoEnrich(data, company=company)

    # _summary가 있으면 헤더에 포함 (AI가 바로 해석 가능)
    summary_line = ""
    if isinstance(enriched, dict) and "_summary" in enriched:
        summary_line = enriched.pop("_summary") + "\n"

    # history 키가 있으면 그것만 추출 (가장 유용한 시계열)
    if isinstance(enriched, dict) and "history" in enriched:
        rows = enriched["history"]
        if isinstance(rows, list) and rows:
            text_body = encodeAuto(rows)
        else:
            text_body = encodeAuto(enriched)
    else:
        text_body = encodeAuto(enriched)

    if not text_body or len(text_body) < 5:
        return None

    header = f"## {label}\n" if label else ""
    text = f'<context source="calc:verified" calc="{source}">\n{header}{summary_line}{text_body}\n</context>'
    tokens = estimateTokens(text)

    return ContextPart(
        key=key,
        text=text,
        priority=priority,
        estimatedTokens=tokens,
        source=source or key,
    )


def _buildParts(
    company: Any,
    calcs: list[tuple[str, str, Callable, PartPriority]],
    basePeriod: str | None = None,
) -> list[ContextPart]:
    """여러 calc를 한꺼번에 실행하여 ContextPart 리스트로.

    calcs: [(key, label, calc_fn, priority), ...]
    """
    parts: list[ContextPart] = []
    bp = basePeriod or _resolveBase(company)
    for key, label, fn, prio in calcs:
        result = _safeCalc(fn, company, basePeriod=bp) if bp else _safeCalc(fn, company)
        part = _calcToContextPart(key, result, prio, label=label, source=f"calc:{key}", company=company)
        if part is not None:
            parts.append(part)
    return parts
