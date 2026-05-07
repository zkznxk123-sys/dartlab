"""Canonical AI tool registry."""

from __future__ import annotations

import inspect
from typing import Any, Callable

from .compileVisual import compileVisual
from .engineCall import engineCall
from .generatedSpecSearch import generatedSpecSearch
from .inspectDataset import inspectDataset
from .proposeSkill import proposeSkill
from .read import read
from .readCapability import readCapability
from .readSkill import readSkill
from .runPython import runPython
from .saveArtifact import saveArtifact
from .skillSearch import skillSearch
from .types import ToolResult, ToolSpec
from .verifyAnswer import verifyAnswer
from .webSearch import webSearch
from .write import write

ToolFn = Callable[..., ToolResult]

_SPECS: dict[str, ToolSpec] = {
    "read": ToolSpec(
        "read",
        "repo, Skill OS resource, allowed local text file을 읽고 docRef를 만든다. 쓸 때: 특정 file/skill 본문 정확히 읽기. 안 쓸 때: 검색은 read_skill/read_capability.",
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
        "artifact/scratchpad-adjacent output을 안전한 사용자 홈 경로에 저장하고 artifactRef를 만든다. 쓸 때: 큰 결과를 파일로 보존. 안 쓸 때: 답변 본문 (chunk 로 자동 발행).",
        {
            "type": "object",
            "properties": {"name": {"type": "string"}, "content": {"type": "string"}, "kind": {"type": "string"}},
            "required": ["name", "content"],
        },
    ),
    "web_search": ToolSpec(
        "web_search",
        "외부 최신 정보가 필요할 때 웹 검색을 실행하고 webRef를 만든다. 쓸 때: 외부 최신 (오늘 종가, 신규 공시, 컨센서스). 안 쓸 때: dartlab 내부 데이터 (engine_call/run_python).",
        {
            "type": "object",
            "properties": {"query": {"type": "string"}, "limit": {"type": "integer"}},
            "required": ["query"],
        },
    ),
    "skill_search": ToolSpec(
        "skill_search",
        "DEPRECATED — read_skill 사용 권장. Skill OS에서 실행 skill을 찾는다.",
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
        "DEPRECATED — read_capability 사용 권장. CAPABILITIES/docstring에서 공개 API를 찾는다.",
        {
            "type": "object",
            "properties": {"query": {"type": "string"}, "limit": {"type": "integer"}},
            "required": ["query"],
        },
    ),
    "engine_call": ToolSpec(
        "engine_call",
        "generated spec 기반 call plan을 검증한 뒤 DartLab 공개 API를 호출하고 refs를 만든다. 쓸 때: 단일 capability 1 회 호출 (Company.show, dartlab.scan). 안 쓸 때: 다단 계산·랭킹·dataframe 가공 (run_python).",
        {"type": "object", "properties": {"plan": {"type": "object"}}, "required": ["plan"]},
    ),
    "run_python": ToolSpec(
        "run_python",
        "DartLab library와 Polars를 조합해 계산/랭킹/표 생성 코드를 실행한다. 쓸 때: 다단 계산, 비교, 랭킹, dataframe 가공. 안 쓸 때: 단일 API 1 회 (engine_call). emit_result() 필수 — print 만 하면 GATE 차단.",
        {
            "type": "object",
            "properties": {"code": {"type": "string"}, "runId": {"type": "string"}},
            "required": ["code"],
        },
    ),
    "verify_answer": ToolSpec(
        "verify_answer",
        "최종 답변의 숫자/날짜/랭킹 claim이 refs로 뒷받침되는지 검증한다. 쓸 때: GATE 통합 호환 wrapper (자동 호출). 안 쓸 때: LLM 직접 호출 (GATE 가 자동).",
        {
            "type": "object",
            "properties": {"answer": {"type": "string"}, "refs": {"type": "array"}},
            "required": ["answer", "refs"],
        },
    ),
    # P1: SSOT v2 — 6 종 화이트리스트
    "read_skill": ToolSpec(
        "read_skill",
        "Skill OS에서 분석 절차 spec(frontmatter+본문)을 검색해 반환한다. 쓸 때: skill 검색·본문 읽기. recipe 발동 후 그 절차 단계 따르기. 안 쓸 때: capability docstring 검색 (read_capability).",
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
    "read_capability": ToolSpec(
        "read_capability",
        "DartLab 공개 API/docstring catalog에서 호출 가능한 capability를 검색한다. 쓸 때: capability 검색·docstring·OutputSchema·AntiPatterns 확인. 안 쓸 때: skill 절차 (read_skill).",
        {
            "type": "object",
            "properties": {"query": {"type": "string"}, "limit": {"type": "integer"}},
            "required": ["query"],
        },
    ),
    "save_artifact": ToolSpec(
        "save_artifact",
        "산출물(표/차트/긴 텍스트)을 사용자 홈 안전 경로에 저장하고 artifactRef를 만든다. 쓸 때: 큰 표 (>50 rows), 차트, 긴 텍스트. 안 쓸 때: 짧은 답변 본문.",
        {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "content": {"type": "string"},
                "kind": {"type": "string"},
            },
            "required": ["name", "content"],
        },
    ),
    "propose_skill": ToolSpec(
        "propose_skill",
        "HARVEST가 발견한 새 분석 절차를 skill spec(kind: generated, status: unverified)으로 작성한다. 쓸 때: HARVEST 단계 trace 기반 신규 후보. 안 쓸 때: WORK·COMPOSE 도중 (운영자 수동 작성 영역).",
        {
            "type": "object",
            "properties": {
                "skillId": {"type": "string"},
                "title": {"type": "string"},
                "purpose": {"type": "string"},
                "category": {"type": "string"},
                "engine": {"type": "string"},
                "whenToUse": {"type": "array"},
                "capabilityRefs": {"type": "array"},
                "datasetRefs": {"type": "array"},
                "toolRefs": {"type": "array"},
                "knowledgeRefs": {"type": "array"},
                "requiredEvidence": {"type": "array"},
                "body": {"type": "string"},
            },
            "required": ["skillId", "title", "purpose"],
        },
    ),
    "compile_visual": ToolSpec(
        "compile_visual",
        "분석 결과를 차트/표 spec 으로 변환해 visualRef 를 발급한다. agent.py 가 visualRef 감지 시 VIEW_SPEC event 발행 → ChartRenderer 인라인. 쓸 때: 시계열·비교·분포 시각화. 안 쓸 때: 단순 텍스트 답변 (chartType 모를 때).",
        {
            "type": "object",
            "properties": {
                "chartType": {
                    "type": "string",
                    "enum": ["line", "bar", "table", "radar", "waterfall", "heatmap", "histogram"],
                    "description": "line=시계열, bar=비교, table=표, radar=다축, waterfall=증감, heatmap=매트릭스, histogram=분포",
                },
                "data": {
                    "type": "array",
                    "description": "행 list (예: [{date:'2024-Q1', value:100}, ...])",
                },
                "title": {"type": "string"},
                "xAxis": {"type": "string"},
                "yAxis": {"type": "string"},
                "subtitle": {"type": "string"},
                "source": {"type": "string"},
            },
            "required": ["chartType", "data"],
        },
    ),
    "inspect_dataset": ToolSpec(
        "inspect_dataset",
        "dataset 의 schema, 행 수, 최신 관측, 샘플을 빠르게 확인해 datasetRef 를 만든다. WORK 에서 run_python 코드를 짜기 전 schema 확인용. 쓸 때: 처음 보는 dataset 의 컬럼·dtype·최신 시점 확인. 안 쓸 때: 한 번 본 dataset 의 다른 슬라이스 (run_python 안에서 직접).",
        {
            "type": "object",
            "properties": {
                "target": {
                    "type": "string",
                    "description": "예: 'Company.show:005930:BS', 'scan:profitability', 'macro', 'gather:price:005930'",
                },
                "sampleRows": {"type": "integer"},
            },
            "required": ["target"],
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
    # SSOT v2 6 종
    "read_skill": readSkill,
    "read_capability": readCapability,
    "save_artifact": saveArtifact,
    "propose_skill": proposeSkill,
    "inspect_dataset": inspectDataset,
    "compile_visual": compileVisual,
}

CANONICAL_TOOL_NAMES = tuple(_SPECS.keys())

# SSOT 6 종 (P1 에서 canonical 로 승격). P0 에서는 list 만 보유.
CANONICAL_V2: tuple[str, ...] = (
    "run_python",
    "read_skill",
    "read_capability",
    "web_search",
    "save_artifact",
    "propose_skill",
)


def toolSpecs(provider: Any = None) -> list[dict[str, Any]]:
    """Tool 명세 목록.

    provider=None: 기존 generic dict (호환).
    provider=LLMProvider 인스턴스 또는 provider id 문자열: 해당 provider 의 schema 형식.
    """
    if provider is None:
        return [spec.to_dict() for spec in _SPECS.values()]

    if isinstance(provider, str):
        from dartlab.ai.providers.catalog import PROVIDER_CLASSES

        cls = PROVIDER_CLASSES.get(provider)
        if cls is None:
            raise ValueError(f"Unknown provider: {provider!r}")
        # 빈 config 로 instantiate — toolSchema 만 사용하므로 API 키 불필요
        from dartlab.ai.providers.base import ProviderConfig

        provider_inst = cls(config=ProviderConfig(provider=provider))
    else:
        provider_inst = provider

    return [provider_inst.toolSchema(spec) for spec in _SPECS.values()]


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
        # 약한 모델이 schema 외 인자를 줄 수 있어 알려진 파라미터만 필터.
        # 함수가 **kwargs 를 받으면 그대로 통과.
        filtered = _filterKwargs(_TOOLS[name], payload)
        result = _TOOLS[name](**filtered)
    return result.to_dict()


def _filterKwargs(func: Callable[..., Any], payload: dict[str, Any]) -> dict[str, Any]:
    try:
        sig = inspect.signature(func)
    except (TypeError, ValueError):
        return payload
    accepts_var_kw = any(p.kind is inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values())
    if accepts_var_kw:
        return payload
    known = {p.name for p in sig.parameters.values() if p.kind is not inspect.Parameter.VAR_POSITIONAL}
    return {k: v for k, v in payload.items() if k in known}


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
