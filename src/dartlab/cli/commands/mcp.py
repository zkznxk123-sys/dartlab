"""dartlab mcp — MCP 서버 실행."""

from __future__ import annotations

import sys


def _stdioServerConfig() -> dict:
    """uv tool install / pipx install 가 만든 entry point (`dartlab` / `dartlab.exe`) 직접 호출.

    이슈 #28 follow-up: Microsoft Store Python 환경에선 `python` 이 PATH 의 App Execution
    Alias stub 이라 Claude Desktop subprocess.spawn 이 ENOENT 로 실패. dartlab entry point
    exe 직접 호출은 PATH 검색 의존이 가벼워 spawn 안전.
    """
    return {
        "mcpServers": {
            "dartlab": {
                "command": "dartlab",
                "args": ["mcp"],
                "env": {"PYTHONUNBUFFERED": "1", "PYTHONUTF8": "1"},
            }
        }
    }


def _stdioServerConfigPythonFallback() -> dict:
    """python -m fallback. uv tool / pipx 미설치 환경 + python 이 PATH stub 아닐 때만."""
    return {
        "mcpServers": {
            "dartlab": {
                "command": "python",
                "args": ["-X", "utf8", "-m", "dartlab.mcp"],
                "env": {"PYTHONUNBUFFERED": "1"},
            }
        }
    }


def configureParser(subparsers) -> None:
    """mcp 서브커맨드 등록 — MCP 서버 stdio 실행."""
    parser = subparsers.add_parser("mcp", help="MCP 서버 실행 (stdio)")
    parser.add_argument(
        "--config",
        choices=["claude-desktop", "claude-code", "cursor"],
        help="지정한 클라이언트의 설정 예시를 출력합니다.",
    )
    parser.add_argument(
        "--install",
        action="store_true",
        help="현재 디렉토리에 .mcp.json을 자동 생성합니다.",
    )
    parser.set_defaults(handler=_run)


def _printConfig(client: str) -> None:
    """MCP 클라이언트 설정 예시 출력."""
    import json

    primary = _stdioServerConfig()
    fallback = _stdioServerConfigPythonFallback()
    note = (
        "# 사전 설치 필요: uv tool install dartlab   (또는: pipx install dartlab)\n"
        "# 이 형식은 .local/bin/dartlab(.exe) entry point 를 직접 호출하므로 spawn 이 안전합니다.\n"
        '# Microsoft Store Python 환경에서 `command: "python"` 이 ENOENT 로 실패하는 이슈를 회피합니다 (#28).\n'
    )

    if client == "claude-desktop":
        # Claude Desktop: ~/AppData/Roaming/Claude/claude_desktop_config.json (Windows)
        #                  ~/Library/Application Support/Claude/claude_desktop_config.json (macOS)
        if sys.platform == "win32":
            path = r"%APPDATA%\Claude\claude_desktop_config.json"
        else:
            path = "~/Library/Application Support/Claude/claude_desktop_config.json"
        print(f"# Claude Desktop 설정 파일: {path}")
        print("# 아래 내용을 mcpServers 에 추가하세요.\n")
        print(note)
        print(json.dumps(primary, indent=2, ensure_ascii=False))
        print()
        print("# 대안 — `dartlab` 명령이 PATH 에 없는 경우:")
        print(json.dumps(fallback, indent=2, ensure_ascii=False))

    elif client == "claude-code":
        # Claude Code: ~/.claude/settings.json 또는 프로젝트 .claude/settings.json
        print("# Claude Code 설정")
        print("# 방법 1: 글로벌 설정 (~/.claude/settings.json)")
        print("# 방법 2: 프로젝트 설정 (.claude/settings.json)")
        print("# 아래 내용을 mcpServers 에 추가하세요.\n")
        print(note)
        print(json.dumps(primary, indent=2, ensure_ascii=False))
        print()
        print("# 또는 CLI 한 줄:")
        print("#   claude mcp add dartlab -- dartlab mcp")
        print()
        print("# 대안 — `dartlab` 명령이 PATH 에 없는 경우:")
        print(json.dumps(fallback, indent=2, ensure_ascii=False))

    elif client == "cursor":
        print("# Cursor 설정: .cursor/mcp.json")
        print("# 아래 내용을 추가하세요.\n")
        print(note)
        print(json.dumps(primary, indent=2, ensure_ascii=False))
        print()
        print("# 대안 — `dartlab` 명령이 PATH 에 없는 경우:")
        print(json.dumps(fallback, indent=2, ensure_ascii=False))


def _run(args) -> None:
    """설정 출력, 자동 설치, 또는 MCP stdio 서버를 시작한다."""
    if args.config:
        _printConfig(args.config)
        return

    if args.install:
        from dartlab.mcp import installMcpConfig

        result = installMcpConfig()
        print(result)
        return

    from dartlab.mcp import runStdio

    runStdio()
