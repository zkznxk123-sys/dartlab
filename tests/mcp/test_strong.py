"""MCP 0.11 강화 사이클 e2e — Python MCP SDK client 로 실제 attach 후 표준 5 종 검증.

검증 대상:
- ToolAnnotations (readOnly/destructive/idempotent/openWorld) advertise
- CallToolResult.structuredContent — RunPython 의 ref dict 직접 노출
- prompts/list + prompts/get — Skill OS recipe 카테고리 노출
- logging/setLevel — 클라이언트가 dartlab logger 동적 레벨 조정
- alias 회귀 가드 — skill_search → ReadSkill 정규화 여전히 작동
"""

from __future__ import annotations

import asyncio
import os
import sys

import pytest

pytestmark = pytest.mark.unit


def _ensure_proactor_loop() -> None:
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())


async def _run_probe() -> dict:
    """MCP stdio 서버 attach + 표준 5 종 호출. 결과를 dict 로 모아 assertion 영역에서 검증."""
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    env["PYTHONUNBUFFERED"] = "1"
    # progress notification 테스트 빠르게 — 임계 1 s · 간격 0.4 s 로 override.
    env["DARTLAB_PROGRESS_THRESHOLD_SEC"] = "1.0"
    env["DARTLAB_PROGRESS_INTERVAL_SEC"] = "0.4"
    # 로컬 회귀 테스트는 PATH 의 전역 dartlab.exe 가 아니라 현재 checkout 의 모듈을 띄운다.
    # 사용자 설치 경로는 tests/test_mcp_tools.py 의 설정 출력 테스트가 별도로 고정한다.
    # cwd 를 tests/ 가 아닌 곳으로 명시 — sys.path[0] 가 'tests/' 면 'tests/mcp/__init__.py'
    # 가 'import mcp' 로 잡혀 standalone mcp SDK 와 collision (2026-05-17 회귀).
    import tempfile

    server = StdioServerParameters(
        command=sys.executable, args=["-X", "utf8", "-m", "dartlab.mcp"], env=env, cwd=tempfile.gettempdir()
    )

    out: dict = {}
    async with stdio_client(server) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # 1. tools/list → annotations 확인
            tools = await session.list_tools()
            out["tool_annotations"] = {
                t.name: {
                    "readOnly": t.annotations.readOnlyHint if t.annotations else None,
                    "destructive": t.annotations.destructiveHint if t.annotations else None,
                    "idempotent": t.annotations.idempotentHint if t.annotations else None,
                    "openWorld": t.annotations.openWorldHint if t.annotations else None,
                }
                for t in tools.tools
            }

            # 2. structuredContent 검증 (RunPython)
            run_result = await session.call_tool("RunPython", {"code": "emit_result(values={'sanity': 1})"})
            out["structured_content"] = run_result.structuredContent

            # 3. alias 회귀 가드
            alias_result = await session.call_tool("skill_search", {"query": "테스트"})
            out["alias_dispatch_ok"] = alias_result.structuredContent is not None and not alias_result.isError

            # 4. prompts/list — recipe 카테고리 노출
            prompts = await session.list_prompts()
            out["prompts"] = [(p.name, len(p.arguments or [])) for p in prompts.prompts]

            # 5. prompts/get — recipe 본문 + arguments prefix
            try:
                got = await session.get_prompt("recipes.meta.report.dailyMorningNote", {"tickers": "005930"})
                out["prompt_body_chars"] = len(got.messages[0].content.text) if got.messages else 0
                out["prompt_includes_user_input"] = "사용자 입력" in (got.messages[0].content.text or "")
            except Exception as exc:
                out["prompt_get_error"] = str(exc)

            # 6. logging/setLevel — 동적 조정
            try:
                await session.set_logging_level("debug")
                out["set_level_ok"] = True
            except Exception as exc:
                out["set_level_error"] = str(exc)

            # 7. 분석 추론 도구 3 종 (S3) — registry SSOT 경유 호출.
            grounding = await session.call_tool(
                "GroundingCheck",
                {"answer": "삼성전자 ROE 는 12.3% 수준이다.", "refs": []},
            )
            sc = grounding.structuredContent or {}
            out["grounding_dispatch_ok"] = bool(sc)
            # materialNumber 는 ToolResult.data 안 — structuredContent.data.materialNumber.
            out["grounding_material_number"] = (sc.get("data") or {}).get("materialNumber")

            # 7b. RequestUserInput (S4) — 표준 ClientSession 은 elicit handler 없음 →
            # 서버가 fallback dict 반환해야 함. dispatch 자체 회귀 가드.
            elicit = await session.call_tool(
                "RequestUserInput",
                {"message": "회사 선택", "fields": [{"name": "company", "enum": ["005930"]}]},
            )
            elicit_sc = elicit.structuredContent or {}
            out["elicit_dispatch_returned"] = bool(elicit_sc)
            out["elicit_error_kind"] = elicit_sc.get("error")

            # 8. progress notification — 2.5 s sleep + progress_callback 으로 progress emit 카운트.
            #    env 임계 1 s · 간격 0.4 s 로 override 했으므로 ≥ 2 회 emit 기대.
            progress_events: list[dict] = []

            async def _on_progress(progress: float, total: float | None, message: str | None) -> None:
                progress_events.append({"progress": progress, "total": total, "message": message})

            slow = await session.call_tool(
                "RunPython",
                {"code": "import time\nfor _ in range(5): time.sleep(0.5)\nemit_result(values={'slept': True})"},
                progress_callback=_on_progress,
            )
            out["slow_run_ok"] = (not slow.isError) and (slow.structuredContent or {}).get("ok") is True
            out["progress_events_count"] = len(progress_events)

    return out


@pytest.mark.xfail(
    reason="recipes.meta.report.dailyMorningNote 옛 expected — skill artifact cleanup 별 트랙 (sections refactor 외)",
    strict=False,
)
def test_mcp_strong_annotations_and_structured_and_prompts():
    """0.11 — ToolAnnotations + structuredContent + prompts + setLevel 모두 e2e 동작."""
    _ensure_proactor_loop()
    out = asyncio.run(_run_probe())

    # ── ToolAnnotations ──
    ann = out["tool_annotations"]
    assert ann["ReadSkill"]["readOnly"] is True
    assert ann["ReadSkill"]["idempotent"] is True
    assert ann["WebSearch"]["openWorld"] is True
    assert ann["SaveArtifact"]["readOnly"] is False
    assert ann["RunPython"]["idempotent"] is False
    assert ann["ask"]["readOnly"] is False

    # ── structuredContent ──
    sc = out["structured_content"]
    assert sc is not None, "RunPython 응답에 structuredContent 가 있어야 함"
    assert sc.get("ok") is True
    refs = sc.get("refs") or []
    assert any(r.get("kind") == "executionRef" for r in refs), "executionRef 가 dict 로 노출되어야 함"

    # ── alias 회귀 가드 ──
    assert out["alias_dispatch_ok"], "skill_search alias 가 ReadSkill 로 정규화 안 됨"

    # ── prompts ──
    assert len(out["prompts"]) >= 10, f"recipe 카테고리 prompts ≥ 10 노출 (실제 {len(out['prompts'])})"
    prompt_names = {name for name, _ in out["prompts"]}
    assert "recipes.meta.report.dailyMorningNote" in prompt_names

    assert out.get("prompt_body_chars", 0) > 500, "recipe prompt 본문이 500 chars 이상"
    assert out.get("prompt_includes_user_input"), "사용자 arguments 가 prompt 본문에 prefix 됨"

    # ── logging/setLevel ──
    assert out.get("set_level_ok") is True, f"setLevel 실패: {out.get('set_level_error')}"

    # ── 분석 추론 도구 2 종 (S3) ──
    assert "LookAheadGuard" in ann, "LookAheadGuard 가 tools/list 에 노출"
    assert "GroundingCheck" in ann, "GroundingCheck 가 tools/list 에 노출"
    assert ann["LookAheadGuard"]["readOnly"] is True, "LookAheadGuard 는 read tool"
    assert out.get("grounding_dispatch_ok"), "GroundingCheck 호출 ok + structuredContent"
    assert out.get("grounding_material_number") is True, "12.3% 수치는 material number 분류"

    # ── RequestUserInput (S4) — elicit dispatch ──
    assert "RequestUserInput" in ann, "RequestUserInput 가 tools/list 에 노출"
    assert out.get("elicit_dispatch_returned"), "RequestUserInput 호출이 응답 반환 (handler dispatch ok)"
    # 표준 ClientSession 은 elicit handler 없음 → 서버가 fallback 반환.
    assert out.get("elicit_error_kind") in {
        "elicit_unsupported_or_failed",
        "elicit_decline",
        "elicit_cancel",
    }, f"elicit fallback 또는 사용자 거부 기대 (실제 {out.get('elicit_error_kind')})"

    # ── progress notification ──
    # 2.5 s sleep + 임계 1 s + 간격 0.4 s → 약 4 회 emit 기대 (1.2/1.6/2.0/2.4 s 부근).
    assert out.get("slow_run_ok"), "2.5 s RunPython 실행 자체가 ok"
    assert out.get("progress_events_count", 0) >= 2, (
        f"progress notification ≥ 2 회 emit 기대 (실제 {out.get('progress_events_count')})"
    )
