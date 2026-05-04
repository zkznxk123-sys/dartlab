"""Canonical AI tool registry."""

from __future__ import annotations

import inspect
from typing import Any, Callable

from .engineCall import engineCall
from .generatedSpecSearch import generatedSpecSearch
from .read import read
from .runPython import runPython
from .skillSearch import skillSearch
from .types import ToolResult, ToolSpec
from .verifyAnswer import verifyAnswer
from .webSearch import webSearch
from .write import write

ToolFn = Callable[..., ToolResult]

_SPECS: dict[str, ToolSpec] = {
    "read": ToolSpec(
        "read",
        "repo, Skill OS resource, allowed local text file을 읽고 docRef를 만든다.",
        {
            "type": "object",
            "properties": {
                "target": {"type": "string"},
                "startLine": {"type": "integer"},
                "endLine": {"type": "integer"},
            },
            "required": ["target"],
        },
    ),
    "write": ToolSpec(
        "write",
        "artifact/scratchpad-adjacent output을 안전한 사용자 홈 경로에 저장하고 artifactRef를 만든다.",
        {
            "type": "object",
            "properties": {"name": {"type": "string"}, "content": {"type": "string"}, "kind": {"type": "string"}},
            "required": ["name", "content"],
        },
    ),
    "web_search": ToolSpec(
        "web_search",
        "외부 최신 정보가 필요할 때 웹 검색을 실행하고 webRef를 만든다.",
        {
            "type": "object",
            "properties": {"query": {"type": "string"}, "limit": {"type": "integer"}},
            "required": ["query"],
        },
    ),
    "skill_search": ToolSpec(
        "skill_search",
        "Skill OS에서 질문 목적에 맞는 실행 skill을 찾는다.",
        {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "limit": {"type": "integer"},
                "includeUser": {"type": "boolean"},
            },
            "required": ["query"],
        },
    ),
    "generated_spec_search": ToolSpec(
        "generated_spec_search",
        "CAPABILITIES/docstring generated spec에서 호출 가능한 공개 API를 찾는다.",
        {
            "type": "object",
            "properties": {"query": {"type": "string"}, "limit": {"type": "integer"}},
            "required": ["query"],
        },
    ),
    "engine_call": ToolSpec(
        "engine_call",
        "generated spec 기반 call plan을 검증한 뒤 DartLab 공개 API를 호출하고 refs를 만든다.",
        {"type": "object", "properties": {"plan": {"type": "object"}}, "required": ["plan"]},
    ),
    "run_python": ToolSpec(
        "run_python",
        "DartLab library와 Polars를 조합해 계산/랭킹/표 생성 코드를 실행한다.",
        {
            "type": "object",
            "properties": {"code": {"type": "string"}, "runId": {"type": "string"}},
            "required": ["code"],
        },
    ),
    "verify_answer": ToolSpec(
        "verify_answer",
        "최종 답변의 숫자/날짜/랭킹 claim이 refs로 뒷받침되는지 검증한다.",
        {
            "type": "object",
            "properties": {"answer": {"type": "string"}, "refs": {"type": "array"}},
            "required": ["answer", "refs"],
        },
    ),
}

_TOOLS: dict[str, ToolFn] = {
    "read": read,
    "write": write,
    "web_search": webSearch,
    "skill_search": skillSearch,
    "generated_spec_search": generatedSpecSearch,
    "engine_call": engineCall,
    "run_python": runPython,
    "verify_answer": verifyAnswer,
}

CANONICAL_TOOL_NAMES = tuple(_SPECS.keys())


def toolSpecs() -> list[dict[str, Any]]:
    return [spec.to_dict() for spec in _SPECS.values()]


def listToolNames() -> tuple[str, ...]:
    return tuple(_SPECS.keys())


def registerTool(
    name: str,
    func: Callable[..., Any],
    *,
    description: str | None = None,
    inputSchema: dict[str, Any] | None = None,
) -> None:
    if name in CANONICAL_TOOL_NAMES:
        raise ValueError(f"canonical tool은 plugin으로 덮어쓸 수 없습니다: {name}")
    _SPECS[name] = ToolSpec(
        name,
        description or inspect.getdoc(func) or f"{name} plugin tool",
        inputSchema or _schemaFromSignature(func),
    )

    def _wrapped(**kwargs: Any) -> ToolResult:
        try:
            result = func(**kwargs)
        except Exception as exc:  # pragma: no cover - defensive plugin boundary
            return ToolResult(False, f"{name} plugin tool 실패: {exc}", error=type(exc).__name__)
        if isinstance(result, ToolResult):
            return result
        return ToolResult(True, f"{name} plugin tool 실행 완료", data={"result": result})

    _TOOLS[name] = _wrapped


def unregisterTool(name: str) -> None:
    if name in CANONICAL_TOOL_NAMES:
        raise ValueError(f"canonical tool은 해제할 수 없습니다: {name}")
    _SPECS.pop(name, None)
    _TOOLS.pop(name, None)


def executeTool(name: str, args: dict[str, Any] | None = None) -> dict[str, Any]:
    if name not in _TOOLS:
        return ToolResult(False, f"Unknown tool: {name}", error="unknown_tool").to_dict()
    payload = dict(args or {})
    if name == "engine_call":
        result = _TOOLS[name](payload.get("plan") or payload)
    elif name == "verify_answer":
        result = _TOOLS[name](payload.get("answer", ""), payload.get("refs") or [])
    else:
        result = _TOOLS[name](**payload)
    return result.to_dict()


def _schemaFromSignature(func: Callable[..., Any]) -> dict[str, Any]:
    properties: dict[str, dict[str, Any]] = {}
    required: list[str] = []
    for param in inspect.signature(func).parameters.values():
        if param.kind in (param.VAR_POSITIONAL, param.VAR_KEYWORD):
            continue
        properties[param.name] = {"type": _jsonType(param.annotation)}
        if param.default is inspect.Parameter.empty:
            required.append(param.name)
    schema: dict[str, Any] = {"type": "object", "properties": properties}
    if required:
        schema["required"] = required
    return schema


def _jsonType(annotation: Any) -> str:
    if annotation in (int, "int"):
        return "integer"
    if annotation in (float, "float"):
        return "number"
    if annotation in (bool, "bool"):
        return "boolean"
    if annotation in (list, "list"):
        return "array"
    if annotation in (dict, "dict"):
        return "object"
    return "string"
