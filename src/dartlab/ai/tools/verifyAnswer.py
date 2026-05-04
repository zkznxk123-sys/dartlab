"""Ref-based final answer verifier."""

from __future__ import annotations

import re

from dartlab.ai.contracts import Ref

from .types import ToolResult

_DATE_RE = re.compile(r"\b(?:20\d{2}|19\d{2})(?:[-.]?\d{1,2})?(?:[-.]?\d{1,2})?\b")
_CODE_SPAN_RE = re.compile(r"`[^`]*`")
_CODE_BLOCK_RE = re.compile(r"```.*?```", re.DOTALL)
_MATERIAL_NUMBER_RE = re.compile(r"\d[\d,.]*(?:\s?(?:조원|억원|원|%|배|건|개|위|Q[1-4]))")
_MATERIAL_DATE_TERMS = ("기준", "최신", "기간", "시점", "as of", "asof", "latest")


def verifyAnswer(answer: str, refs: list[Ref] | list[dict]) -> ToolResult:
    ref_kinds = {_ref_kind(ref) for ref in refs}
    issues: list[str] = []
    text = _strip_code(str(answer or ""))
    if _has_material_number(text) and not ({"valueRef", "tableRef"} & ref_kinds):
        issues.append("unsupported_numeric_claim")
    if _has_material_date(text) and "dateRef" not in ref_kinds:
        issues.append("unsupported_date_claim")
    if _has_material_ranking(text) and "tableRef" not in ref_kinds:
        issues.append("missing_ranking_table_ref")
    ok = not issues
    verify_ref = Ref(
        id="verify:answer",
        kind="verifyRef",
        title="answer verification",
        source="verify_answer",
        payload={"ok": ok, "issues": issues, "refKinds": sorted(ref_kinds)},
    )
    return ToolResult(ok, "검증 통과" if ok else "검증 실패", refs=[verify_ref], data={"ok": ok, "issues": issues})


def _strip_code(text: str) -> str:
    return _CODE_SPAN_RE.sub("", _CODE_BLOCK_RE.sub("", text))


def _has_material_number(text: str) -> bool:
    return bool(_MATERIAL_NUMBER_RE.search(text))


def _has_material_date(text: str) -> bool:
    if not _DATE_RE.search(text):
        return False
    lowered = text.lower()
    return any(term in lowered for term in _MATERIAL_DATE_TERMS)


def _has_material_ranking(text: str) -> bool:
    if not any(term in text for term in ("순위", "상위", "후보", "랭킹")):
        return False
    return "|" in text or bool(_MATERIAL_NUMBER_RE.search(text))


def _ref_kind(ref: Ref | dict) -> str:
    if isinstance(ref, Ref):
        return ref.kind
    return str(ref.get("kind") or "")
