"""(deprecated) review 프리셋 → reportTypes.py로 통합.

외부 호환용 re-export. 2026-Q3 제거 예정.
"""

from __future__ import annotations

from dartlab.review.reportTypes import REPORT_TYPES


def _toLegacy(rt_key: str) -> dict:
    rt = REPORT_TYPES[rt_key]
    return {
        "sections": list(rt.sectionOrder),
        "detail": rt.detail,
        "description": rt.description,
    }


PRESETS: dict[str, dict] = {
    "executive": _toLegacy("executive"),
    "audit": _toLegacy("audit"),
    "credit": _toLegacy("credit"),
    "growth": _toLegacy("growth"),
    "valuation": _toLegacy("valuation"),
}
