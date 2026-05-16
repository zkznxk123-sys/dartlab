from __future__ import annotations

from pathlib import Path

import pytest

import dartlab.skills as skills
from dartlab.ai.tools.registry import executeTool, listToolNames

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def _isolated_skill_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    from dartlab.skills import registry

    root = tmp_path / "repo"
    (root / "src" / "dartlab").mkdir(parents=True)
    (root / "pyproject.toml").write_text("[project]\nname='tmp'\n", encoding="utf-8")
    monkeypatch.chdir(root)
    registry._LIST_SKILLS_CACHE.clear()
    yield root
    registry._LIST_SKILLS_CACHE.clear()


def test_create_user_skill_writes_local_skill_and_readskill_exposes_trust_tier(_isolated_skill_repo: Path) -> None:
    result = executeTool(
        "CreateUserSkill",
        {
            "title": "L15 local event watch",
            "purpose": "L1.5 원천 데이터로 이벤트 이상 징후를 추적한다.",
            "capabilityRefs": ["Company.show"],
            "toolRefs": ["RunPython"],
            "body": (
                "## 절차\n\n"
                "- `Company.show` 는 `EngineCall` 로 먼저 호출한다.\n"
                "- 여러 표를 합칠 때만 `RunPython fallback` 으로 정리한다.\n"
            ),
            "visualRefs": ["engines.viz.priceChart"],
            "visualGuidance": ["가격 이벤트는 observed price-chart 로만 표시한다."],
        },
    )

    assert result["ok"] is True
    assert result["data"]["id"] == "user.l15-local-event-watch"
    assert result["data"]["trustTier"] == "localUserDraft"
    target = _isolated_skill_repo / ".dartlab" / "skills" / "user.l15-local-event-watch.md"
    assert target.exists()
    assert "src/dartlab/skills/specs" not in result["data"]["path"].replace("\\", "/")

    spec = skills.get("user.l15-local-event-watch")
    assert spec.kind == "user"
    assert spec.scope == "user"
    assert spec.category == "user"
    assert spec.status == "drafted"
    assert spec.toolRefs[:2] == ["EngineCall", "RunPython"]

    read_result = executeTool(
        "ReadSkill",
        {"query": "L15 local event watch", "limit": 5, "includeUser": True},
    )
    rows = read_result["data"]["skills"]
    row = next(item for item in rows if item["id"] == "user.l15-local-event-watch")
    assert row["scope"] == "user"
    assert row["kind"] == "user"
    assert row["status"] == "drafted"
    assert row["trustTier"] == "localUserDraft"

    builtin_only = executeTool(
        "ReadSkill",
        {"query": "user.l15-local-event-watch", "limit": 5, "includeUser": False},
    )
    assert all(item["id"] != "user.l15-local-event-watch" for item in builtin_only["data"]["skills"])


def test_create_user_skill_defaults_body_with_runpython_fallback() -> None:
    result = executeTool(
        "create_user_skill",
        {
            "title": "Default body event pack",
            "purpose": "기본 본문에도 EngineCall 우선과 RunPython fallback 을 넣는다.",
            "capabilityRefs": ["Company.show"],
            "toolRefs": ["RunPython"],
        },
    )

    assert result["ok"] is True
    body = skills.get("user.default-body-event-pack").source["body"]
    assert "EngineCall" in body
    assert "RunPython fallback" in body


def test_create_user_skill_rejects_runpython_without_fallback_phrase() -> None:
    result = executeTool(
        "CreateUserSkill",
        {
            "title": "Bad Python First",
            "purpose": "RunPython 만으로 엔진 데이터를 직접 처리하려는 잘못된 스킬.",
            "toolRefs": ["RunPython"],
            "body": "## 절차\n\n- RunPython 으로 dartlab 데이터를 조회한다.",
        },
    )

    assert result["ok"] is False
    assert result["error"] == "invalid_tool_refs"
    assert "fallback" in result["summary"]


def test_create_user_skill_allows_only_observed_viz_refs() -> None:
    result = executeTool(
        "CreateUserSkill",
        {
            "title": "Unobserved viz reference",
            "purpose": "검증되지 않은 viz skill 을 연결하지 못해야 한다.",
            "visualRefs": ["engines.viz.tableBackedChart"],
        },
    )

    assert result["ok"] is False
    assert result["error"] == "invalid_visual_ref"
    assert "observed" in result["summary"]


def test_create_user_skill_is_registered_as_canonical_tool() -> None:
    names = set(listToolNames())

    assert "CreateUserSkill" in names
    assert executeTool("CreateUserSkill", {"title": "", "purpose": "x"})["error"] == "missing_title"
