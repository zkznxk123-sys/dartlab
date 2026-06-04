"""Formatting helpers for DartLab user-facing messages.

Capabilities:
    - Formats simple and structured message catalog entries.
    - Builds capability suggestion text from generated capability metadata.

Args:
    Formatting helpers accept catalog keys and template variables.

Returns:
    Plain text messages ready for logging, exceptions, or UI transport.

Example:
    >>> formatMessage("download:done_short", sizeStr="1MB")
    '✓ 다운로드 완료 (1MB)'

Guide:
    Keep side effects out of this module. Emission belongs to ``dartlab.core.messaging``.

SeeAlso:
    ``messagingCatalog`` and ``messagingContext``.

Requires:
    Static message templates from ``messagingCatalog``.

AIContext:
    Lets server, CLI, and provider code share identical wording without duplicating templates.

LLM Specifications:
    AntiPatterns: Do not log, print, or raise from formatting helpers.
    OutputSchema: ``str`` or ``None`` for suggestions.
    Prerequisites: Key exists in ``SIMPLE`` or ``STRUCTURED`` for ``formatMessage``.
    Freshness: Capability suggestions follow generated capability metadata.
    Dataflow: catalog key -> template expansion -> formatted message.
    TargetMarkets: All DartLab user-facing surfaces.
"""

from __future__ import annotations

from typing import Any

from dartlab.core.messagingCatalog import SIMPLE as _SIMPLE
from dartlab.core.messagingCatalog import STRUCTURED as _STRUCTURED
from dartlab.core.messagingCatalog import StructuredMsg as _StructuredMsg
from dartlab.core.messagingContext import ctx as _ctx


def formatMessage(key: str, **kwargs: Any) -> str:
    """Format a message without emitting it.

    Args:
        key: Message key registered in the simple or structured catalog.
        **kwargs: Template variables such as ``stockCode`` or ``label``.

    Returns:
        Formatted message text.

    Raises:
        ``KeyError`` when ``key`` is not registered or a required template variable is missing.
    Requires:
        key가 ``messagingCatalog.SIMPLE`` 또는 ``STRUCTURED``에 등록되어 있어야 한다.

    Example:
        >>> formatMessage("download:done_short", sizeStr="1MB")
        '✓ 다운로드 완료 (1MB)'
    """
    if key in _STRUCTURED:
        return _formatStructured(_STRUCTURED[key], **kwargs)
    return _formatSimple(key, **kwargs)


def suggest(funcName: str) -> str | None:
    """Return capability guidance for a function or method.

    Capabilities:
        generated capability metadata에서 함수/메서드 요약, capabilities, requires를 찾아
        사람이 읽을 안내 문장으로 조립한다.
    AIContext:
        사용자가 기능명을 잘못 쓰거나 다음 호출법을 물을 때 AI/CLI가 같은 capability
        원장을 참조하게 한다.
    Guide:
        direct key, ``Company.<name>``, ``scan.<name>``, ``gather.<name>`` 순서로 찾는다.
    When:
        메시징 레이어가 함수별 도움말이나 대체 호출 안내를 제안할 때.
    How:
        ``dartlab.reference.capability.loadCapabilities()`` 로 라이브 카탈로그 dict 를 조회한다.

    Args:
        funcName: Name such as ``"valuation"``, ``"Company.BS"``, or ``"scan.governance"``.

    Returns:
        Guidance text, or ``None`` when no generated capability entry matches.

    Raises:
        No public exception; missing generated capability module returns ``None``.
    Requires:
        생성된 capability 모듈이 있으면 사용한다. 없으면 ``None``을 반환한다.

    Example:
        >>> suggest("__missing__") is None
        True
    SeeAlso:
        dartlab.reference.capability.loadCapabilities: 라이브 capability 카탈로그 source.
        formatMessage: catalog message formatting.
    """
    try:
        from dartlab.reference.capability import loadCapabilities

        capabilities = loadCapabilities()
    except ImportError:
        return None

    entry = capabilities.get(funcName)
    if entry is None:
        entry = capabilities.get(f"Company.{funcName}")
    if entry is None:
        for prefix in ("scan.", "gather."):
            entry = capabilities.get(f"{prefix}{funcName}")
            if entry:
                break
    if entry is None:
        return None

    lines = [f"[{funcName}] {entry.get('summary', '')}"]

    capText = entry.get("capabilities")
    if capText:
        lines.append("")
        for item in capText.split("\n"):
            item = item.strip()
            if item:
                lines.append(f"  - {item}")

    reqText = entry.get("requires")
    if reqText:
        lines.append(f"\n  필요: {reqText}")

    return "\n".join(lines)


def _formatSimple(key: str, **kwargs: Any) -> str:
    return _SIMPLE[key].format(**kwargs)


def _formatStructured(msg: _StructuredMsg, **kwargs: Any) -> str:
    lines = [msg.template.format(**kwargs)]

    actions: list[str] = list(msg.actions)
    if msg.actionsWithKey or msg.actionsWithoutKey:
        if _ctx.hasDartKey:
            actions.extend(msg.actionsWithKey)
        else:
            actions.extend(msg.actionsWithoutKey)

    if actions:
        lines.append("")
        for action in actions:
            lines.append(f"  • {action.format(**kwargs)}")

    return "\n".join(lines)


__all__ = ["formatMessage", "suggest"]
