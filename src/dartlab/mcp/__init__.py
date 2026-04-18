"""DartLab MCP 서버 -- 한국 상장기업 전자공시 분석.

설치 후 바로 사용::

    pip install dartlab
    # Claude Code / Codex에서 "삼성전자 분석해줘" → 바로 동작

수동 설정 (.mcp.json)::

    {
        "mcpServers": {
            "dartlab": {
                "command": "uv",
                "args": ["run", "python", "-X", "utf8", "-m", "dartlab.mcp"]
            }
        }
    }

자동 설정::

    dartlab mcp --install   # .mcp.json 자동 생성
"""

from __future__ import annotations

import json
import logging
import sys
import time
import traceback
from typing import Any

_log = logging.getLogger("dartlab.mcp")
_log.addHandler(logging.StreamHandler(sys.stderr))
_log.setLevel(logging.INFO)

_CACHE_MAX = 5
_CACHE_TTL = 600
_cache: dict[str, tuple[Any, float]] = {}


def _getCompany(stockCode: str) -> Any:
    """종목코드로 Company 인스턴스 (캐싱)."""
    entry = _cache.get(stockCode)
    if entry:
        obj, ts = entry
        if (time.monotonic() - ts) < _CACHE_TTL:
            return obj
        del _cache[stockCode]
    from dartlab import Company

    _log.info("Company('%s') loading...", stockCode)
    c = Company(stockCode)
    if len(_cache) >= _CACHE_MAX:
        del _cache[next(iter(_cache))]
    _cache[stockCode] = (c, time.monotonic())
    _log.info("Company('%s') ready", stockCode)
    return c


_MCP_MAX_RESULT_CHARS = 12000  # MCP 도구 결과 상한 (외부 AI 컨텍스트 절약)


def _fmt(obj) -> str:
    """객체를 LLM이 읽기 좋은 텍스트로 변환. 결과가 크면 잘라냄."""
    if obj is None:
        return "데이터 없음"
    if hasattr(obj, "to_pandas"):
        result = obj.to_pandas().to_string()
    elif isinstance(obj, dict):
        result = _fmtDict(obj)
    elif isinstance(obj, list):
        result = "\n".join(str(item) for item in obj)
    else:
        result = str(obj)
    if len(result) > _MCP_MAX_RESULT_CHARS:
        return result[:_MCP_MAX_RESULT_CHARS] + f"\n\n...(결과 잘림, 전체 {len(result)}자. 범위를 좁혀 재조회하세요)"
    return result


def _fmtDict(d: dict, depth: int = 0) -> str:
    """dict를 마크다운 텍스트로 변환. analysis 결과용."""
    parts: list[str] = []
    prefix = "#" * min(depth + 3, 5)  # ###, ####, #####
    for key, val in d.items():
        if val is None:
            continue
        if isinstance(val, dict):
            parts.append(f"{prefix} {key}")
            parts.append(_fmtDict(val, depth + 1))
        elif hasattr(val, "to_pandas"):
            parts.append(f"{prefix} {key}")
            parts.append(val.to_pandas().to_string())
        elif isinstance(val, list):
            if val and isinstance(val[0], str):
                parts.append(f"{prefix} {key}")
                for item in val:
                    parts.append(f"- {item}")
            elif val and isinstance(val[0], dict):
                parts.append(f"{prefix} {key}")
                for item in val:
                    parts.append(str(item))
            else:
                parts.append(f"**{key}**: {val}")
        elif isinstance(val, (int, float)):
            parts.append(f"- **{key}**: {val}")
        else:
            parts.append(f"- **{key}**: {val}")
    return "\n".join(parts)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Instructions -- LLM에게 사용법을 알려준다
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_MCP_INSTRUCTIONS = """\
dartlab은 한국 상장기업 전자공시(DART) 및 미국 SEC EDGAR 분석 도구입니다.

## 지원 시장
- **한국 (DART)**: 종목코드 6자리 (예: "005930") 또는 회사명 (예: "삼성전자")
- **미국 (EDGAR)**: 티커 1-5자 (예: "AAPL") 또는 CIK 번호
- searchCompany로 종목코드/티커를 검색할 수 있다.

## 도구 사용 흐름

### 개별 종목 분석
1. 종목코드를 모르면 → searchCompany
2. 빠른 판단 → companyInsights (7영역 등급 + 프로파일)
3. 심층 분석 → companyAnalysis(axis="financial", sub="수익구조") 등
4. 원본 데이터 → companyFinancials, companyRatios
5. 밸류에이션 → companyValuation, companyForecast
6. 신용 분석 → companyCredit
7. 주가/기술적 분석 → companyGather("price"), companyQuant("판단")
8. 시장 비교 → marketScan
9. 정리된 보고서 → companyReview (사용자가 명시할 때만)

### 시장/거시 분석 (Company 불필요)
- macroAnalysis: 경제 사이클, 금리, 자산, 심리, 유동성, 종합
- gatherData: 주가, 수급, 거시지표, 뉴스
- topdownScreen: 사이클 → 추천 섹터 → 종목 후보
- dartlabSearch: 공시 원문 검색
- dartlabListing: 상장 종목/공시 목록

## review vs analysis
- companyReview: 전체 보고서. "보고서 만들어줘"라고 명시할 때만.
- companyAnalysis: 특정 영역 원본 데이터. 직접 해석할 때 사용.
- companyInsights: 7영역 등급 요약. 빠른 판단.

## 출력 규칙
- 도구 결과를 사용자에게 그대로 보여준 뒤 해석을 덧붙여라.
- 도구로 확인되지 않은 수치를 인용하지 마라.
- 한국어 질문에는 한국어로 답변하라.

## 행동 규칙
- 분석 요청 시 되묻지 말고 즉시 도구를 호출하라.
"""


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MCP 도구 정의 — 자동 생성 파일에서 import
# generateSpec.py 실행 시 _generated_tools.py가 갱신됨
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

from dartlab.mcp._generated_tools import TOOL_FEATURE_MAP as _TOOL_FEATURE_MAP  # noqa: E402
from dartlab.mcp._generated_tools import TOOLS as _TOOLS  # noqa: E402


def _executeTool(name: str, args: dict) -> str:
    """MCP 도구 실행."""
    import dartlab

    code = args.get("stockCode")

    try:
        if name == "companyReview":
            c = _getCompany(code)
            section = args.get("section")
            if section:
                return c.review(section).toMarkdown()
            return c.review().toMarkdown()

        if name == "companyInsights":
            return str(_getCompany(code).insights)
        if name == "searchCompany":
            return _fmt(dartlab.searchName(args["query"]))

        if name == "companyFinancials":
            return _fmt(getattr(_getCompany(code), args["statement"], None))

        if name == "companyRatios":
            return _fmt(_getCompany(code).ratios)

        if name == "companyAnalysis":
            c = _getCompany(code)
            axis = args.get("axis")
            sub = args.get("sub")
            if axis and sub:
                return _fmt(c.analysis(axis, sub))
            elif axis:
                return _fmt(c.analysis(axis))
            else:
                return _fmt(c.analysis())

        if name == "companyValuation":
            return _fmt(_getCompany(code).analysis("valuation", "가치평가"))

        if name == "companyForecast":
            return _fmt(_getCompany(code).analysis("forecast", "매출전망"))

        if name == "companyShow":
            return str(_getCompany(code).show(args["topic"]))
        if name == "companyTopics":
            return json.dumps(_getCompany(code).topics, ensure_ascii=False, indent=2)

        if name == "companyDiff":
            c = _getCompany(code)
            topic = args.get("topic")
            return str(c.diff(topic) if topic else c.diff())
        if name == "companyGovernance":
            return _fmt(_getCompany(code).governance())

        if name == "companyAudit":
            return str(_getCompany(code).audit())
        if name == "companyProfile":
            c = _getCompany(code)
            return json.dumps(
                {"corpName": c.corpName, "stockCode": c.stockCode, "facts": str(c.facts)[:500]},
                ensure_ascii=False,
                indent=2,
            )
        if name == "companySections":
            return _fmt(_getCompany(code).sections)

        if name == "marketScan":
            return _fmt(dartlab.scan(args["axis"]))

        # ── P1: 시장/거시 ──
        if name == "macroAnalysis":
            axis = args.get("axis")
            if axis:
                return _fmt(dartlab.macro(axis))
            return _fmt(dartlab.macro())

        if name == "gatherData":
            axis = args.get("axis")
            target = args.get("target")
            if axis and target:
                return _fmt(dartlab.gather(axis, target))
            elif axis:
                return _fmt(dartlab.gather(axis))
            return _fmt(dartlab.gather())

        if name == "quantAnalysis":
            c = _getCompany(code)
            metric = args.get("metric")
            if metric:
                return _fmt(c.quant(metric))
            return _fmt(c.quant())

        if name == "topdownScreen":
            market = args.get("market", "KR")
            topN = args.get("topN", 5)
            return _fmt(dartlab.topdown(market=market, topN=topN))

        # ── P2: Company 확장 ──
        if name == "companyCredit":
            c = _getCompany(code)
            axis = args.get("axis")
            if axis:
                return _fmt(c.credit(axis))
            return _fmt(c.credit())

        if name == "companyGather":
            c = _getCompany(code)
            return _fmt(c.gather(args["axis"]))

        if name == "companyQuant":
            c = _getCompany(code)
            metric = args.get("metric")
            if metric:
                return _fmt(c.quant(metric))
            return _fmt(c.quant())

        if name == "companyFilings":
            c = _getCompany(code)
            topK = args.get("topK", 10)
            return _fmt(c.filings(topK=topK))

        if name == "dartlabSearch":
            corp = args.get("corp")
            if corp:
                return _fmt(dartlab.search(args["query"], corp=corp))
            return _fmt(dartlab.search(args["query"]))

        if name == "dartlabListing":
            kind = args["kind"]
            corp = args.get("corp")
            if kind == "companies":
                return _fmt(dartlab.listing())
            elif kind == "filings":
                return _fmt(dartlab.listing("filings", corp=corp))
            elif kind == "topics":
                return _fmt(dartlab.listing("topics"))
            return _fmt(dartlab.listing())

        # ── API Discovery Tools (polars 방식 introspection) ──
        if name == "listDartlabApi":
            return _listDartlabApi()
        if name == "searchDartlabApi":
            return _searchDartlabApi(args.get("query", ""))
        if name == "verifyDartlabApi":
            return _verifyDartlabApi(args.get("apiRef", ""))

        return f"Unknown tool: {name}"

    except Exception as e:  # noqa: BLE001
        _log.error("Tool %s error: %s\n%s", name, e, traceback.format_exc())
        try:
            from dartlab.core.desk import guide

            feature = _TOOL_FEATURE_MAP.get(name, "data")
            guideMsg = guide.handleError(e, feature=feature)
            return f"Error: {e}\n\n{guideMsg}"
        except ImportError:
            return f"Error: {e}"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# API Discovery — Python introspection 기반
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def _listDartlabApi() -> str:
    """dartlab 전체 공개 API — 런타임 introspection."""
    import inspect

    import dartlab
    from dartlab.providers.dart.company import Company

    lines: list[str] = ["# dartlab API\n"]

    lines.append("## Module-level")
    for name in sorted(getattr(dartlab, "__all__", [])):
        obj = getattr(dartlab, name, None)
        if obj is None:
            continue
        kind = "class" if inspect.isclass(obj) else "function" if callable(obj) else "module"
        doc = inspect.getdoc(obj)
        summary = doc.split("\n")[0] if doc else ""
        lines.append(f"- `dartlab.{name}` ({kind}): {summary}")

    lines.append("\n## Company methods")
    for name in sorted(dir(Company)):
        if name.startswith("_"):
            continue
        obj = getattr(Company, name, None)
        if obj is None:
            continue
        if not callable(obj) and not isinstance(inspect.getattr_static(Company, name), property):
            continue
        impl = getattr(Company, f"_{name}Impl", None)
        doc = inspect.getdoc(impl or obj) or ""
        summary = doc.split("\n")[0] if doc else ""
        lines.append(f"- `Company.{name}`: {summary}")

    return "\n".join(lines)


def _searchDartlabApi(query: str) -> str:
    """dartlab API 검색 — 이름 + docstring 키워드 매칭."""
    import inspect

    import dartlab
    from dartlab.providers.dart.company import Company

    if not query.strip():
        return "query 를 지정하세요. 예: '수익성', 'show', 'scan'"

    q = query.lower()
    results: list[str] = []

    for name in getattr(dartlab, "__all__", []):
        obj = getattr(dartlab, name, None)
        if obj is None:
            continue
        doc = inspect.getdoc(obj) or ""
        if q in name.lower() or q in doc.lower():
            sig = ""
            try:
                sig = str(inspect.signature(obj))
            except (ValueError, TypeError):
                pass
            results.append(f"## dartlab.{name}{sig}\n{doc[:500]}")

    for name in sorted(dir(Company)):
        if name.startswith("_"):
            continue
        obj = getattr(Company, name, None)
        if obj is None:
            continue
        impl = getattr(Company, f"_{name}Impl", None)
        doc = inspect.getdoc(impl or obj) or ""
        if q in name.lower() or q in doc.lower():
            results.append(f"## Company.{name}\n{doc[:500]}")

    if not results:
        return f"'{query}' 에 해당하는 API 를 찾지 못했습니다."
    return "\n\n".join(results[:10])


def _verifyDartlabApi(apiRef: str) -> str:
    """dartlab API 존재 확인 + docstring 반환."""
    import inspect

    import dartlab
    from dartlab.providers.dart.company import Company

    if not apiRef.strip():
        return "apiRef 를 지정하세요. 예: 'Company.show', 'dartlab.scan'"

    if apiRef.startswith("Company."):
        name = apiRef[8:]
        obj = getattr(Company, name, None)
        if obj is None:
            return f"✗ {apiRef} 존재하지 않음"
        impl = getattr(Company, f"_{name}Impl", None)
        doc = inspect.getdoc(impl or obj) or ""
        return f"✓ {apiRef}\n\n{doc[:1000]}"

    name = apiRef.replace("dartlab.", "")
    obj = getattr(dartlab, name, None)
    if obj is None:
        return f"✗ {apiRef} 존재하지 않음"
    doc = inspect.getdoc(obj) or ""
    return f"✓ dartlab.{name}\n\n{doc[:1000]}"


# Discovery tool 정의 (TOOLS 에 추가)
_DISCOVERY_TOOLS = [
    {
        "name": "listDartlabApi",
        "description": "dartlab 전체 공개 API 목록 (런타임 introspection). 어떤 함수/메서드가 있는지 확인.",
        "params": {},
        "required": [],
    },
    {
        "name": "searchDartlabApi",
        "description": "dartlab API 검색. 키워드로 관련 함수를 찾고 docstring(시그니처/파라미터/반환값) 반환.",
        "params": {
            "query": {"type": "string", "description": "검색어 (함수명, 키워드, 설명). 예: '수익성', 'show', 'scan'"},
        },
        "required": ["query"],
    },
    {
        "name": "verifyDartlabApi",
        "description": "dartlab API 존재 확인 + 전체 docstring. 함수가 실제로 있는지, 어떤 파라미터/반환값인지 확인.",
        "params": {
            "apiRef": {
                "type": "string",
                "description": "API 참조. 예: 'Company.show', 'dartlab.scan', 'Company.analysis'",
            },
        },
        "required": ["apiRef"],
    },
]

_TOOLS.extend(_DISCOVERY_TOOLS)


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
    _log.info("MCP 서버 초기화 -- %d 도구", len(_TOOLS))

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
            for t in _TOOLS
        ]

    @app.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[TextContent]:
        _log.info("call_tool: %s(%s)", name, list(arguments.keys()))
        return [TextContent(type="text", text=_executeTool(name, arguments))]

    @app.list_resources()
    async def list_resources() -> list[Resource]:
        resources = [
            Resource(
                uri="dartlab://info",
                name="DartLab",
                description="한국 상장기업 전자공시 분석 도구 (DART)",
                mimeType="application/json",
            ),
            Resource(
                uri="dartlab://scan/profitability",
                name="전종목 수익성",
                description="전종목 영업이익률/순이익률/ROE/ROA 횡단 비교",
                mimeType="application/json",
            ),
            Resource(
                uri="dartlab://scan/growth",
                name="전종목 성장성",
                description="전종목 매출/영업이익 YoY 성장률 횡단 비교",
                mimeType="application/json",
            ),
            Resource(
                uri="dartlab://macro/종합",
                name="거시경제 종합",
                description="경제 사이클, 금리, 자산, 심리, 유동성 종합 판정",
                mimeType="application/json",
            ),
        ]
        for code in _cache:
            resources.append(
                Resource(
                    uri=f"dartlab://company/{code}/topics",
                    name=f"{code} topics",
                    description=f"{code} 조회 가능 토픽",
                    mimeType="application/json",
                )
            )
        return resources

    @app.read_resource()
    async def read_resource(uri: str) -> list[ReadResourceContents]:
        uri_str = str(uri)
        if uri_str == "dartlab://info":
            import dartlab

            return [
                ReadResourceContents(
                    content=json.dumps(
                        {
                            "version": getattr(dartlab, "__version__", "unknown"),
                            "tools": len(_TOOLS),
                            "cached": list(_cache.keys()),
                        },
                        ensure_ascii=False,
                        indent=2,
                    ),
                    mime_type="application/json",
                )
            ]
        if uri_str.startswith("dartlab://company/"):
            parts = uri_str.replace("dartlab://company/", "").split("/", 1)
            if len(parts) == 2 and parts[1] == "topics":
                return [
                    ReadResourceContents(
                        content=json.dumps(_getCompany(parts[0]).topics, ensure_ascii=False, indent=2),
                        mime_type="application/json",
                    )
                ]
        if uri_str.startswith("dartlab://scan/"):
            axis = uri_str.replace("dartlab://scan/", "")
            import dartlab

            result = dartlab.scan(axis)
            return [
                ReadResourceContents(
                    content=_fmt(result),
                    mime_type="application/json",
                )
            ]
        if uri_str.startswith("dartlab://macro/"):
            axis = uri_str.replace("dartlab://macro/", "")
            import dartlab

            result = dartlab.macro(axis)
            return [
                ReadResourceContents(
                    content=_fmt(result),
                    mime_type="application/json",
                )
            ]
        return [ReadResourceContents(content="Unknown resource", mime_type="text/plain")]

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

    servers["dartlab"] = {
        "command": "uv",
        "args": ["run", "python", "-X", "utf8", "-m", "dartlab.mcp"],
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
