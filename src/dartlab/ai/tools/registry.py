"""Canonical AI tool registry.

도구 명명: PascalCase (Claude 도구 체계 호환). 일관성 + LLM 학습 패턴 활용.
"""

from __future__ import annotations

import inspect
from typing import Any, Callable

from .compileVisual import compileVisual
from .engineCall import engineCall
from .inspectDataset import inspectDataset
from .readCapability import readCapability
from .readFile import readFile
from .readSkill import getSkillBody, readSkill
from .runPython import runPython
from .runWorkbench import runWorkbench
from .saveArtifact import saveArtifact
from .types import ToolResult, ToolSpec
from .webSearch import webSearch

ToolFn = Callable[..., ToolResult]

_SPECS: dict[str, ToolSpec] = {
    # ── 분석 절차 / 메타 — 시작 도구 ──
    "ReadSkill": ToolSpec(
        "ReadSkill",
        "Skill OS 에서 분석 절차 spec(frontmatter+본문) 검색. 분석 의도면 가장 먼저. recipe 발견 시 그 절차 따르기.",
        {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "limit": {"type": "integer"},
                "includeUser": {"type": "boolean"},
            },
            "required": ["query"],
        },
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False,
    ),
    "GetSkillBody": ToolSpec(
        "GetSkillBody",
        "단일 skill 의 본문 전문이 필요할 때. ReadSkill 결과의 bodyPreview 가 부족하면 두 번째 호출.",
        {
            "type": "object",
            "properties": {"skillId": {"type": "string"}},
            "required": ["skillId"],
        },
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False,
    ),
    "ReadCapability": ToolSpec(
        "ReadCapability",
        "DartLab 공개 API/docstring 카탈로그 검색. 어떤 capability(EngineCall 의 apiRef) 가 있는지 확인할 때.",
        {
            "type": "object",
            "properties": {"query": {"type": "string"}, "limit": {"type": "integer"}},
            "required": ["query"],
        },
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False,
    ),
    # ── 데이터 호출 — 실행 도구 ──
    "EngineCall": ToolSpec(
        "EngineCall",
        "DartLab 공개 capability 1 회 호출 (Company.show, scan, macro 등). 정형 ref 반환. 단일 데이터 조회면 RunPython 보다 이거. 다단 계산이면 RunPython.",
        {
            "type": "object",
            "properties": {
                "apiRef": {
                    "type": "string",
                    "description": "예: 'Company.show', 'scan', 'macro.kospi', 'dartlab.scan'",
                },
                "args": {
                    "type": "object",
                    "description": "capability 인자 (예: {'stockCode': '005930', 'topic': 'IS'})",
                    "additionalProperties": True,
                },
            },
            "required": ["apiRef"],
        },
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False,
    ),
    "RunPython": ToolSpec(
        "RunPython",
        "DartLab + Polars 임의 코드 실행. 다단 계산·랭킹·dataframe 가공·시계열 연산. 결과는 emit_result(table=..., values=..., date=...) keyword 형식 (dict 한 개 positional 도 자동 unpack). 사용 가능 변수: dartlab, pl(polars), normalizeColumn, columnsFor, availableTopics. 단일 capability 1 회 호출이면 EngineCall 권장.",
        {
            "type": "object",
            "properties": {"code": {"type": "string"}, "runId": {"type": "string"}},
            "required": ["code"],
        },
        # 임의 코드 실행 — read-only 라 단정 못 함 (사용자 코드가 SaveArtifact 같은 도구 우회 가능).
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=False,
        openWorldHint=False,
    ),
    "InspectDataset": ToolSpec(
        "InspectDataset",
        "dataset schema·행 수·최신 관측·샘플 빠르게 확인. RunPython 코드 짜기 전 컬럼 추측 실패 방지용.",
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
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False,
    ),
    # ── 파일·외부 ──
    "Read": ToolSpec(
        "Read",
        "안전 경로 (repo, 사용자 artifacts) 안의 텍스트 파일을 읽어 docRef 발급. 사용자 보고서·블로그 본문·skill body 직접 인용 시.",
        {
            "type": "object",
            "properties": {
                "target": {"type": "string", "description": "절대 경로 또는 repo 기준 상대 경로"},
                "startLine": {"type": "integer"},
                "endLine": {"type": "integer"},
            },
            "required": ["target"],
        },
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False,
    ),
    "WebSearch": ToolSpec(
        "WebSearch",
        "외부 최신 정보 (오늘 종가, 신규 공시, 컨센서스). dartlab 내부 데이터엔 EngineCall/RunPython.",
        {
            "type": "object",
            "properties": {"query": {"type": "string"}, "limit": {"type": "integer"}},
            "required": ["query"],
        },
        # 외부 검색 — 결과가 외부 환경 (web) 의존, idempotent 아님, openWorld True.
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=False,
        openWorldHint=True,
    ),
    # ── 산출 ──
    "SaveArtifact": ToolSpec(
        "SaveArtifact",
        "큰 표 (>50 rows)·차트·긴 텍스트를 사용자 홈 안전 경로에 저장 → artifactRef. 짧은 답변 본문엔 쓰지 말 것.",
        {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "content": {"type": "string"},
                "kind": {"type": "string"},
            },
            "required": ["name", "content"],
        },
        # 디스크 쓰기 — 사용자 홈 ~/.dartlab/artifacts/ 에 새 파일 생성. 같은 이름 두 번 호출 시
        # 덮어쓰기 가능 (idempotent 아님). destructive 는 아니지만 read-only 도 아님.
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=False,
        openWorldHint=False,
    ),
    "CompileVisual": ToolSpec(
        "CompileVisual",
        "분석 결과를 차트/표 spec 으로 변환 → visualRef → 메시지 흐름에 인라인 차트 렌더. 시계열·비교·분포는 텍스트보다 이게 명확.",
        {
            "type": "object",
            "properties": {
                "chartType": {
                    "type": "string",
                    "enum": ["line", "bar", "table", "radar", "waterfall", "heatmap", "histogram"],
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
        # 메모리 spec 생성 — 디스크 쓰기 없음. 같은 입력은 같은 spec.
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False,
    ),
    # ── elevate (옵션 sub-agent) ──
    "RunWorkbench": ToolSpec(
        "RunWorkbench",
        "깊은 분석을 5 패스 (BRIEF/WORK/CRITIQUE/COMPOSE/GATE/HARVEST) 작업대로 elevate. 회사 종합 분석·skill 절차 의존·ref 검증 강제 필요할 때만.",
        {
            "type": "object",
            "properties": {
                "question": {"type": "string"},
                "stockCode": {"type": "string"},
                "market": {"type": "string", "enum": ["KR", "US"]},
            },
            "required": ["question"],
        },
        # 5 패스 elevate — 내부에서 RunPython / SaveArtifact 호출 가능. read-only 단정 X.
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=False,
        openWorldHint=False,
    ),
}

_TOOLS: dict[str, ToolFn] = {
    "ReadSkill": readSkill,
    "GetSkillBody": getSkillBody,
    "ReadCapability": readCapability,
    "EngineCall": engineCall,
    "RunPython": runPython,
    "InspectDataset": inspectDataset,
    "Read": readFile,
    "WebSearch": webSearch,
    "SaveArtifact": saveArtifact,
    "CompileVisual": compileVisual,
    "RunWorkbench": runWorkbench,
}

CANONICAL_TOOL_NAMES = tuple(_SPECS.keys())

# chat-native LLM 노출 default. ReadSkill 부터 시작 권장 (system prompt 가 순서 안내).
# GetSkillBody 는 ReadSkill 후보 압축한 뒤 단일 skill 본문 fetch — 두 단계 호출 루틴.
CANONICAL_V2: tuple[str, ...] = (
    "ReadSkill",
    "GetSkillBody",
    "ReadCapability",
    "EngineCall",
    "RunPython",
    "Read",
    "WebSearch",
    "SaveArtifact",
    "CompileVisual",
)

# snake_case ↔ PascalCase 호환 — 옛 호출자 / 옛 model 가 snake 로 부르면 자동 매핑.
_LEGACY_NAME_MAP = {
    "read_skill": "ReadSkill",
    "get_skill_body": "GetSkillBody",
    "read_capability": "ReadCapability",
    "engine_call": "EngineCall",
    "run_python": "RunPython",
    "inspect_dataset": "InspectDataset",
    "read": "Read",
    "web_search": "WebSearch",
    "save_artifact": "SaveArtifact",
    "compile_visual": "CompileVisual",
    "run_workbench": "RunWorkbench",
}


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
    # Legacy snake 이름 (read_skill 등) 도 canonical PascalCase 로 정규화해 보호 — plugin
    # 이 옛 이름으로 우회 등록하면 canonical 도구가 silently 덮어씌워지는 회귀 가능.
    canonical = _LEGACY_NAME_MAP.get(name, name)
    if canonical in CANONICAL_TOOL_NAMES:
        raise ValueError(f"canonical tool은 plugin으로 덮어쓸 수 없습니다: {name} (-> {canonical})")
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
    canonical = _LEGACY_NAME_MAP.get(name, name)
    if canonical in CANONICAL_TOOL_NAMES:
        raise ValueError(f"canonical tool은 해제할 수 없습니다: {name} (-> {canonical})")
    _SPECS.pop(name, None)
    _TOOLS.pop(name, None)


def executeTool(name: str, args: dict[str, Any] | None = None) -> dict[str, Any]:
    canonical = _LEGACY_NAME_MAP.get(name, name)
    if canonical not in _TOOLS:
        return ToolResult(False, f"Unknown tool: {name}", error="unknown_tool").to_dict()
    payload = dict(args or {})
    filtered = _filterKwargs(_TOOLS[canonical], payload)
    result = _TOOLS[canonical](**filtered)
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
