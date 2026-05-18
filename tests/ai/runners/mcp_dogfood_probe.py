"""dartlab MCP 도그푸드 probe — 외부 클라이언트 입장에서 11 canonical 도구 직접 사용.

실행 ::
    uv run python -X utf8 tests/ai/runners/mcp_dogfood_probe.py

목적: pytest 가 dispatch / 거부 경로 위주로 커버할 때, 실제 호출 흐름의 happy path 마찰을
잡는 *수동 verification asset*. 도그푸드 자체가 강화 사이클의 일부 — 단위 테스트만으로는
LookAheadGuard 의 Company(market=...) 같은 외부 의존 회귀를 못 잡는다는 발견 (2026-05-09).

검증 항목 (12):
  1. ReadSkill — 분석 의도 매칭
  2. ReadCapability — API 카탈로그 검색
  3. RunPython sanity
  4. RunPython 실제 dartlab.Company.show 호출
  5. S2 sandbox os.system 차단
  6. S3 GroundingCheck 답변 검증
  7. S3 LookAheadGuard 실호출 (asOf 강제)
  7b. LookAheadGuard asOf 누락 거부
  8. S3 OutcomeLog pending 기록
  9. S4 RequestUserInput fallback
  10. S1 progress notification (1 s 임계 + 0.5 s 간격)
  11. prompts/list

판정: 각 항목 OK / MEH / FAIL. 마지막에 카운트 + 상세 출력.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys


def _proactor():
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())


def _short(text, n=180):
    s = json.dumps(text, ensure_ascii=False, default=str) if not isinstance(text, str) else text
    s = s.replace("\n", " ")
    return s[:n] + ("..." if len(s) > n else "")


async def main():
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    env["PYTHONUNBUFFERED"] = "1"
    env["DARTLAB_PROGRESS_THRESHOLD_SEC"] = "1.0"
    env["DARTLAB_PROGRESS_INTERVAL_SEC"] = "0.5"
    server = StdioServerParameters(command="dartlab", args=["mcp"], env=env)

    findings = []  # (verdict, msg)

    def note(verdict, msg):
        findings.append((verdict, msg))
        print(f"  [{verdict}] {msg}")

    print("=" * 72)
    print("dartlab MCP 도그푸드 — 11 도구 실사용")
    print("=" * 72)

    async with stdio_client(server) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()

            # ── 1. ReadSkill — 분석 시작 ───────────────────────────────
            print("\n## 1. ReadSkill('quant 예측')")
            res = await s.callTool("ReadSkill", {"query": "quant 예측", "limit": 3})
            sc = res.structuredContent or {}
            refs = sc.get("refs") or []
            print(f"  refs={len(refs)}, summary={_short(sc.get('summary'))}")
            if refs:
                top = refs[0]
                print(f"  top: id={top.get('id')}, title={_short(top.get('title'), 80)}")
                if top.get("id") in {"skill:engines.quant", "skill:engines.quant.forecast"}:
                    note("OK", "ReadSkill 이 quant 예측 의도를 정확히 매칭")
                else:
                    note("MEH", f"top match가 quant 가 아님: {top.get('id')}")
            else:
                note("FAIL", "ReadSkill refs 0 — 검색 실패")

            # ── 2. ReadCapability — 같은 의도 다른 채널 ─────────────────
            print("\n## 2. ReadCapability('quant')")
            res = await s.callTool("ReadCapability", {"query": "quant", "limit": 3})
            sc = res.structuredContent or {}
            refs = sc.get("refs") or []
            print(f"  refs={len(refs)}")
            for ref in refs[:2]:
                print(f"    - {ref.get('payload', {}).get('apiRef')} (score={ref.get('payload', {}).get('score'):.2f})")
            if any("quant" in (ref.get("payload", {}).get("apiRef") or "") for ref in refs):
                note("OK", "ReadCapability 가 quant API 발견")

            # ── 3. RunPython — 실제 분석 (sanity) ────────────────────────
            print("\n## 3. RunPython sanity")
            res = await s.callTool(
                "RunPython",
                {"code": "emit_result(values={'mode': 'dogfood', 'pid_alive': True})"},
            )
            sc = res.structuredContent or {}
            note(
                "OK" if sc.get("ok") else "FAIL",
                f"RunPython sanity ok={sc.get('ok')}, refs={len(sc.get('refs') or [])}",
            )

            # ── 4. RunPython — 실제 dartlab 호출 (cold path 포함) ──────
            print("\n## 4. RunPython — dartlab.Company('005930').show('BS')")
            try:
                res = await s.callTool(
                    "RunPython",
                    {
                        "code": (
                            "import dartlab\n"
                            "c = dartlab.Company('005930')\n"
                            "df = c.show('BS')\n"
                            "emit_result(values={'rows': df.height if df is not None else 0, 'columns': len(df.columns) if df is not None else 0})"
                        )
                    },
                )
                sc = res.structuredContent or {}
                if sc.get("ok"):
                    rows = next(
                        (r.get("payload", {}).get("value") for r in (sc.get("refs") or []) if r.get("title") == "rows"),
                        None,
                    )
                    note("OK", f"실제 dartlab API 통한 BS 로드 성공 — rows={rows}")
                else:
                    note("FAIL", f"dartlab.Company.show 실패: {_short(sc.get('summary'))}")
            except Exception as e:
                note("FAIL", f"RunPython exception: {e}")

            # ── 5. S2 sandbox 차단 ────────────────────────────────────
            print("\n## 5. S2 sandbox — os.system 차단 검증")
            res = await s.callTool(
                "RunPython", {"code": "import os\nos.system('echo blocked')\nemit_result(values={'leak': True})"}
            )
            sc = res.structuredContent or {}
            stderr = ""
            for ref in sc.get("refs") or []:
                stderr = ref.get("payload", {}).get("stderr", "") or stderr
            if not sc.get("ok") and "PermissionError" in stderr and "os.system" in stderr:
                note("OK", "차단 메시지 + 대안 안내 PermissionError 로 정확히 거부")
            else:
                note("FAIL", f"sandbox 차단 안 됨: ok={sc.get('ok')}")

            # ── 6. S3 GroundingCheck — 실 답변 검산 ──────────────────────
            print("\n## 6. GroundingCheck — 답변 검증")
            sample = "삼성전자 ROE 는 12.3% 다. 3 분기 연속 OPM > 15% 유지."
            res = await s.callTool("GroundingCheck", {"answer": sample, "refs": []})
            sc = res.structuredContent or {}
            data = sc.get("data") or {}
            print(f"  materialNumber={data.get('materialNumber')}, grounded={data.get('grounded')}")
            if data.get("materialNumber") is True and data.get("grounded") is False:
                note("OK", "수치 claim 잡고 ref 없음 → grounded=False (정확)")

            # ── 7. S3 LookAheadGuard — asOf 강제 ──────────────────────
            print("\n## 7. LookAheadGuard — asOf 강제 (실호출)")
            try:
                res = await s.callTool(
                    "LookAheadGuard",
                    {"stockCode": "005930", "asOf": "2024Q4", "topic": "BS"},
                )
                sc = res.structuredContent or {}
                if sc.get("ok"):
                    rows = sc.get("data", {}).get("rowCount", 0)
                    note("OK", f"asOf=2024Q4 BS load 성공 — {rows} rows")
                else:
                    # 실 데이터 없거나 provider 미설정이면 graceful fail.
                    note("MEH", f"호출 자체 dispatch ok 하지만 결과 fail: {_short(sc.get('summary'))}")
            except Exception as e:
                note("FAIL", f"LookAheadGuard exception: {e}")

            print("\n## 7b. LookAheadGuard — asOf 누락 거부 검증")
            res = await s.callTool("LookAheadGuard", {"stockCode": "005930", "asOf": ""})
            sc = res.structuredContent or {}
            if not sc.get("ok") and sc.get("error") == "lookahead_guard_missing_asof":
                note("OK", "asOf 누락을 명시 에러 코드로 거부")

            # ── 8. S3 OutcomeLog — pending 기록 ───────────────────────
            print("\n## 8. OutcomeLog — pending entry")
            res = await s.callTool(
                "OutcomeLog",
                {
                    "stockCode": "005930",
                    "market": "KR",
                    "date": "2026-05-09",
                    "decision": "[Dogfood] Hold — sandbox 검증용 임시 entry",
                    "theme": "DogfoodTest",
                },
            )
            sc = res.structuredContent or {}
            data = sc.get("data") or {}
            note("OK" if sc.get("ok") else "FAIL", f"OutcomeLog ok={sc.get('ok')}, wrote={data.get('wrote')}")

            # ── 9. S4 RequestUserInput — fallback ───────────────────────
            print("\n## 9. RequestUserInput — 표준 ClientSession 의 fallback")
            res = await s.callTool(
                "RequestUserInput",
                {
                    "message": "분석할 회사를 선택하세요",
                    "fields": [{"name": "company", "enum": ["005930", "AAPL"]}],
                },
            )
            sc = res.structuredContent or {}
            err = sc.get("error")
            if err in {"elicit_unsupported_or_failed", "elicit_decline", "elicit_cancel"}:
                note("OK", f"클라이언트 elicit 미지원 → server 가 fallback 깔끔히 반환 ({err})")
            else:
                note("MEH", f"unexpected: {err}")

            # ── 10. S1 progress — 2 s sleep RunPython ────────────────────
            print("\n## 10. S1 progress — 2 s sleep RunPython")
            events = []

            async def on_progress(p, total, msg):
                events.append((p, msg))

            res = await s.callTool(
                "RunPython",
                {"code": "import time\nfor _ in range(4): time.sleep(0.5)\nemit_result(values={'done': True})"},
                progress_callback=on_progress,
            )
            sc = res.structuredContent or {}
            note(
                "OK" if (sc.get("ok") and len(events) >= 1) else "FAIL",
                f"slow RunPython ok={sc.get('ok')}, progress events={len(events)}",
            )
            if events:
                print(f"  first event: progress={events[0][0]}, msg={_short(events[0][1], 80)}")

            # ── 11. prompts/list — 49 recipe ───────────────────────────
            print("\n## 11. prompts/list")
            prompts = await s.listPrompts()
            recipe_count = sum(1 for p in prompts.prompts if ".recipe." in p.name)
            note("OK" if recipe_count >= 30 else "MEH", f"recipe prompt {recipe_count} (전체 {len(prompts.prompts)})")

    # ── 결과 정리 ────────────────────────────────────────────────────
    print("\n" + "=" * 72)
    print("판정")
    print("=" * 72)
    ok = sum(1 for v, _ in findings if v == "OK")
    meh = sum(1 for v, _ in findings if v == "MEH")
    fail = sum(1 for v, _ in findings if v == "FAIL")
    print(f"  OK={ok}, MEH={meh}, FAIL={fail}")
    print()
    for v, msg in findings:
        print(f"  [{v}] {msg}")


if __name__ == "__main__":
    _proactor()
    asyncio.run(main())
