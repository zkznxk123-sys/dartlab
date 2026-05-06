"""propose_skill — HARVEST 가 신규 spec 작성.

src/dartlab/skills/specs/<engine>/<id>.md 에 kind: generated, status: unverified 로 작성.
기존 skill 수정 금지 (curated/observed/auditP/official 보호).
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from dartlab.ai.contracts import Ref

from .types import ToolResult

_SPEC_ROOT = Path(__file__).resolve().parents[3] / "skills" / "specs"
_ID_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9_.-]*$")


def proposeSkill(
    skillId: str,
    title: str,
    purpose: str,
    *,
    category: str = "engines",
    engine: str | None = None,
    whenToUse: list[str] | None = None,
    capabilityRefs: list[str] | None = None,
    datasetRefs: list[str] | None = None,
    toolRefs: list[str] | None = None,
    knowledgeRefs: list[str] | None = None,
    requiredEvidence: list[str] | None = None,
    body: str = "",
    **_extra: Any,  # LLM 이 schema 외 인자 (kind/scope/status 등) 넘겨도 무시
) -> ToolResult:
    sid = (skillId or "").strip()
    if not sid or not _ID_RE.match(sid.replace(".", "")):
        return ToolResult(False, "skillId 형식 오류", error="invalid_id")

    parts = sid.split(".")
    if len(parts) < 3 or parts[0] != "engines":
        return ToolResult(False, "skillId 는 'engines.<engine>.<name>' 형태여야 함", error="invalid_id_shape")

    inferred_engine = engine or parts[1]
    target_dir = _SPEC_ROOT / "engines" / inferred_engine
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / f"{parts[-1]}.md"

    if target.exists():
        return ToolResult(
            False,
            f"이미 존재 — 기존 spec 수정 금지: {target.relative_to(_SPEC_ROOT.parent)}",
            error="spec_exists",
        )

    frontmatter = _buildFrontmatter(
        sid=sid,
        title=title or sid,
        purpose=purpose or "",
        category=category,
        whenToUse=whenToUse or [],
        capabilityRefs=capabilityRefs or [],
        datasetRefs=datasetRefs or [],
        toolRefs=toolRefs or [],
        knowledgeRefs=knowledgeRefs or [],
        requiredEvidence=requiredEvidence or [],
    )
    content = frontmatter + "\n" + (body or "").strip() + "\n"

    try:
        target.write_text(content, encoding="utf-8")
    except OSError as exc:
        return ToolResult(False, f"propose_skill 저장 실패: {exc}", error="write_failed")

    # P3 wiring: skill registry 재빌드 트리거 (실패해도 spec 작성 자체는 성공으로 처리)
    rebuild_status = "skipped"
    try:
        from dartlab.skills.compiler import buildSkillArtifacts

        buildSkillArtifacts()
        rebuild_status = "ok"
    except Exception as exc:  # noqa: BLE001
        rebuild_status = f"failed:{type(exc).__name__}"

    refs = [
        Ref(
            id=f"skillProposal:{sid}",
            kind="skillRef",
            title=title or sid,
            source=str(target),
            payload={
                "skillId": sid,
                "kind": "generated",
                "status": "unverified",
                "path": str(target),
                "rebuild": rebuild_status,
            },
        )
    ]
    return ToolResult(
        True,
        f"신규 skill spec 작성: {sid} (status: unverified, rebuild={rebuild_status})",
        refs=refs,
        data={"path": str(target), "skillId": sid, "rebuild": rebuild_status},
    )


def _yamlList(items: list[Any]) -> str:
    if not items:
        return "[]"
    return "[" + ", ".join(f'"{str(x).replace(chr(34), chr(39))}"' for x in items) + "]"


def _buildFrontmatter(
    *,
    sid: str,
    title: str,
    purpose: str,
    category: str,
    whenToUse: list[str],
    capabilityRefs: list[str],
    datasetRefs: list[str],
    toolRefs: list[str],
    knowledgeRefs: list[str],
    requiredEvidence: list[str],
) -> str:
    lines = [
        "---",
        f"id: {sid}",
        f'title: "{title}"',
        "kind: generated",
        "scope: builtin",
        "status: unverified",
        f"category: {category}",
        f'purpose: "{purpose}"',
        f"whenToUse: {_yamlList(whenToUse)}",
        f"capabilityRefs: {_yamlList(capabilityRefs)}",
        f"datasetRefs: {_yamlList(datasetRefs)}",
        f"toolRefs: {_yamlList(toolRefs)}",
        f"knowledgeRefs: {_yamlList(knowledgeRefs)}",
        f"requiredEvidence: {_yamlList(requiredEvidence)}",
        "---",
    ]
    return "\n".join(lines)
