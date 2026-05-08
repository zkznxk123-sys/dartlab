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

        return {"skills": [skill.to_dict() for skill in listSkills(includeUser=bool(args.get("includeUser", True)))]}
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
        ).to_dict()
    return {
        "ok": False,
        "error": (
            f"Unknown tool: {name}. 0.10 부터 33 generated 도구 (companyStory / companyAnalysis / "
            f"marketScan 등) 와 DARTLAB_MCP_COMPAT 환경변수가 제거되었습니다. RunPython 안에서 "
            "dartlab.Company / dartlab.scan / dartlab.macro 직접 호출하세요. 자세한 마이그레이션은 "
            "CHANGELOG 참조."
        ),
    }


def _executeWorkspaceAgentTool(name: str, args: dict[str, Any]) -> str:
    """canonical Ask Workbench MCP 도구 실행 → JSON 직렬화."""
    return json.dumps(_executeAskWorkbenchTool(name, args), ensure_ascii=False, indent=2, default=str)


def _resourcePayload(uri_str: str) -> tuple[str, str]:
    if uri_str == "dartlab://info":
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
    if uri_str == "dartlab://ask-workbench":
        return (
            json.dumps(_executeAskWorkbenchTool("ask_kernel_status", {}), ensure_ascii=False, indent=2),
            "application/json",
        )
    if uri_str == "dartlab://datasets":
        return (
            json.dumps(
                {"datasets": [], "note": "dataset refs are produced by EngineCall/RunPython"},
                ensure_ascii=False,
                indent=2,
            ),
            "application/json",
        )
    if uri_str == "dartlab://reference":
        return (
            json.dumps(
                _executeAskWorkbenchTool("search_reference", {"query": "DartLab Ask Workbench", "limit": 5}),
                ensure_ascii=False,
                indent=2,
            ),
            "application/json",
        )
    if uri_str == "dartlab://skills":
        return (
            json.dumps(
                _executeAskWorkbenchTool("listDartlabSkills", {"includeUser": False}),
                ensure_ascii=False,
                indent=2,
            ),
            "application/json",
        )
    if uri_str.startswith("dartlab://skills/"):
        skill_id = uri_str.replace("dartlab://skills/", "", 1)
        from dartlab.skills import describeSkill

        return (
            json.dumps(describeSkill(skill_id, includeUser=False), ensure_ascii=False, indent=2),
            "application/json",
        )
    if uri_str.startswith("dartlab://runs/") and uri_str.endswith("/scratchpad"):
        from pathlib import Path

        run_id = uri_str.removeprefix("dartlab://runs/").removesuffix("/scratchpad")
        path = Path.home() / ".dartlab" / "ask_runs" / f"{run_id}.jsonl"
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


def _advertisedTools() -> list[dict[str, Any]]:
    """MCP list_tools 에 노출할 도구 — registry canonical 6 + ask."""
    tools: list[dict[str, Any]] = []
    for spec in _askWorkbenchToolSpecs():
        schema = spec.get("inputSchema") or {}
        tools.append(
            {
                "name": spec["name"],
                "description": spec["description"],
                "params": schema.get("properties") or {},
                "required": schema.get("required") or [],
            }
        )
    return tools


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MCP 서버 생성
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def create_server():
    """MCP 서버 인스턴스 생성."""
    try:
        from mcp.server import Server
        from mcp.server.lowlevel.server import ReadResourceContents
        from mcp.types import Resource, TextContent, Tool
    except ImportError as exc:
        raise ImportError("MCP SDK 필요: pip install --upgrade dartlab") from exc

    app = Server("dartlab", instructions=_MCP_INSTRUCTIONS)
    _log.info("MCP 서버 초기화 완료")

    @app.list_tools()
    async def list_tools() -> list[Tool]:
        return [
            Tool(
                name=t["name"],
                description=t["description"],
                inputSchema={
                    "type": "object",
                    "properties": t["params"],
                    "required": t["required"],
                },
            )
            for t in _advertisedTools()
        ]

    @app.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[TextContent]:
        _log.info("call_tool: %s(%s)", name, list(arguments.keys()))
        return [TextContent(type="text", text=_executeWorkspaceAgentTool(name, arguments))]

    @app.list_resources()
    async def list_resources() -> list[Resource]:
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
    async def read_resource(uri: str) -> list[ReadResourceContents]:
        uri_str = str(uri)
        content, mime_type = _resourcePayload(uri_str)
        return [ReadResourceContents(content=content, mime_type=mime_type)]

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


def run_stdio():
    """stdio 모드로 MCP 서버 실행."""
    import asyncio

    try:
        from mcp.server.stdio import stdio_server
    except ImportError as exc:
        raise ImportError("MCP SDK 필요: pip install --upgrade dartlab") from exc

    app = create_server()

    async def _main():
        async with stdio_server() as (read_stream, write_stream):
            _log.info("DartLab MCP 서버 시작 (stdio)")
            await app.run(read_stream, write_stream, app.create_initialization_options())

    asyncio.run(_main())


def create_sse_app():
    """SSE 전송 기반 ASGI 앱 생성. FastAPI에 마운트하거나 독립 실행 가능."""
    from mcp.server.sse import SseServerTransport
    from starlette.applications import Starlette
    from starlette.routing import Mount, Route

    mcp_server = create_server()
    sse = SseServerTransport("/messages/")

    async def handle_sse(request):
        async with sse.connect_sse(request.scope, request.receive, request._send) as (read, write):
            await mcp_server.run(read, write, mcp_server.create_initialization_options())

    return Starlette(
        routes=[
            Route("/sse", endpoint=handle_sse),
            Mount("/messages/", app=sse.handle_post_message),
        ],
    )


def run_sse(host: str = "0.0.0.0", port: int = 8001):
    """SSE 모드로 MCP 서버 실행 (HTTP)."""
    import uvicorn

    _log.info("DartLab MCP 서버 시작 (SSE http://%s:%d/sse)", host, port)
    uvicorn.run(create_sse_app(), host=host, port=port)


if __name__ == "__main__":
    run_stdio()
