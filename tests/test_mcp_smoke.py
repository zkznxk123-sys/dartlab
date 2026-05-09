"""MCP stdio cold-start smoke test — initialize 왕복 + duplicate logger 가드 회귀."""

from __future__ import annotations

import os
import subprocess
import sys
import time

import pytest

pytestmark = pytest.mark.unit


def _spawn_mcp_stdio() -> subprocess.Popen:
    """`python -X utf8 -m dartlab.mcp` 를 stdio 서버로 spawn."""
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    env["PYTHONUTF8"] = "1"
    return subprocess.Popen(
        [sys.executable, "-X", "utf8", "-m", "dartlab.mcp"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        bufsize=0,
    )


def test_mcp_stdio_starts_and_logs_each_message_once():
    """서버 부팅 stderr 가드 — '초기화' / '시작' 메시지가 정확히 1 회씩 출력.

    duplicate logger handler 회귀를 잡는다 (이슈 #28 의 ② 가설).
    """
    proc = _spawn_mcp_stdio()
    try:
        # 부팅 후 stderr 가 모두 flush 될 시간 확보. Windows + Proactor 환경에서 flush
        # 지연이 발생해 2 s 는 종종 비어 있는 stderr 로 false fail. 4 s 로 여유.
        time.sleep(4.0)
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=2)

    stderr_text = proc.stderr.read().decode("utf-8", errors="replace") if proc.stderr else ""

    # 메시지 갯수 검증 — 각 정확히 1 회.
    init_count = stderr_text.count("MCP 서버 초기화 완료")
    start_count = stderr_text.count("DartLab MCP 서버 시작 (stdio)")
    assert init_count == 1, f"기대 1, 실제 {init_count} — duplicate logger handler 회귀? stderr={stderr_text!r}"
    assert start_count == 1, f"기대 1, 실제 {start_count} — duplicate logger handler 회귀? stderr={stderr_text!r}"


def test_mcp_create_server_cold_path_under_threshold():
    """create_server() 가 timeout 임계 안에 끝나는지 — Claude Desktop attach 가드.

    측정 대상: import dartlab.mcp + create_server() 합계.
    임계: 5 초 (Claude Desktop ~23 초 timeout 대비 충분히 여유).
    회귀 시 PEP 562 lazy 이탈 또는 module-top eager import 추가 가능성.
    """
    code = (
        "import time, sys\n"
        "t0 = time.perf_counter()\n"
        "from dartlab.mcp import create_server\n"
        "create_server()\n"
        "t1 = time.perf_counter()\n"
        "sys.stdout.write(f'{(t1-t0)*1000:.0f}\\n')\n"
    )
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    result = subprocess.run(
        [sys.executable, "-X", "utf8", "-c", code],
        capture_output=True,
        text=True,
        env=env,
        timeout=30,
    )
    assert result.returncode == 0, f"create_server() 부팅 실패: {result.stderr}"
    elapsed_ms = float(result.stdout.strip().splitlines()[-1])
    assert elapsed_ms < 5000, (
        f"create_server() cold path {elapsed_ms:.0f} ms — 5000 ms 임계 초과. "
        "PEP 562 lazy 이탈 또는 module-top eager import 회귀 가능성."
    )
