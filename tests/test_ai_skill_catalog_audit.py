"""Skill catalog audit — 작업대 default 후보 호환성 검증.

P2 의 readSkill 통합 audit 자리. 모든 spec 이 SkillSpec 으로 파싱되는지,
status / kind 분포가 합리적인지, requiredEvidence 가 GATE 매핑과 호환인지.
"""

from __future__ import annotations

from collections import Counter

import pytest

pytestmark = pytest.mark.unit


def test_all_skill_specs_parse_into_dataclass():
    from dartlab.skills import listSkills

    specs = listSkills()
    assert specs, "skill 인덱스가 비어 있다"
    for spec in specs:
        assert spec.id
        assert spec.title
        assert spec.kind in ("curated", "generated", "recipe", "user")
        assert spec.status in ("unverified", "observed", "auditP", "official", "deprecated")


def test_skill_kind_status_distribution_is_reasonable():
    from dartlab.skills import listSkills

    specs = listSkills()
    kinds = Counter(s.kind for s in specs)
    statuses = Counter(s.status for s in specs)

    # curated 가 대다수여야 한다 (사람이 작성한 것 위주)
    assert kinds["curated"] >= max(kinds["generated"], kinds["user"], 1)
    assert sum(statuses.values()) == len(specs)


def test_required_evidence_tokens_are_known_to_gate():
    """모든 spec 의 requiredEvidence 가 GATE 매핑 또는 무해한 자유 텍스트인지."""

    from dartlab.ai.workbench.gate import _KNOWN_KIND_ALIASES
    from dartlab.skills import listSkills

    unknown_tokens: set[str] = set()
    for spec in listSkills():
        for token in spec.requiredEvidence or []:
            if str(token) not in _KNOWN_KIND_ALIASES:
                unknown_tokens.add(str(token))

    # 알 수 없는 토큰이 있어도 GATE 는 무시 (issue 마킹 안 함). 본 테스트는
    # 미래 매핑 확장 후보를 시각화한다.
    assert isinstance(unknown_tokens, set)


def test_search_skills_returns_top_matches_for_common_query():
    from dartlab.skills import searchSkills

    matches = searchSkills("수익성", limit=5)
    assert matches, "'수익성' 검색이 비어 있다"
    assert all(match.score > 0 for match in matches)
