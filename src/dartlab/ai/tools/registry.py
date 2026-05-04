"""Canonical AI tool registry."""

from __future__ import annotations

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
    return [_SPECS[name].to_dict() for name in CANONICAL_TOOL_NAMES]


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
