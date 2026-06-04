"""User guidance handlers for DartLab messaging.

Capabilities:
    - Builds data, key, company, analysis, and setup guidance messages.

Args:
    Helpers accept domain context such as company objects, service ids, or resource names.

Returns:
    Guidance strings, lists of next steps, or ``None`` when no guidance is needed.

Example:
    >>> missingDataHint("재고자산", recoverCmd="dartlab.collect('005930')")
    "재고자산 데이터 없음 → dartlab.collect('005930')으로 먼저 수집하세요"

Guide:
    Keep these handlers side-effect-light. Prompting is isolated in ``promptKeyIfMissing``.

SeeAlso:
    ``messaging``, ``messagingErrors``, and ``core.providers``.

Requires:
    Key requirement catalog and optional provider registry.

AIContext:
    Centralizes user recovery guidance so CLI, notebook, and server surfaces stay consistent.

LLM Specifications:
    AntiPatterns: Do not add template catalog constants here; use ``messagingCatalog``.
    OutputSchema: Korean guidance strings or step lists.
    Prerequisites: Caller provides domain context.
    Freshness: Provider setup URLs follow ``KEY_REQUIREMENTS`` and provider specs.
    Dataflow: domain state -> handler -> user-facing guidance.
    TargetMarkets: All DartLab user-facing interfaces.
"""

from __future__ import annotations

from typing import Any

from dartlab.core.logger import getLogger
from dartlab.core.messagingCatalog import KEY_REQUIREMENTS as _KEY_REQUIREMENTS

_log = getLogger(__name__)


def missingDataHint(
    resource: str,
    *,
    recoverCmd: str | None = None,
    detail: str | None = None,
) -> str:
    """Create a friendly missing-data hint.

    Args:
        resource: Data resource name such as ``"재고자산"`` or ``"컨센서스"``.
        recoverCmd: Optional command the user can run to recover.
        detail: Optional explanation appended in parentheses.

    Returns:
        Korean missing-data guidance.

    Raises:
        None.

    Example:
        >>> missingDataHint("재고자산", recoverCmd="dartlab.collect('005930')")
        "재고자산 데이터 없음 → dartlab.collect('005930')으로 먼저 수집하세요"
    """
    base = f"{resource} 데이터 없음"
    if recoverCmd:
        base += f" → {recoverCmd}으로 먼저 수집하세요"
    if detail:
        base += f" ({detail})"
    return base


def apiKeyMissingHint(provider: str) -> str:
    """Return provider-specific API key setup guidance.

    Args:
        provider: Provider id such as ``"dart"`` or ``"fred"``.

    Returns:
        Korean provider setup guidance.

    Raises:
        Propagates provider guide import/runtime errors.

    Example:
        >>> isinstance(apiKeyMissingHint("dart"), str)
        True
    """
    from dartlab.core.providers import providerGuide

    return providerGuide(provider)


def onCompanyCreated(company: Any) -> list[str]:
    """Return hints shown after ``Company`` creation.

    Args:
        company: Company-like object exposing availability/freshness attributes.

    Returns:
        List of Korean hints. Empty when no hint is needed.

    Raises:
        None.

    Example:
        >>> onCompanyCreated(type("C", (), {"stockCode": "005930"})())
        []
    """
    hints: list[str] = []

    hasDocs = getattr(company, "_hasDocs", False)
    hasFinance = getattr(company, "_hasFinanceParquet", False)
    hasReport = getattr(company, "_hasReport", False)
    stockCode = getattr(company, "stockCode", "")

    if hasDocs and not hasFinance:
        hints.append(f"finance 데이터를 추가하면 재무비율/분석을 사용할 수 있습니다: dartlab.collect('{stockCode}')")
    if hasDocs and not hasReport:
        hints.append("report 데이터를 추가하면 배당/임원/지배구조 상세를 볼 수 있습니다")

    freshnessResult = getattr(company, "_freshnessResult", None)
    if freshnessResult and hasattr(freshnessResult, "ageInDays"):
        age = freshnessResult.ageInDays
        if age is not None and age > 90:
            hints.append(f"데이터가 {age}일 전 기준입니다. 갱신: c.update() 또는 dartlab collect {stockCode}")

    return hints


def nextSteps(company: Any) -> list[str]:
    """Return suggested next calls after ``Company`` creation.

    Args:
        company: Company-like object exposing data availability attributes.

    Returns:
        List of command snippets.

    Raises:
        None.

    Example:
        >>> steps = nextSteps(type("C", (), {})())
        >>> any("analysis" in s for s in steps)
        True
    """
    hasFinance = getattr(company, "_hasFinanceParquet", False)
    hasDocs = getattr(company, "_hasDocs", False)
    steps: list[str] = []

    if hasFinance:
        steps.append("c.panel('IS' / 'BS' / 'CF')   재무제표")
        steps.append("c.panel('ratios')             재무비율")
    if hasDocs:
        steps.append("c.panel(topic)                공시 원문 조회")
        steps.append("c.sections                   전체 topic × period 지도")
    steps.append("c.analysis('수익성')             14축 분석")
    steps.append("c.story('수익성')               6막 보고서")

    return steps


def onScanRequested(axis: str) -> str | None:
    """Return scan-axis guidance when needed.

    Args:
        axis: Requested scan axis.

    Returns:
        Guidance string or ``None``. Currently no scan guidance is emitted.

    Raises:
        None.

    Example:
        >>> onScanRequested("valuation") is None
        True
    """
    return None


def onAnalysisRequested(axis: str | None = None) -> str | None:
    """Return analysis-axis selection guidance.

    Args:
        axis: Selected analysis axis, or ``None`` when the user has not chosen one.

    Returns:
        Guidance string when ``axis`` is ``None``; otherwise ``None``.

    Raises:
        None.

    Example:
        >>> "분석 축" in onAnalysisRequested()
        True
    """
    if axis is not None:
        return None

    return (
        "분석 축을 선택하세요:\n"
        "  구조: 수익구조, 자금조달, 자산구조, 현금흐름\n"
        "  성과: 수익성, 성장성, 안정성, 효율성\n"
        "  종합: 종합평가, 이익품질, 비용구조\n"
        "  투자: 자본배분, 투자효율\n"
        "  외부: 지배구조, 공시변화, 비교분석\n"
        "  전망: 매출전망, 예측신호\n"
        '  예시: c.analysis("financial", "수익구조")'
    )


def onKeyRequired(service: str) -> str:
    """Return API-key setup guidance for a service.

    Args:
        service: ``"dart"``, ``"fred"``, ``"ecos"``, or provider id.

    Returns:
        Korean setup guidance.

    Raises:
        No public exception; provider registry import errors fall back to generic guidance.

    Example:
        >>> "API 키" in onKeyRequired("dart")
        True
    """
    req = _KEY_REQUIREMENTS.get(service)
    if req:
        return (
            f"\n  {req['label']} API 키가 필요합니다.\n"
            f"  {req['guide']}\n\n"
            f"  1. 키 발급: {req['signupUrl']}\n"
            f"  2. 설정 방법 (택1):\n"
            f"     a) dartlab.setup() → {req['setupCmd']}\n"
            f"     b) .env 파일에 직접 입력: {req['envKey']}=발급받은키\n"
            f"     c) 환경변수 설정: export {req['envKey']}=발급받은키\n"
        )

    try:
        from dartlab.core.providers import _PROVIDERS

        spec = _PROVIDERS.get(service)
        if spec and spec.auth_kind == "api_key" and spec.env_key:
            lines = [
                f"\n  {spec.label} API 키가 필요합니다.",
                f"  {spec.description}",
            ]
            if spec.freeTierHint:
                lines.append(f"  ({spec.freeTierHint})")
            lines.append("")
            if spec.signupUrl:
                lines.append(f"  1. 키 발급: {spec.signupUrl}")
            lines.append("  2. 설정 방법 (택1):")
            lines.append(f'     a) dartlab.setup("{service}") → 대화형 입력')
            lines.append(f"     b) .env 파일에 직접 입력: {spec.env_key}=발급받은키")
            lines.append(f"     c) 환경변수 설정: export {spec.env_key}=발급받은키")
            lines.append("")
            return "\n".join(lines)
    except ImportError:
        pass

    return f"\n  '{service}' 서비스의 API 키가 필요합니다.\n  dartlab.setup()으로 설정하세요.\n"


def promptKeyIfMissing(service: str) -> str | None:
    """Prompt for a missing API key when running interactively.

    Args:
        service: Service or provider id.

    Returns:
        Existing or newly saved key, or ``None`` in non-interactive/cancelled flows.

    Raises:
        No public exception; user cancellation returns ``None``.

    Example:
        >>> promptKeyIfMissing("__missing__") is None
        True
    """
    import os

    req = _KEY_REQUIREMENTS.get(service)
    if req:
        envKey = req["envKey"]
        existing = os.environ.get(envKey)
        if existing:
            return existing
        _log.info(onKeyRequired(service))
        try:
            from dartlab.core.env import promptAndSave

            return promptAndSave(envKey, label=req["label"], guide=req["signupUrl"])
        except (EOFError, KeyboardInterrupt):
            return None

    try:
        from dartlab.core.providers import _PROVIDERS

        spec = _PROVIDERS.get(service)
        if spec and spec.auth_kind == "api_key" and spec.env_key:
            existing = os.environ.get(spec.env_key)
            if existing:
                return existing
            _log.info(onKeyRequired(service))
            try:
                from dartlab.core.env import promptAndSave

                return promptAndSave(spec.env_key, label=spec.label, guide=spec.signupUrl or "")
            except (EOFError, KeyboardInterrupt):
                return None
    except ImportError:
        pass

    return None


__all__ = [
    "apiKeyMissingHint",
    "missingDataHint",
    "nextSteps",
    "onAnalysisRequested",
    "onCompanyCreated",
    "onKeyRequired",
    "onScanRequested",
    "promptKeyIfMissing",
]
