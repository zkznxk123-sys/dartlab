"""Playwright Visual Loop — dashboard 화면 캡처 CLI.

목적: AI 가 catalog 수정 후 화면 안 보고 "완료" 보고하는 회귀 차단.
각 commit 후 snap → AI 가 Read tool 로 PNG 시각 검수 → 결함 0 까지 loop.

사용:
    uv run python -X utf8 src/dartlab/viz/dashboardSnap.py \\
        --code 005930 --views all \\
        --out .claude/snaps/

옵션:
    --code STR    종목코드 (default 005930).
    --views STR   캡처할 view list (콤마 또는 'all'). default 'overview'.
    --out PATH    출력 디렉토리 (default .claude/snaps).
    --base URL    frontend dev server (default http://127.0.0.1:5400).
    --period STR  annual/quarterly (default quarterly).
    --width INT   viewport 폭 (default 1920).
    --height INT  viewport 높이 (default 1200).
    --wait MS     screenshot 전 대기 (default 2500 — recharts 애니메이션).

설계:
    Playwright chromium headless. 한 페이지 진입 → networkidle + wait_for_timeout →
    full_page screenshot. recharts ResponsiveContainer 가 width=100% 라 viewport
    영향 큼 — 1920×1200 표준 (xl breakpoint 보장).
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

FINANCIAL_VIEWS = ("story", "dupont", "value", "growth", "credit", "quality", "snowflake")
ANALYSIS_TABS = ("viewer",)


async def snapPage(
    url: str,
    outPath: Path,
    *,
    viewport: tuple[int, int] = (1920, 1200),
    waitMs: int = 2500,
) -> None:
    """단일 URL 캡처."""
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": viewport[0], "height": viewport[1]})
        try:
            await page.goto(url, wait_until="networkidle", timeout=30000)
            await page.wait_for_timeout(waitMs)
            outPath.parent.mkdir(parents=True, exist_ok=True)
            await page.screenshot(path=str(outPath), full_page=True)
            print(f"[snap] {url} → {outPath}")
        finally:
            await browser.close()


async def snapDashboard(
    code: str,
    views: list[str],
    *,
    base: str = "http://127.0.0.1:5400",
    outDir: Path,
    period: str = "quarterly",
    viewport: tuple[int, int] = (1920, 1200),
    waitMs: int = 2500,
) -> None:
    """재무제표 sub view N 개 + 7 탭 캡처."""
    targets: list[tuple[str, str]] = []

    # 재무제표 sub view.
    for v in views:
        if v in FINANCIAL_VIEWS:
            url = f"{base}/analysis/{code}/financial?view={v}&period={period}"
            outPath = outDir / f"financial-{v}.png"
            targets.append((url, str(outPath)))

    # 다른 탭.
    for t in ANALYSIS_TABS:
        if t in views or "all" in views:
            url = f"{base}/analysis/{code}/{t}?period={period}"
            outPath = outDir / f"{t}.png"
            targets.append((url, str(outPath)))

    for url, outPath in targets:
        await snapPage(url, Path(outPath), viewport=viewport, waitMs=waitMs)


def main() -> int:
    """CLI 진입점."""
    parser = argparse.ArgumentParser(description="Dashboard Playwright snap CLI")
    parser.add_argument("--code", default="005930", help="종목코드")
    parser.add_argument("--views", default="overview", help="콤마 list 또는 'all'")
    parser.add_argument("--out", type=Path, default=Path(".claude/snaps"), help="출력 디렉토리")
    parser.add_argument("--base", default="http://127.0.0.1:5400", help="frontend dev server URL")
    parser.add_argument("--period", default="quarterly", choices=["annual", "quarterly"])
    parser.add_argument("--width", type=int, default=1920)
    parser.add_argument("--height", type=int, default=1200)
    parser.add_argument("--wait", type=int, default=2500, help="screenshot 전 대기 ms")
    args = parser.parse_args()

    if args.views == "all":
        views = list(FINANCIAL_VIEWS) + list(ANALYSIS_TABS) + ["all"]
    else:
        views = [v.strip() for v in args.views.split(",")]

    asyncio.run(
        snapDashboard(
            args.code,
            views,
            base=args.base,
            outDir=args.out,
            period=args.period,
            viewport=(args.width, args.height),
            waitMs=args.wait,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
