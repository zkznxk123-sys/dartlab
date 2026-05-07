"""Read tool for Skill OS resources and allowed local text files."""

from __future__ import annotations

from pathlib import Path

from dartlab.ai.contracts import Ref

from .formatting import short_text
from .types import ToolResult


def read(target: str, *, startLine: int | None = None, endLine: int | None = None) -> ToolResult:
    target = str(target or "").strip()
    if not target:
        return ToolResult(False, "읽을 target이 비어 있습니다.", error="missing_target")
    if target.startswith("dartlab://skills/"):
        return _read_skill(target.replace("dartlab://skills/", "", 1))
    if target.startswith("skill:"):
        return _read_skill(target.replace("skill:", "", 1))
    if target.startswith("dartlab://"):
        return ToolResult(False, f"지원하지 않는 resource: {target}", error="unsupported_resource")
    return _read_file(target, startLine=startLine, endLine=endLine)


def _read_skill(skill_id: str) -> ToolResult:
    from dartlab.skills import describeSkill

    try:
        payload = describeSkill(skill_id)
    except KeyError as exc:
        return ToolResult(False, f"skill을 찾지 못했습니다: {skill_id}", error="skill_not_found")
    # Skill OS 본문은 dartlab 프로젝트 산출물이므로 internal.
    ref = Ref(
        id=f"doc:skill:{skill_id}",
        kind="docRef",
        title=payload.get("title") or skill_id,
        source=f"dartlab://skills/{skill_id}",
        payload=payload,
        sourceType="internal",
    )
    return ToolResult(True, f"{skill_id} skill을 읽었습니다.", refs=[ref], data={"content": payload})


def _read_file(path_text: str, *, startLine: int | None, endLine: int | None) -> ToolResult:
    path = Path(path_text).expanduser()
    if not path.is_absolute():
        path = Path.cwd() / path
    try:
        resolved = path.resolve()
    except OSError as exc:
        return ToolResult(False, f"경로를 해석하지 못했습니다: {path_text}", error=str(exc))
    if not _allowed_path(resolved):
        return ToolResult(False, f"허용되지 않은 경로입니다: {resolved}", error="path_not_allowed")
    if not resolved.exists() or not resolved.is_file():
        return ToolResult(False, f"파일을 찾지 못했습니다: {resolved}", error="file_not_found")
    text = resolved.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    start = max(1, int(startLine or 1))
    end = min(len(lines), int(endLine or min(len(lines), start + 199)))
    snippet = "\n".join(lines[start - 1 : end])
    source_type = _detect_source_type(resolved)
    ref = Ref(
        id=f"doc:file:{resolved.as_posix()}:{start}-{end}",
        kind="docRef",
        title=resolved.name,
        source=str(resolved),
        payload={"path": str(resolved), "startLine": start, "endLine": end, "text": snippet},
        sourceType=source_type,
    )
    return ToolResult(
        True,
        f"{resolved.name} {start}-{end}행을 읽었습니다.",
        refs=[ref],
        data={"text": short_text(snippet, limit=8000)},
    )


def _allowed_path(path: Path) -> bool:
    roots: list[Path] = [Path.cwd().resolve(), Path.home().resolve()]
    return any(path == root or root in path.parents for root in roots)


def _detect_source_type(path: Path) -> str:
    """resolved path 가 dartlab repo (cwd) 안이면 internal, 외부 (사용자 홈 등) 면 external.

    dartlab repo 안의 파일은 프로젝트 산출물이고 reviewer 가 읽은 것 — 신뢰 가능.
    repo 밖 (사용자 홈, ~/Downloads, ~/Documents 등) 의 파일은 출처 불명 — 외부 본문 처리.
    """
    cwd = Path.cwd().resolve()
    if path == cwd or cwd in path.parents:
        return "internal"
    return "external"
