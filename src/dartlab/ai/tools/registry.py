"""Canonical AI tool registry."""

from __future__ import annotations

import inspect
from typing import Any, Callable

from .compileVisual import compileVisual
from .inspectDataset import inspectDataset
from .proposeSkill import proposeSkill
from .readCapability import readCapability
from .readSkill import readSkill
from .runPython import runPython
from .saveArtifact import saveArtifact
from .types import ToolResult, ToolSpec
from .webSearch import webSearch

ToolFn = Callable[..., ToolResult]

_SPECS: dict[str, ToolSpec] = {
    "web_search": ToolSpec(
        "web_search",
        "외부 최신 정보가 필요할 때 웹 검색을 실행하고 webRef를 만든다. 쓸 때: 외부 최신 (오늘 종가, 신규 공시, 컨센서스). 안 쓸 때: dartlab 내부 데이터 (run_python).",
        {
            "type": "object",
            "properties": {"query": {"type": "string"}, "limit": {"type": "integer"}},
            "required": ["query"],
        },
    ),
    "run_python": ToolSpec(
        "run_python",
        "DartLab library와 Polars를 조합해 계산/랭킹/표 생성 코드를 실행한다. 쓸 때: 다단 계산, 비교, 랭킹, dataframe 가공, 단일 capability 1 회 호출도 가능 (Company.show / dartlab.scan 등). emit_result() 필수 — print 만 하면 GATE 차단.",
        {
            "type": "object",
            "properties": {"code": {"type": "string"}, "runId": {"type": "string"}},
            "required": ["code"],
        },
    ),
    # SSOT P-revised — canonical 6 데이터 도구 + meta
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
                "whenToUse": {"type": "array", "items": {"type": "string"}},
                "capabilityRefs": {"type": "array", "items": {"type": "string"}},
                "datasetRefs": {"type": "array", "items": {"type": "string"}},
                "toolRefs": {"type": "array", "items": {"type": "string"}},
                "knowledgeRefs": {"type": "array", "items": {"type": "string"}},
                "requiredEvidence": {"type": "array", "items": {"type": "string"}},
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
                    "items": {"type": "object", "additionalProperties": True},
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
    "web_search": webSearch,
    "run_python": runPython,
    "read_skill": readSkill,
    "read_capability": readCapability,
    "save_artifact": saveArtifact,
    "propose_skill": proposeSkill,
    "inspect_dataset": inspectDataset,
    "compile_visual": compileVisual,
}

CANONICAL_TOOL_NAMES = tuple(_SPECS.keys())

# SSOT P-revised — canonical 6 데이터 도구 (chat-native LLM 노출 default).
# inspect_dataset 은 workbench WORK 패스 한정 helper, propose_skill 은 다음 commit 에서 삭제.
CANONICAL_V2: tuple[str, ...] = (
    "run_python",
    "read_skill",
    "read_capability",
    "web_search",
    "save_artifact",
    "compile_visual",
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
