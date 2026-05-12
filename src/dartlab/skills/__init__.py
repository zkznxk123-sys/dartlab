"""DartLab skills runtime.

This package owns both the SkillSpec source files and the public runtime API.
MCP, Workbench, Web UI, notebooks, and audits should use this module instead
of maintaining separate skill resolvers.
"""

from __future__ import annotations

from .models import EvidenceCheckResult, SkillCategory, SkillMatch, SkillSpec
from .registry import checkEvidence, describeSkill, getSkill, lintSkill, listSkills, searchSkills

__all__ = [
    "SkillSpec",
    "SkillCategory",
    "SkillMatch",
    "EvidenceCheckResult",
    "list",
    "search",
    "get",
    "describe",
    "checkEvidence",
    "listSkills",
    "searchSkills",
    "getSkill",
    "describeSkill",
    "lintSkill",
]


def list(*, includeUser: bool = True) -> list[SkillSpec]:  # noqa: A001 - public API name
    """공유 SkillSpec 목록 반환."""

    return listSkills(includeUser=includeUser)


def search(query: str, *, limit: int = 8, includeUser: bool = True) -> list[SkillMatch]:
    """공유 SkillSpec 검색."""

    return searchSkills(query, limit=limit, includeUser=includeUser)


def get(skillId: str, *, includeUser: bool = True) -> SkillSpec:
    """id로 SkillSpec 조회."""

    return getSkill(skillId, includeUser=includeUser)


def describe(skillId: str, *, includeUser: bool = True) -> dict:
    """SkillSpec 설명 dict 반환."""

    return describeSkill(skillId, includeUser=includeUser)
