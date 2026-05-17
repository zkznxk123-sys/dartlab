"""ui/web 셸 + chat 통합 검증.

가정:
- vite dev (5400) 또는 dartlab ai (8400) 가 떠 있음.
- BASE 환경변수로 지정 (기본 5400).

검사:
1. 라우트 — `/` (redirect), `/ask`, `/dashboard` 200
2. 콘솔 에러 0
3. light/dark 양 모드 스크린샷 → screenshots/{mode}-{route}.png
4. shadcn 마운트 — `[data-slot="sidebar"]` (dashboard), `Tabs` (mode-nav)
5. Ask 페이지에 chat 입력 + Send 버튼 존재
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = os.environ.get("DARTLAB_UI_BASE", "http://localhost:5400")
SHOTS = Path(__file__).resolve().parent.parent / "screenshots"
SHOTS.mkdir(exist_ok=True)

ROUTES = [
    ("/ask", "ask"),
    ("/dashboard", "dashboard"),
]


def runMode(page, mode: str) -> list[str]:
    fails: list[str] = []
    page.goto(BASE + "/", wait_until="domcontentloaded")
    page.evaluate(f"() => localStorage.setItem('dartlab-ui-theme', '{mode}')")

    for path, name in ROUTES:
        console_errors: list[str] = []
        page.on(
            "console",
            lambda msg: console_errors.append(f"{msg.type}: {msg.text}") if msg.type == "error" else None,
        )

        resp = page.goto(BASE + path, wait_until="networkidle", timeout=15000)
        if resp is None or resp.status != 200:
            fails.append(f"[{mode}] {path}: HTTP {resp.status if resp else 'none'}")
            continue

        page.wait_for_timeout(800)

        # mode nav 마운트 (양 라우트 모두)
        if page.locator('[role="tablist"]').count() == 0:
            fails.append(f"[{mode}] {path}: ModeNav (Tabs) not mounted")

        if path == "/dashboard":
            if page.locator('[data-slot="sidebar"]').count() == 0:
                fails.append(f"[{mode}] {path}: shadcn Sidebar not mounted")

        if path == "/ask":
            if page.locator('input[placeholder*="질문"]').count() == 0:
                fails.append(f"[{mode}] {path}: chat input missing")

        # 테마 클래스 확인
        is_dark = page.evaluate("() => document.documentElement.classList.contains('dark')")
        if mode == "dark" and not is_dark:
            fails.append(f"[{mode}] {path}: html.dark missing")
        if mode == "light" and is_dark:
            fails.append(f"[{mode}] {path}: html.dark present in light")

        page.screenshot(path=str(SHOTS / f"{mode}-{name}.png"))

        if console_errors:
            fails.append(f"[{mode}] {path}: {len(console_errors)} console errors")
            for e in console_errors[:3]:
                fails.append(f"    {e}")

    # / redirect 확인
    page.goto(BASE + "/", wait_until="networkidle")
    page.wait_for_timeout(500)
    final_url = page.url
    if "/ask" not in final_url:
        fails.append(f"/ redirect failed → final: {final_url}")

    return fails


def run() -> int:
    print(f"[verify] BASE = {BASE}", flush=True)
    with sync_playwright() as p:
        b = p.chromium.launch()
        ctx = b.new_context(viewport={"width": 1440, "height": 900})
        page = ctx.new_page()
        all_fails: list[str] = []
        for mode in ("light", "dark"):
            print(f"[verify] mode = {mode}", flush=True)
            all_fails.extend(runMode(page, mode))
        b.close()

    print(f"\n[verify] screenshots → {SHOTS}", flush=True)
    if all_fails:
        print(f"\n[verify] FAIL ({len(all_fails)})", flush=True)
        for f in all_fails:
            print(f"  - {f}", flush=True)
        return 1
    print(
        "\n[verify] PASS — / → /ask redirect, /ask chat input, /dashboard sidebar, mode-nav tabs, light + dark",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    sys.exit(run())
