"""CreateUserSkill — project-local user skill draft writer."""

from __future__ import annotations

import hashlib
import re
from datetime import date
from pathlib import Path
from typing import Any

import yaml

from dartlab.ai.contracts import Ref

from .types import ToolResult

_ID_RE = re.compile(r"^user\.[a-z0-9][a-z0-9-]{0,62}$")
_SLUG_RE = re.compile(r"[^a-z0-9]+")
_UNTRUSTED_PATTERNS = (
    "ignore previous instructions",
    "ignore all previous",
    "system prompt",
    "developer message",
    "print secret",
    "reveal secret",
    "api key",
    "password",
    "exfiltrate",
)
_ALLOWED_TOOLS = {
    "ReadSkill",
    "GetSkillBody",
    "ReadCapability",
    "EngineCall",
    "RunPython",
    "InspectDataset",
    "Read",
    "WebSearch",
    "SaveArtifact",
    "CompileVisual",
    "EvidenceGate",
    "RunWorkbench",
}


def _slugify(value: str) -> str:
    text = (value or "").strip().lower()
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1-\2", text).lower()
    slug = _SLUG_RE.sub("-", text).strip("-")
    if slug:
        return slug[:63].strip("-") or "skill"
    digest = hashlib.sha1(value.encode("utf-8")).hexdigest()[:8]
    return f"skill-{digest}"


def _normalizeSkillId(raw: str | None, title: str) -> str:
    value = (raw or "").strip()
    if not value:
        return f"user.{_slugify(title)}"
    if value.startswith("user."):
        return f"user.{_slugify(value.removeprefix('user.'))}"
    return f"user.{_slugify(value)}"


def _repoUserSkillRoot() -> Path:
    from dartlab.skills import registry

    return registry._repoRoot() / ".dartlab" / "skills"  # noqa: SLF001 - internal tool uses registry root


def _clearSkillCache() -> None:
    from dartlab.skills import registry

    registry._LIST_SKILLS_CACHE.clear()  # noqa: SLF001 - new local skill must be visible in-session


def _containsUntrustedInstruction(*chunks: str) -> str | None:
    text = "\n".join(chunk or "" for chunk in chunks).lower()
    for pattern in _UNTRUSTED_PATTERNS:
        if pattern in text:
            return pattern
    return None


def _validateVisualRefs(visualRefs: list[str]) -> str | None:
    if not visualRefs:
        return None
    from dartlab.skills import getSkill

    for visual_ref in visualRefs:
        if not visual_ref.startswith("engines.viz."):
            return f"visualRefs 는 engines.viz.* observed skill 만 허용: {visual_ref}"
        try:
            spec = getSkill(visual_ref, includeUser=False)
        except KeyError:
            return f"unknown visualRef: {visual_ref}"
        if spec.status != "observed":
            return f"visualRef 는 observed 여야 함: {visual_ref} status={spec.status}"
    return None


def _normalizeTools(toolRefs: list[str], capabilityRefs: list[str], body: str) -> list[str]:
    tools: list[str] = []
    for tool in toolRefs:
        clean = str(tool or "").strip()
        if clean and clean not in tools:
            tools.append(clean)
    if capabilityRefs and "EngineCall" not in tools:
        tools.insert(0, "EngineCall")
    if "RunPython" in tools and "EngineCall" in tools:
        tools = [tool for tool in tools if tool not in {"EngineCall", "RunPython"}]
        tools.insert(0, "RunPython")
        tools.insert(0, "EngineCall")
    if "RunPython" in tools and body.strip() and "fallback" not in body.lower() and "폴백" not in body:
        raise ValueError(
            "RunPython 을 쓰는 user skill 은 본문에 RunPython fallback 또는 RunPython 폴백을 명시해야 한다"
        )
    unknown = [tool for tool in tools if tool not in _ALLOWED_TOOLS]
    if unknown:
        raise ValueError(f"unknown toolRefs: {', '.join(unknown)}")
    return tools


def _defaultBody(title: str, toolRefs: list[str], capabilityRefs: list[str]) -> str:
    capability_line = (
        "- capabilityRefs 에 있는 DartLab 데이터 호출은 먼저 `EngineCall` 로 실행한다.\n"
        if capabilityRefs
        else "- 필요한 공식 skill 또는 capability 를 `ReadSkill` / `ReadCapability` 로 먼저 확인한다.\n"
    )
    fallback_line = (
        "- 여러 EngineCall 결과를 합치거나 표를 정리해야 할 때만 `RunPython fallback` 을 사용한다.\n"
        if "RunPython" in toolRefs
        else "- 엔진에 이미 있는 계산을 로컬 스킬 본문에서 재구현하지 않는다.\n"
    )
    return (
        "## 절차\n\n"
        f"{capability_line}"
        f"{fallback_line}"
        "- 답변에는 tableRef/valueRef/dateRef/sourceRef 같은 근거 ref 를 남긴다.\n\n"
        "## 검증\n\n"
        "- 데이터가 부족하면 결론을 낮추고 필요한 다음 입력을 말한다.\n"
        "- 로컬 사용자 스킬은 공식 Skill OS 승격 전까지 unverified/drafted 로 취급한다.\n"
        f"\n<!-- localUserSkill: {title.strip()} -->"
    )


def _skillPath(skillId: str, *, incubating: bool) -> Path:
    root = _repoUserSkillRoot()
    filename = f"{skillId}.md"
    return (root / "incubating" / filename) if incubating else (root / filename)


def _writeAndValidate(targetPath: Path, content: str) -> None:
    from dartlab.skills import registry

    temp_path = targetPath.with_name(f".{targetPath.name}.tmp.md")
    try:
        temp_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path.write_text(content, encoding="utf-8")
        spec = registry._loadSpec(temp_path, defaultScope="user", forceUser=True)  # noqa: SLF001
        registry.lintSkill(spec)
        targetPath.parent.mkdir(parents=True, exist_ok=True)
        targetPath.write_text(content, encoding="utf-8")
    finally:
        temp_path.unlink(missing_ok=True)


def createUserSkill(
    title: str,
    *,
    id: str = "",
    purpose: str = "",
    whenToUse: list[str] | None = None,
    body: str = "",
    capabilityRefs: list[str] | None = None,
    toolRefs: list[str] | None = None,
    linkedSkills: list[str] | None = None,
    requiredEvidence: list[str] | None = None,
    expectedOutputs: list[str] | None = None,
    visualRefs: list[str] | None = None,
    visualGuidance: list[str] | None = None,
    incubating: bool = False,
    overwrite: bool = False,
) -> ToolResult:
    """로컬 user skill 초안을 `.dartlab/skills` 아래에 작성한다."""
    clean_title = (title or "").strip()
    if not clean_title:
        return ToolResult(False, "title 이 비어 있다", error="missing_title")
    clean_purpose = (purpose or "").strip()
    if not clean_purpose:
        return ToolResult(False, "purpose 가 비어 있다", error="missing_purpose")

    skill_id = _normalizeSkillId(id, clean_title)
    if not _ID_RE.match(skill_id):
        return ToolResult(False, f"id 는 user.<lowercase-slug> 형식이어야 한다: {skill_id}", error="invalid_id")

    blocked = _containsUntrustedInstruction(clean_title, clean_purpose, body)
    if blocked:
        return ToolResult(False, f"untrusted instruction pattern 차단: {blocked}", error="untrusted_instruction")

    caps = [str(item).strip() for item in capabilityRefs or [] if str(item).strip()]
    visuals = [str(item).strip() for item in visualRefs or [] if str(item).strip()]
    visual_error = _validateVisualRefs(visuals)
    if visual_error:
        return ToolResult(False, visual_error, error="invalid_visual_ref")

    body_text = (body or "").strip()
    try:
        tools = _normalizeTools([str(item) for item in toolRefs or []], caps, body_text)
    except ValueError as exc:
        return ToolResult(False, str(exc), error="invalid_tool_refs")
    if not body_text:
        body_text = _defaultBody(clean_title, tools, caps)

    from dartlab.skills import getSkill

    try:
        builtin = getSkill(skill_id, includeUser=False)
    except KeyError:
        builtin = None
    if builtin is not None:
        return ToolResult(False, f"builtin skill id 와 충돌: {skill_id}", error="builtin_id_collision")

    target_path = _skillPath(skill_id, incubating=bool(incubating))
    if target_path.exists() and not overwrite:
        return ToolResult(False, f"이미 로컬 user skill 이 존재한다: {target_path}", error="user_skill_exists")

    frontmatter: dict[str, Any] = {
        "id": skill_id,
        "title": clean_title,
        "category": "user",
        "kind": "user",
        "scope": "user",
        "status": "drafted",
        "purpose": clean_purpose,
        "whenToUse": list(whenToUse or [clean_title]),
        "runtimeCompatibility": {
            "server": {"status": "supported"},
            "localPython": {"status": "supported"},
            "mcp": {"status": "supported"},
            "webAi": {
                "status": "limited",
                "limitations": ["프로젝트 로컬 .dartlab/skills 를 읽을 수 있는 세션에서만 사용"],
            },
            "pyodide": {
                "status": "unsupported",
                "limitations": ["브라우저 단독 런타임은 로컬 파일 시스템 user skill 을 직접 읽지 않는다"],
            },
        },
        "source": {"type": "local_user_skill", "owner": "user"},
        "lastUpdated": date.today().isoformat(),
    }
    optional_lists = {
        "capabilityRefs": caps,
        "toolRefs": tools,
        "linkedSkills": [str(item).strip() for item in linkedSkills or [] if str(item).strip()],
        "requiredEvidence": [str(item).strip() for item in requiredEvidence or [] if str(item).strip()],
        "expectedOutputs": [str(item).strip() for item in expectedOutputs or [] if str(item).strip()],
        "visualRefs": visuals,
        "visualGuidance": [str(item).strip() for item in visualGuidance or [] if str(item).strip()],
    }
    for key, value in optional_lists.items():
        if value:
            frontmatter[key] = value

    head = yaml.safe_dump(frontmatter, sort_keys=False, allow_unicode=True).strip()
    content = f"---\n{head}\n---\n\n{body_text}\n"

    try:
        _writeAndValidate(target_path, content)
    except Exception as exc:  # noqa: BLE001
        return ToolResult(False, f"user skill 검증 실패: {exc}", error=type(exc).__name__)

    _clearSkillCache()
    ref = Ref(
        id=f"skill:{skill_id}",
        kind="skillRef",
        title=clean_title,
        source=f"dartlab://skills/{skill_id}",
        payload={
            "path": str(target_path),
            "scope": "user",
            "status": "drafted",
            "trustTier": "localUserDraft",
            "officialArtifactSync": False,
        },
    )
    return ToolResult(
        True,
        f"로컬 user skill 작성: {skill_id}",
        refs=[ref],
        data={
            "id": skill_id,
            "path": str(target_path),
            "scope": "user",
            "status": "drafted",
            "trustTier": "localUserDraft",
            "includeUserRequired": True,
        },
    )


__all__ = ["createUserSkill"]
