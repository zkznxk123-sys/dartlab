"""DartLab MCP 서버 -- Ask Workbench 표준 도구 표면.

설치 (한 번만)::

    uv tool install dartlab        # 또는: pipx install dartlab

수동 설정 (.mcp.json)::

    {
        "mcpServers": {
            "dartlab": {
                "command": "dartlab",
                "args": ["mcp"],
                "env": {"PYTHONUNBUFFERED": "1", "PYTHONUTF8": "1"}
            }
        }
    }

자동 설정::

    dartlab mcp --install   # .mcp.json 자동 생성

note: `command: "python"` 은 Microsoft Store Python 환경에서 spawn ENOENT 로 실패합니다
(이슈 #28). dartlab entry point exe 직접 호출이 더 견고.
"""

from __future__ import annotations

import json
import logging
import sys
from typing import Any

# Logger — stderr 명시 라우팅 + handler 이중 등록 방지 (stream identity 까지 비교).
# MCP stdio 는 stdout 을 JSON-RPC 프레이밍에 쓰므로 모든 로그는 stderr 로만.
_log = logging.getLogger("dartlab.mcp")
_log.propagate = False
if not any(isinstance(h, logging.StreamHandler) and getattr(h, "stream", None) is sys.stderr for h in _log.handlers):
    _log.addHandler(logging.StreamHandler(sys.stderr))
_log.setLevel(logging.INFO)


_MCP_WORKSPACE_AGENT_TOOL_NAMES = (
    "ask",
    # registry SSOT — PascalCase canonical
    "ReadSkill",
    "ReadCapability",
    "RunPython",
    "WebSearch",
    "SaveArtifact",
    "CompileVisual",
    # 분석 추론 surfacing — workbench 안에 갇혀 있던 도구를 외부 자율 호출 가능하게.
    "OutcomeLog",
    "LookAheadGuard",
    "GroundingCheck",
    # MCP elicit — 사용자 입력 요청. session 의존이라 call_tool handler 가 직접 dispatch.
    "RequestUserInput",
)


def _askWorkbenchToolSpecs() -> list[dict[str, Any]]:
    from dartlab.ai.tools.registry import toolSpecs as _aiToolSpecs

    specs = {spec["name"]: spec for spec in _aiToolSpecs()}
    specs["ask"] = {
        "name": "ask",
        "description": "DartLab 공식 AI 답변 진입점. Skill OS, generated spec, tools, ref 검증 루프를 통해 답변한다.",
        "inputSchema": {
            "type": "object",
            "properties": {"question": {"type": "string"}, "stockCode": {"type": "string"}},
            "required": ["question"],
        },
        # ask 는 5 패스 elevate — 내부에서 RunPython / SaveArtifact 호출 가능. read-only 단정 X.
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": False,
    }
    return [specs[name] for name in _MCP_WORKSPACE_AGENT_TOOL_NAMES]


def _executeAskWorkbenchTool(name: str, args: dict[str, Any]) -> dict[str, Any]:
    from dartlab.ai.tools.registry import CANONICAL_TOOL_NAMES as _AI_TOOL_NAMES
    from dartlab.ai.tools.registry import executeTool as _executeAiTool

    if name == "ask":
        from dartlab.ai.kernel import ask as _ask

        question = str(args.get("question") or "")
        kwargs = {key: value for key, value in args.items() if key != "question"}
        return {"ok": True, "answer": _ask(question, stream=False, **kwargs)}
    if name in _AI_TOOL_NAMES:
        return _executeAiTool(name, args)
    return _executeCompatAskTool(name, args)


def _executeCompatAskTool(name: str, args: dict[str, Any]) -> dict[str, Any]:
    from dartlab.ai.tools.registry import executeTool as _executeAiTool

    if name == "ask_kernel_status":
        from dartlab.ai.workbench.loop import GRAPH_NODES

        return {
            "name": "Ask Workbench",
            "entry": "ask",
            "tools": list(_MCP_WORKSPACE_AGENT_TOOL_NAMES),
            "passes": list(GRAPH_NODES),
        }
    if name == "search_reference":
        query = str(args.get("query") or "")
        skills = _executeAiTool("ReadSkill", {"query": query, "limit": args.get("limit") or 5})
        specs = _executeAiTool("ReadCapability", {"query": query, "limit": args.get("limit") or 5})
        return {
            "ok": bool(skills.get("ok") or specs.get("ok")),
            "refs": [*(skills.get("refs") or []), *(specs.get("refs") or [])],
        }
    if name == "listDartlabSkills":
        from dartlab.skills import listSkills

        return {"skills": [skill.toDict() for skill in listSkills(includeUser=bool(args.get("includeUser", True)))]}
    if name in {"searchDartlabSkills", "skill_search"}:
        return _executeAiTool(
            "ReadSkill",
            {
                "query": args.get("query", ""),
                "limit": args.get("limit") or 8,
                "includeUser": args.get("includeUser", True),
            },
        )
    if name == "explainDartlabSkill":
        return _executeAiTool("GetSkillBody", {"skillId": args.get("skillId")})
    if name == "checkDartlabSkillEvidence":
        from dartlab.skills import checkEvidence

        return checkEvidence(
            str(args.get("skillId") or ""), args.get("refs") or [], includeUser=bool(args.get("includeUser", True))
        ).toDict()
    return {
        "ok": False,
        "error": (
            f"Unknown tool: {name}. 0.10 부터 33 generated 도구 (companyStory / companyAnalysis / "
            f"marketScan 등) 와 DARTLAB_MCP_COMPAT 환경변수가 제거되었습니다. RunPython 안에서 "
            "dartlab.Company / dartlab.scan / dartlab.macro 직접 호출하세요. 자세한 마이그레이션은 "
            "CHANGELOG 참조."
        ),
    }


def _executeWorkspaceAgentTool(name: str, args: dict[str, Any]) -> dict[str, Any]:
    """canonical Ask Workbench MCP 도구 실행 → 정형 dict.

    SDK 의 call_tool 은 dict 반환을 받으면 structuredContent + serialized text 양쪽
    모두 채운다 (mcp.server.lowlevel.server.Server.call_tool docstring). 그래서 이 함수는
    dict 만 반환하고 call_tool handler 가 그대로 return — 외부 LLM 이 ref/values/table 등을
    structured 로 파싱 가능 + 텍스트 클라이언트도 호환.
    """
    return _executeAskWorkbenchTool(name, args)


def _resourcePayload(uriStr: str) -> tuple[str, str]:
    if uriStr == "dartlab://info":
        import dartlab

        return (
            json.dumps(
                {
                    "version": getattr(dartlab, "__version__", "unknown"),
                    "tools": len(_advertisedTools()),
                },
                ensure_ascii=False,
                indent=2,
            ),
            "application/json",
        )
    if uriStr == "dartlab://ask-workbench":
        return (
            json.dumps(_executeAskWorkbenchTool("ask_kernel_status", {}), ensure_ascii=False, indent=2),
            "application/json",
        )
    if uriStr == "dartlab://datasets":
        return (
            json.dumps(
                {"datasets": [], "note": "dataset refs are produced by EngineCall/RunPython"},
                ensure_ascii=False,
                indent=2,
            ),
            "application/json",
        )
    if uriStr == "dartlab://reference":
        return (
            json.dumps(
                _executeAskWorkbenchTool("search_reference", {"query": "DartLab Ask Workbench", "limit": 5}),
                ensure_ascii=False,
                indent=2,
            ),
            "application/json",
        )
    if uriStr == "dartlab://skills":
        return (
            json.dumps(
                _executeAskWorkbenchTool("listDartlabSkills", {"includeUser": False}),
                ensure_ascii=False,
                indent=2,
            ),
            "application/json",
        )
    if uriStr.startswith("dartlab://skills/"):
        skill_id = uriStr.replace("dartlab://skills/", "", 1)
        from dartlab.skills import describeSkill

        return (
            json.dumps(describeSkill(skill_id, includeUser=False), ensure_ascii=False, indent=2),
            "application/json",
        )
    if uriStr.startswith("dartlab://runs/") and uriStr.endswith("/scratchpad"):
        from pathlib import Path

        runId = uriStr.removeprefix("dartlab://runs/").removesuffix("/scratchpad")
        path = Path.home() / ".dartlab" / "ask_runs" / f"{runId}.jsonl"
        if not path.exists():
            return ("", "application/jsonl")
        return (path.read_text(encoding="utf-8"), "application/jsonl")
    return ("Unknown resource", "text/plain")


_MCP_INSTRUCTIONS = """\
DartLab MCP의 기본 표면은 ask가 실행하는 Ask Workbench와 SSOT v2 6 종 도구다. 목적은 LLM이 DartLab을
프롬프트 지식으로 외우게 하는 것이 아니라, 질문마다 먼저 skill을 고르고, capability docstring에서 호출 가능한 API를
확인한 뒤 run_python으로 실행하고 ref 검증 후 답하게 하는 것이다.

## SSOT P-revised — canonical 6 데이터 도구
- ask: Workbench 5 패스 (BRIEF→WORK→CRITIQUE→COMPOSE→GATE→HARVEST) 일괄 실행.
- ReadSkill: Skill OS 검색 + frontmatter (whenToUse, capabilityRefs, requiredEvidence) + 본문.
- ReadCapability: dartlab 공개 API/docstring 검색.
- RunPython: dartlab + Polars 코드 실행, ref 발급 (executionRef/valueRef/tableRef/dateRef). 단일 capability 1 회 호출도 본 도구 안에서.
- WebSearch: 외부 최신 정보 → webRef.
- SaveArtifact: 큰 표·차트 별도 파일 저장 → artifactRef.
- CompileVisual: 차트 spec codegen → visualRef (인라인 렌더).

## 기본 흐름
1. ask로 전체 답변 루프 실행 (단순 질문은 이걸로 끝).
2. 작업대 직접 사용 시: ReadSkill 로 절차 → ReadCapability 로 API → RunPython 으로 실행 → 답변 + ref.
3. 데이터셋 스키마·기간·행 수·최신 기준시점이 필요하면 RunPython 안에서 dartlab.* 직접 호출로 확인한다.
4. 후보·상위·랭킹 답변은 bullet 나열로 끝내지 않고 입력/유니버스, 필터, 계산식/지표, 결과와 evidence table을 함께 낸다.

## 0.10 BREAKING — 옛 33 generated 도구 제거
companyStory / companyAnalysis / companyValuation / companyForecast / companyShow / companyTopics /
companyDiff / companyGovernance / companyAudit / companyProfile / companyCredit / companyGather /
companyQuant / companyFilings / marketScan / macroAnalysis / gatherData / quantAnalysis /
topdownScreen / dartlabSearch / dartlabListing / pastInsight / sectorInsights / industryMap /
capabilities / listDartlabApi / searchDartlabApi / verifyDartlabApi / 그리고 Analysis Graph 도구
(contextForQuestion / queryAnalysisGraph / impactForGraphNode / explainDartlabTool /
planDartlabQuestion / validateDartlabPlan / listDartlabProcesses) 는 모두 RunPython 안에서
직접 호출하는 패턴으로 통합되었다. DARTLAB_MCP_COMPAT 환경변수도 폐기. 마이그레이션 예:

    # 옛: companyAnalysis(stockCode="005930", axis="수익성")
    RunPython(code='''
    c = dartlab.Company("005930")
    print(c.analysis(axis="수익성"))
    ''')

## 경계
- Company, gather, scan, macro, analysis, quant, viz는 generated MCP tool로 직접 우회하지 않는다.
  RunPython 안에서 사용하는 DartLab 라이브러리다.
- Skills는 MCP 전용 규칙이 아니라 dartlab.skills 공용 runtime을 그대로 노출한다.
- 삭제된 운영 문서 경로를 공식 진입점으로 안내하지 않는다. 모든 절차는 Skill OS에서 찾는다.
- 도구로 확인되지 않은 수치, 날짜, 실행 성공 여부를 단정하지 않는다.
- 후보·상위·랭킹 결과를 표 없이 종목명과 퍼센트만 나열하지 않는다.
"""


def _progressThresholdSec() -> float:
    """env override `DARTLAB_PROGRESS_THRESHOLD_SEC` (default 5.0). 짧은 도구는 emit 안 함."""
    import os as _os

    raw = _os.environ.get("DARTLAB_PROGRESS_THRESHOLD_SEC")
    try:
        return float(raw) if raw else 5.0
    except (TypeError, ValueError):
        return 5.0


def _progressIntervalSec() -> float:
    """env override `DARTLAB_PROGRESS_INTERVAL_SEC` (default 1.0)."""
    import os as _os

    raw = _os.environ.get("DARTLAB_PROGRESS_INTERVAL_SEC")
    try:
        return float(raw) if raw else 1.0
    except (TypeError, ValueError):
        return 1.0


async def _handleRequestUserInput(args: dict[str, Any], session: Any) -> dict[str, Any]:
    """RequestUserInput dispatch — session.elicit_form 호출.

    fields → JSON Schema 변환 후 elicit_form 으로 클라이언트에게 폼 요청. 클라이언트가
    accept/decline/cancel 로 응답. 결과를 ToolResult dict 형태로 반환.

    클라이언트 elicit 미지원이면 send_request 가 timeout / error 로 raise — 여기서 잡아
    fallback dict 반환.
    """
    from dartlab.ai.tools.requestUserInput import buildElicitSchema

    message = str(args.get("message") or "")
    fields = args.get("fields") or []
    if not isinstance(fields, list):
        fields = []
    schema = buildElicitSchema(fields)

    try:
        result = await session.elicit_form(message=message, requestedSchema=schema)
    except Exception as exc:  # noqa: BLE001 — 클라이언트 transport 의 어떤 실패든 fallback.
        return {
            "ok": False,
            "summary": f"RequestUserInput — 클라이언트 elicit 미지원 또는 실패: {type(exc).__name__}",
            "data": {"message": message, "requestedSchema": schema, "fallback": True},
            "error": "elicit_unsupported_or_failed",
        }

    action = getattr(result, "action", "decline")
    content = getattr(result, "content", None)
    return {
        "ok": action == "accept",
        "summary": f"elicit action={action}",
        "data": {
            "action": action,
            "content": content if isinstance(content, dict) else None,
            "message": message,
            "requestedSchema": schema,
        },
        "error": None if action == "accept" else f"elicit_{action}",
    }


async def _runWithProgress(
    name: str,
    arguments: dict[str, Any],
    progressToken: Any,
    session: Any,
) -> dict[str, Any]:
    """sync 도구 실행을 thread 로 옮기고 임계 위에서 progress notification 주기적 emit.

    클라이언트가 `_meta.progressToken` 으로 progress 요청한 경우만 호출. 짧은 도구 호출
    (대부분의 ReadSkill / RunPython sanity 등) 은 임계 전에 끝나 overhead 0 — emit 안 함.
    임계와 간격은 env (`DARTLAB_PROGRESS_THRESHOLD_SEC` · `DARTLAB_PROGRESS_INTERVAL_SEC`)
    로 튠. 테스트는 이 env 로 1 s 임계 / 0.5 s 간격으로 빠르게 검증.
    """
    import asyncio
    import time

    threshold = _progressThresholdSec()
    interval = _progressIntervalSec()
    start = time.perf_counter()

    async def _emit() -> None:
        while True:
            await asyncio.sleep(interval)
            elapsed = time.perf_counter() - start
            if elapsed < threshold:
                continue
            try:
                await session.send_progress_notification(
                    progress_token=progressToken,
                    progress=elapsed,
                    total=None,
                    message=f"{name} 실행 중 ({elapsed:.0f} s)...",
                )
            except Exception:
                # 클라이언트 disconnect / send 실패 — 다음 cycle 에서 재시도. 무한 루프 방지는
                # cancel 로만 (try 본문 정상 종료).
                pass

    progress_task = asyncio.create_task(_emit())
    try:
        result = await asyncio.to_thread(_executeWorkspaceAgentTool, name, arguments)
    finally:
        progress_task.cancel()
        try:
            await progress_task
        except (asyncio.CancelledError, Exception):
            pass
    return result


def _recipeSkillsForPrompts() -> list[Any]:
    """MCP `prompts/list` 에 노출할 Skill OS skill 의 SSOT 필터.

    현재 정책: `kind == "recipe"` 카테고리만 노출. `engines/{engine}/recipe/*.md` 가 여기
    해당. 새 Skill OS 카테고리 (예: `playbook`, `scenario`) 도입 시 이 필터 갱신 필요 —
    `tests/test_mcp.py::test_recipe_skills_all_exposed_as_prompts` 가 silent drift 회귀를 막는다.
    """
    from dartlab.skills import listSkills

    return [s for s in listSkills(includeUser=False) if s.kind == "recipe"]


def _advertisedTools() -> list[dict[str, Any]]:
    """MCP list_tools 에 노출할 도구 — registry canonical 6 + ask.

    각 도구의 ToolSpec annotations (readOnly/destructive/idempotent/openWorld hint) 도 함께
    노출 — `list_tools()` handler 가 ToolAnnotations 로 매핑한다.
    """
    tools: list[dict[str, Any]] = []
    for spec in _askWorkbenchToolSpecs():
        schema = spec.get("inputSchema") or {}
        annotations: dict[str, bool] = {}
        for key in ("readOnlyHint", "destructiveHint", "idempotentHint", "openWorldHint"):
            value = spec.get(key)
            if value is not None:
                annotations[key] = bool(value)
        tools.append(
            {
                "name": spec["name"],
                "description": spec["description"],
                "params": schema.get("properties") or {},
                "required": schema.get("required") or [],
                "annotations": annotations,
            }
        )
    return tools


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MCP 서버 생성
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def createServer():
    """MCP 서버 인스턴스 생성."""
    try:
        from mcp.server import Server
        from mcp.server.lowlevel.server import ReadResourceContents
        from mcp.types import (
            GetPromptResult,
            Prompt,
            PromptArgument,
            PromptMessage,
            Resource,
            TextContent,
            Tool,
            ToolAnnotations,
        )
    except ImportError as exc:
        raise ImportError("MCP SDK 필요: pip install --upgrade dartlab") from exc

    app = Server("dartlab", instructions=_MCP_INSTRUCTIONS)
    _log.info("MCP 서버 초기화 완료")

    def _toAnnotations(specAnnotations: dict[str, bool]) -> ToolAnnotations | None:
        if not specAnnotations:
            return None
        return ToolAnnotations(**specAnnotations)

    @app.list_tools()
    async def listTools() -> list[Tool]:
        """tools/list — advertise 된 tool list (annotation 포함)."""
        tools: list[Tool] = []
        for t in _advertisedTools():
            tools.append(
                Tool(
                    name=t["name"],
                    description=t["description"],
                    inputSchema={
                        "type": "object",
                        "properties": t["params"],
                        "required": t["required"],
                    },
                    annotations=_toAnnotations(t.get("annotations") or {}),
                )
            )
        return tools

    @app.call_tool()
    async def callTool(name: str, arguments: dict) -> dict[str, Any]:
        """tools/call — tool name + arguments 를 받아 dispatch + structuredContent 반환."""
        # SDK 가 dict 반환을 받으면 structuredContent + serialized text 양쪽 모두 자동 채움.
        # 외부 LLM 은 ref/values/table 등을 structured 로 파싱 가능 + 텍스트 클라이언트 호환.
        _log.info("call_tool: %s(%s)", name, list(arguments.keys()))

        # progressToken 이 있으면 5 s 임계 위 실행은 백그라운드 progress notification.
        # 짧은 호출은 overhead 0 — sync 그대로. 클라이언트가 progress 미요청이면 emit skip.
        progressToken = None
        session = None
        try:
            ctx = app.request_context
            meta = getattr(ctx, "meta", None)
            if meta is not None:
                progressToken = getattr(meta, "progressToken", None)
            session = getattr(ctx, "session", None)
        except (LookupError, RuntimeError):
            pass

        # RequestUserInput 은 session.elicit_form 직접 dispatch — sync registry executor 가
        # async session 의존성을 끼워넣지 않도록.
        if name == "RequestUserInput" and session is not None:
            return await _handleRequestUserInput(arguments, session)

        if progressToken is None or session is None:
            return _executeWorkspaceAgentTool(name, arguments)

        return await _runWithProgress(name, arguments, progressToken, session)

    @app.list_resources()
    async def listResources() -> list[Resource]:
        """resources/list — dartlab 노출 가능한 resource list (skill spec 등)."""
        return [
            Resource(
                uri="dartlab://info",
                name="DartLab",
                description="Ask Workbench Kernel 상태와 DartLab 런타임 정보",
                mimeType="application/json",
            ),
            Resource(
                uri="dartlab://ask-workbench",
                name="Ask Workbench",
                description="표준 MCP 도구, 런타임 데이터셋, 검산 경계 요약",
                mimeType="application/json",
            ),
            Resource(
                uri="dartlab://datasets",
                name="Runtime Dataset Catalog",
                description="접근 가능한 런타임 데이터셋 id, 경로, 최신 관측일 요약",
                mimeType="application/json",
            ),
            Resource(
                uri="dartlab://reference",
                name="DartLab Reference",
                description="Ask Workbench 설계와 공개 참조 검색 표면",
                mimeType="application/json",
            ),
            Resource(
                uri="dartlab://skills",
                name="DartLab Skills",
                description="DartLab Skill OS 목록. AI, MCP, story, UI, audit가 같은 resolver를 사용",
                mimeType="application/json",
            ),
        ]

    @app.read_resource()
    async def readResource(uri: str) -> list[ReadResourceContents]:
        """resources/read — uri 로 resource 본문 읽기."""
        uriStr = str(uri)
        content, mime_type = _resourcePayload(uriStr)
        return [ReadResourceContents(content=content, mime_type=mime_type)]

    # ── Prompts API — Skill OS recipe 카테고리를 prompt 로 노출 ─────────────────
    # 외부 LLM 이 한 번의 prompt 호출로 multi-step 분석 시나리오를 받음. arguments 는
    # skill 의 inputs frontmatter 에서 derive — required=False (LLM 이 채우거나 무시).

    @app.list_prompts()
    async def listPrompts() -> list[Prompt]:
        """prompts/list — recipe 카테고리 기반 prompt list."""
        prompts: list[Prompt] = []
        for spec in _recipeSkillsForPrompts():
            args = [
                PromptArgument(name=f"input{idx + 1}", description=text, required=False)
                for idx, text in enumerate(spec.inputs or [])
            ]
            prompts.append(
                Prompt(
                    name=spec.id,
                    description=f"{spec.title} — {spec.purpose[:200]}" if spec.purpose else spec.title,
                    arguments=args or None,
                )
            )
        return prompts

    # ── logging/setLevel — 클라이언트가 dartlab logger 레벨 동적 조정 ─────────
    @app.set_logging_level()
    async def setLoggingLevel(level: str) -> None:
        """logging/setLevel — 클라이언트가 dartlab logger 레벨 동적 조정."""
        # MCP LoggingLevel 은 RFC5424 (debug/info/notice/warning/error/critical/alert/emergency).
        # Python logging 은 이 중 일부만 매칭. 그 외는 가장 가까운 표준 레벨로 매핑.
        mapping = {
            "debug": logging.DEBUG,
            "info": logging.INFO,
            "notice": logging.INFO,
            "warning": logging.WARNING,
            "error": logging.ERROR,
            "critical": logging.CRITICAL,
            "alert": logging.CRITICAL,
            "emergency": logging.CRITICAL,
        }
        py_level = mapping.get(str(level).lower(), logging.INFO)
        _log.setLevel(py_level)
        _log.info("logger level set to %s (Python %d) by client", level, py_level)

    @app.get_prompt()
    async def getPrompt(name: str, arguments: dict[str, str] | None = None) -> GetPromptResult:
        """prompts/get — recipe name + arguments 로 prompt 본문 반환."""
        from dartlab.skills import getSkill

        try:
            spec = getSkill(name, includeUser=False)
        except KeyError as exc:
            raise ValueError(f"Unknown prompt: {name}") from exc

        body = str(spec.source.get("body") or "")
        # 사용자 arguments 가 있으면 본문 위에 컨텍스트 블록 prepend.
        prefix = ""
        if arguments:
            lines = "\n".join(f"- {k}: {v}" for k, v in arguments.items())
            prefix = f"## 사용자 입력\n{lines}\n\n---\n\n"
        text = f"# {spec.title}\n\n{spec.purpose}\n\n{prefix}{body}"

        return GetPromptResult(
            description=spec.title,
            messages=[PromptMessage(role="user", content=TextContent(type="text", text=text))],
        )

    return app


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 설치 헬퍼 -- dartlab mcp --install
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def installMcpConfig(targetDir: str | None = None) -> str:
    """프로젝트에 .mcp.json을 자동 생성한다.

    Returns:
        생성된 파일 경로.
    """
    from pathlib import Path

    root = Path(targetDir) if targetDir else Path.cwd()
    mcpFile = root / ".mcp.json"

    config: dict = {}
    if mcpFile.exists():
        try:
            config = json.loads(mcpFile.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            config = {}

    servers = config.setdefault("mcpServers", {})
    if "dartlab" in servers:
        return f"이미 등록됨: {mcpFile}"

    # uv tool install / pipx install 가 만든 entry point (`dartlab` / `dartlab.exe`) 직접 호출.
    # 이슈 #28 follow-up: Microsoft Store Python 의 `python` PATH stub 이 spawn ENOENT 로 실패하는
    # 회피책. dartlab entry point exe 는 PATH 검색 의존이 가벼워 spawn 안전.
    servers["dartlab"] = {
        "command": "dartlab",
        "args": ["mcp"],
        "env": {"PYTHONUNBUFFERED": "1", "PYTHONUTF8": "1"},
    }
    mcpFile.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")
    return f"생성 완료: {mcpFile}"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 엔트리포인트
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def runStdio():
    """stdio 모드로 MCP 서버 실행."""
    import asyncio

    try:
        from mcp.server.stdio import stdio_server
    except ImportError as exc:
        raise ImportError("MCP SDK 필요: pip install --upgrade dartlab") from exc

    app = createServer()

    async def _main():
        async with stdio_server() as (read_stream, write_stream):
            _log.info("DartLab MCP 서버 시작 (stdio)")
            await app.run(read_stream, write_stream, app.create_initialization_options())

    asyncio.run(_main())


def createSseApp():
    """SSE 전송 기반 ASGI 앱 생성. FastAPI에 마운트하거나 독립 실행 가능."""
    from mcp.server.sse import SseServerTransport
    from starlette.applications import Starlette
    from starlette.routing import Mount, Route

    mcp_server = createServer()
    sse = SseServerTransport("/messages/")

    async def handleSse(request):
        """SSE 연결 handshake — 클라이언트 → mcp_server 양방향 stream."""
        async with sse.connect_sse(request.scope, request.receive, request._send) as (read, write):
            await mcp_server.run(read, write, mcp_server.create_initialization_options())

    return Starlette(
        routes=[
            Route("/sse", endpoint=handleSse),
            Mount("/messages/", app=sse.handle_post_message),
        ],
    )


def runSse(host: str = "0.0.0.0", port: int = 8001):
    """SSE 모드로 MCP 서버 실행 (HTTP)."""
    import uvicorn

    _log.info("DartLab MCP 서버 시작 (SSE http://%s:%d/sse)", host, port)
    uvicorn.run(createSseApp(), host=host, port=port)


if __name__ == "__main__":
    runStdio()
