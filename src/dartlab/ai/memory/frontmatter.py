"""Skill spec frontmatter 의 status 라인 안전 갱신.

운영자 confirm 통과 후에만 호출. ai/ 안에서 직접 호출하지 말 것 — CLI 가 진입점.
"""

from __future__ import annotations

import re
from pathlib import Path

_VALID_STATUSES = {"unverified", "observed", "auditP", "official", "deprecated"}
_STATUS_LINE_RE = re.compile(r"^(status:\s*)(\S+)\s*$", re.MULTILINE)


def updateStatus(specPath: Path, newStatus: str) -> bool:
    """frontmatter 의 status 라인을 newStatus 로 교체. 성공 시 True."""
    if newStatus not in _VALID_STATUSES:
        raise ValueError(f"invalid status: {newStatus!r}")
    if not specPath.exists():
        return False
    text = specPath.read_text(encoding="utf-8")
    new_text, count = _STATUS_LINE_RE.subn(rf"\g<1>{newStatus}", text, count=1)
    if count == 0:
        return False
    specPath.write_text(new_text, encoding="utf-8")
    return True


def readStatus(specPath: Path) -> str | None:
    """readStatus — TODO 한국어 동작 설명."""
    if not specPath.exists():
        return None
    text = specPath.read_text(encoding="utf-8")
    m = _STATUS_LINE_RE.search(text)
    return m.group(2) if m else None
