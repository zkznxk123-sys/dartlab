"""AI runtime 계약 조회 — capabilities/docstring 뼈대 위의 얇은 검증 메타.

새 planner 나 지식 레이어가 아니다. 공개 API docstring/CAPABILITIES 로 정해진
도구 역할을 runtime 이 검증 가능한 최소 계약으로 읽기 쉽게 만든다.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any

from dartlab.ai.runtime.contract_graph import (
    contractForTool,
    legacyAnswerContractNames,
)


@dataclass(frozen=True)
class ContractIssue:
    code: str
    detail: str = ""


_DATE_KEYS = ("start", "end", "from", "to", "date", "asOf", "asof")
_POLLUTED_KEY_RE = re.compile(r"[\[\]{}]|to=|functions\.|tool_calls|arguments|role=", re.IGNORECASE)


def contractMetadataForTool(name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
    """tool 출력 Evidence Header 에 붙일 capabilities 계약 메타."""
    contract = contractForTool(name, arguments or {})
    return contract.toDict() if contract is not None else {}


def resolveAnswerContracts(question: str | None, toolCalls: list[dict[str, Any]]) -> set[str]:
    """질문과 호출 도구에서 검사해야 할 얇은 계약 이름을 찾는다."""
    return legacyAnswerContractNames(question, toolCalls)


def validateToolArguments(
    *,
    question: str | None,
    toolCalls: list[dict[str, Any]],
    today: date | None = None,
) -> list[ContractIssue]:
    """capabilities 계약에 비춰 명백히 깨진 tool 인자를 검사한다."""
    today = today or date.today()
    issues: list[ContractIssue] = []
    for call in toolCalls:
        name = str(call.get("name", ""))
        args = _callArgs(call)
        if name == "capabilities" and _hasPollutedCapabilitiesKey(args):
            issues.append(ContractIssue("bad_tool_args", "polluted_capabilities_key"))

        dates = {k: _parseDate(args.get(k)) for k in _DATE_KEYS if k in args}
        parsed = {k: v for k, v in dates.items() if v is not None}
        start = parsed.get("start") or parsed.get("from")
        end = parsed.get("end") or parsed.get("to")
        if start and end and start > end:
            issues.append(ContractIssue("bad_tool_args", "date_range_reversed"))
        if any(d > today + timedelta(days=1) for d in parsed.values()):
            issues.append(ContractIssue("bad_tool_args", "future_date"))

        contract = contractForTool(name, args)
        if contract is not None and contract.contractId == "gather.krx.close":
            target = str(args.get("target") or "").lower()
            if target and target not in {"close", "raw"}:
                issues.append(ContractIssue("bad_tool_args", "krx_price_target_not_close"))
    return issues


def sanitizeToolArguments(
    name: str,
    arguments: dict[str, Any] | None,
    *,
    today: date | None = None,
) -> dict[str, Any]:
    """runtime 실행 전 명백히 깨진 tool 인자를 1회 보정한다."""
    today = today or date.today()
    clean = dict(arguments or {})
    if name == "capabilities":
        clean = sanitizeCapabilitiesArgs(clean)
    if name == "gather" and str(clean.get("axis") or "").lower() == "macro":
        target = clean.get("target")
        if isinstance(target, str):
            try:
                from dartlab.gather.ecos.catalog import resolveId

                clean["target"] = resolveId(target) or target
            except Exception:
                pass
        if str(clean.get("target") or "").upper() == "USDKRW":
            clean["market"] = "KR"
    if name == "show" and _looks_like_foreign_ticker(clean.get("stockCode")):
        topic = clean.get("topic")
        if isinstance(topic, str):
            normalized = topic.strip()
            if normalized == "ratioSeries":
                clean["topic"] = "ratios"
            elif normalized.lower() in {"dividend", "dividends", "payout", "shareholder_return"}:
                clean["topic"] = "ratios"
    for key in _DATE_KEYS:
        parsed = _parseDate(clean.get(key))
        if parsed and parsed > today:
            clean[key] = today.isoformat()
    start = _parseDate(clean.get("start") or clean.get("from"))
    end = _parseDate(clean.get("end") or clean.get("to"))
    if start and end and start > end:
        clean["start"] = end.isoformat()
    return clean


def latestDateFromToolArgs(toolCalls: list[dict[str, Any]]) -> date | None:
    """tool 인자에 명시된 날짜 중 가장 최신일."""
    latest: date | None = None
    for call in toolCalls:
        args = _callArgs(call)
        for key in _DATE_KEYS:
            parsed = _parseDate(args.get(key))
            if parsed and (latest is None or parsed > latest):
                latest = parsed
    return latest


def staleCutoff(today: date | None = None) -> date:
    """최근/현재 질문에서 명백히 낡았다고 볼 보수적 기준."""
    return (today or date.today()) - timedelta(days=120)


def _hasPollutedCapabilitiesKey(args: dict[str, Any]) -> bool:
    key = args.get("key")
    if key is None:
        return False
    if not isinstance(key, str):
        return True
    return bool(_POLLUTED_KEY_RE.search(key))


def sanitizeCapabilitiesArgs(args: dict[str, Any]) -> dict[str, Any]:
    """오염된 capabilities key 를 정상 key/search 로 1회 보정한다."""
    clean = dict(args)
    key = clean.get("key")
    if isinstance(key, str) and _POLLUTED_KEY_RE.search(key):
        lowered = key.lower()
        for candidate in ("analysis", "scan", "gather", "macro", "quant", "capabilities"):
            if candidate in lowered:
                clean["key"] = candidate
                return clean
        clean.pop("key", None)
    return clean


def _looks_like_foreign_ticker(value: Any) -> bool:
    text = str(value or "").strip()
    return bool(text) and not text.isdigit()


def _callArgs(call: dict[str, Any]) -> dict[str, Any]:
    args = call.get("arguments") or call.get("args") or {}
    return args if isinstance(args, dict) else {}


def _parseDate(value: Any) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    if not text:
        return None
    match = re.search(r"(20\d{2})[-./년\s]*(\d{1,2})[-./월\s]*(\d{1,2})", text)
    if not match:
        return None
    try:
        return date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
    except ValueError:
        return None
