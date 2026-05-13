"""MCP transport entry points."""

from __future__ import annotations

from dartlab.mcp.server import createServer, mcpLog


def runStdio() -> None:
    """stdio 모드로 MCP 서버를 실행한다.

    Returns:
        None: 서버 event loop 를 종료될 때까지 실행한다.

    Example:
        `runStdio()`

    Raises:
        ImportError: MCP stdio transport 를 import 할 수 없을 때.
    """
    import asyncio

    try:
        from mcp.server.stdio import stdio_server
    except ImportError as exc:
        raise ImportError("MCP SDK 필요: pip install --upgrade dartlab") from exc

    app = createServer()

    async def main() -> None:
        """stdio stream 을 열고 MCP server 를 실행한다.

        Returns:
            None: stream 이 닫힐 때까지 server run 을 수행한다.

        Example:
            `await main()`

        Raises:
            RuntimeError: stdio transport 연결 또는 server run 이 실패할 때.
        """
        async with stdio_server() as (readStream, writeStream):
            mcpLog.info("DartLab MCP 서버 시작 (stdio)")
            await app.run(readStream, writeStream, app.create_initialization_options())

    asyncio.run(main())


def createSseApp():
    """SSE 전송 기반 ASGI 앱을 생성한다.

    Returns:
        Starlette: `/sse` 와 `/messages/` route 를 가진 ASGI 앱.

    Example:
        `app = createSseApp()`

    Raises:
        ImportError: MCP SSE transport 또는 Starlette 를 import 할 수 없을 때.
    """
    from mcp.server.sse import SseServerTransport
    from starlette.applications import Starlette
    from starlette.routing import Mount, Route

    mcpServer = createServer()
    sse = SseServerTransport("/messages/")

    async def handleSse(request):
        """SSE 연결 handshake 로 MCP 양방향 stream 을 연다.

        Args:
            request: Starlette Request 객체.

        Returns:
            None: 연결 생명주기 동안 MCP server run 을 수행한다.

        Example:
            `await handleSse(request)`

        Raises:
            RuntimeError: SSE transport 연결 또는 MCP server run 이 실패할 때.
        """
        async with sse.connect_sse(request.scope, request.receive, request._send) as (read, write):
            await mcpServer.run(read, write, mcpServer.create_initialization_options())

    return Starlette(
        routes=[
            Route("/sse", endpoint=handleSse),
            Mount("/messages/", app=sse.handle_post_message),
        ],
    )


def runSse(host: str = "0.0.0.0", port: int = 8001) -> None:
    """SSE 모드로 MCP HTTP 서버를 실행한다.

    Args:
        host: bind host.
        port: bind port.

    Returns:
        None: uvicorn 서버를 종료될 때까지 실행한다.

    Example:
        `runSse(host="127.0.0.1", port=8001)`

    Raises:
        ImportError: uvicorn 또는 SSE app 의 의존성을 import 할 수 없을 때.
    """
    import uvicorn

    mcpLog.info("DartLab MCP 서버 시작 (SSE http://%s:%d/sse)", host, port)
    uvicorn.run(createSseApp(), host=host, port=port)
