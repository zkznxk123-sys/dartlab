"""Playwright Visual Loop — dashboard 화면 캡처 + 정량 측정 CLI.

목적:
1. AI 가 catalog 수정 후 화면 안 보고 완료 보고하는 회귀 차단 (PNG snap).
2. PNG 어림짐작 금지 — 카드별 boundingBox + chart/mini-table 영역 + 겹침 px 정량
   측정 (measureCards). v3-r5 의 다섯 차례 회귀 차단 룰
   ([[feedback_dashboard_world_class_assets]]).

사용:
    uv run python -X utf8 src/dartlab/viz/dashboardSnap.py \\
        --code 005930 --out .claude/snaps/ \\
        [--measure]  # JSON 측정 결과 동시 저장

옵션:
    --code STR    종목코드 (default 005930).
    --views STR   캡처할 view list (콤마 또는 'all'). default 'financial' (v3-r6 1 view).
    --out PATH    출력 디렉토리 (default .claude/snaps).
    --base URL    frontend dev server (default http://127.0.0.1:5400).
    --period STR  annual/quarterly (default quarterly).
    --width INT   viewport 폭 (default 1920).
    --height INT  viewport 높이 (default 1200).
    --wait MS     screenshot 전 대기 (default 2500 — recharts 애니메이션).
    --measure     PNG + 카드별 metric JSON 동시 저장 (`<out>/<view>.metrics.json`).

설계:
    Playwright chromium headless. URL 진입 → networkidle + wait → full_page
    screenshot. recharts ResponsiveContainer 가 width=100% 라 viewport 영향
    큼 — 1920×1200 표준.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any

# v3-r6 — sub view 7 일시 폐기. 단일 "financial" 1 view.
LEGACY_FINANCIAL_VIEWS = ("story", "dupont", "value", "growth", "credit", "quality", "snowflake")
ANALYSIS_TABS = ("viewer",)


async def measureCards(page: Any) -> list[dict[str, Any]]:
    """카드별 boundingBox + chart canvas + mini-table 좌표 + 겹침 px 측정.

    Returns:
        list of {cardKey, box, chartBox, tableBox, overlapPx, chrome:
        {headerPx, footerPx, contentPx}}.
        v3-r5 PNG 어림짐작 회귀 차단 — JSON 정량 metric 직접 검수.
    """
    # CardShell 의 wrapper 는 BentoGrid 의 직접 자식 div (grid-column span ...).
    cardHandles = await page.locator('div.grid > div').all()
    metrics: list[dict[str, Any]] = []
    for h in cardHandles:
        try:
            box = await h.bounding_box()
        except Exception:  # noqa: BLE001
            box = None
        if not box:
            continue
        title = ""
        try:
            titleEl = h.locator('[data-slot="card-title"], .text-xs.font-medium').first
            if await titleEl.count():
                title = (await titleEl.inner_text()).strip()
        except Exception:  # noqa: BLE001
            pass
        chartBox = None
        try:
            chart = h.locator('.recharts-surface, svg.recharts-surface').first
            if await chart.count():
                chartBox = await chart.bounding_box()
        except Exception:  # noqa: BLE001
            pass
        tableBox = None
        try:
            table = h.locator('table').first
            if await table.count():
                tableBox = await table.bounding_box()
        except Exception:  # noqa: BLE001
            pass
        overlapPx = 0.0
        if chartBox and tableBox:
            chartBottom = chartBox["y"] + chartBox["height"]
            tableTop = tableBox["y"]
            if chartBottom > tableTop:
                overlapPx = round(chartBottom - tableTop, 1)
        # chrome (header + footer + padding) — 카드 outer 와 chart canvas px 차이.
        contentPx = chartBox["height"] if chartBox else 0
        chromePx = box["height"] - contentPx if chartBox else 0
        metrics.append(
            {
                "title": title,
                "box": {k: round(v, 1) for k, v in box.items()},
                "chartBox": {k: round(v, 1) for k, v in chartBox.items()} if chartBox else None,
                "tableBox": {k: round(v, 1) for k, v in tableBox.items()} if tableBox else None,
                "overlapPx": overlapPx,
                "chromePx": round(chromePx, 1),
                "densityPct": round(contentPx / box["height"] * 100, 1) if box["height"] else 0,
            }
        )
    return metrics


async def snapPage(
    url: str,
    outPath: Path,
    *,
    viewport: tuple[int, int] = (1920, 1200),
    waitMs: int = 2500,
    measure: bool = False,
) -> dict[str, Any] | None:
    """단일 URL 캡처 + (옵션) 카드별 metric 측정."""
    from playwright.async_api import async_playwright

    metrics: dict[str, Any] | None = None
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": viewport[0], "height": viewport[1]})
        try:
            # v3-r6 — networkidle 은 backend 14 카드 build 시 timeout. domcontentloaded + 충분 wait.
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_timeout(waitMs + 5000)  # backend spec build 대기 추가 5s
            outPath.parent.mkdir(parents=True, exist_ok=True)
            await page.screenshot(path=str(outPath), full_page=True)
            print(f"[snap] {url} -> {outPath}")
            if measure:
                cardMetrics = await measureCards(page)
                metrics = {
                    "url": url,
                    "viewport": {"w": viewport[0], "h": viewport[1]},
                    "cardCount": len(cardMetrics),
                    "totalOverlapPx": round(sum(c["overlapPx"] for c in cardMetrics), 1),
                    "avgDensityPct": round(
                        sum(c["densityPct"] for c in cardMetrics) / len(cardMetrics), 1
                    )
                    if cardMetrics
                    else 0,
                    "cards": cardMetrics,
                }
                metricsPath = outPath.with_suffix(".metrics.json")
                metricsPath.write_text(json.dumps(metrics, indent=2, ensure_ascii=False), encoding="utf-8")
                print(
                    f"[measure] {len(cardMetrics)} cards, "
                    f"overlap={metrics['totalOverlapPx']}px, "
                    f"density={metrics['avgDensityPct']}% -> {metricsPath}"
                )
        finally:
            await browser.close()
    return metrics


async def snapDashboard(
    code: str,
    views: list[str],
    *,
    base: str = "http://127.0.0.1:5400",
    outDir: Path,
    period: str = "quarterly",
    viewport: tuple[int, int] = (1920, 1200),
    waitMs: int = 2500,
    measure: bool = False,
) -> None:
    """재무분석 1 view (v3-r6) + 다른 탭 캡처."""
    targets: list[tuple[str, Path]] = []

    # 재무분석 1 view (view 없음 → OVERVIEW_KEYS curated).
    if "financial" in views or "all" in views or "overview" in views:
        url = f"{base}/analysis/{code}/financial?period={period}"
        targets.append((url, outDir / "financial.png"))

    # legacy sub view (필요시).
    for v in views:
        if v in LEGACY_FINANCIAL_VIEWS:
            url = f"{base}/analysis/{code}/financial?view={v}&period={period}"
            targets.append((url, outDir / f"financial-{v}.png"))

    # 다른 탭.
    for t in ANALYSIS_TABS:
        if t in views or "all" in views:
            url = f"{base}/analysis/{code}/{t}?period={period}"
            targets.append((url, outDir / f"{t}.png"))

    for url, outPath in targets:
        await snapPage(url, outPath, viewport=viewport, waitMs=waitMs, measure=measure)


def main() -> int:
    """CLI 진입점."""
    parser = argparse.ArgumentParser(description="Dashboard Playwright snap + measure CLI")
    parser.add_argument("--code", default="005930", help="종목코드")
    parser.add_argument("--views", default="financial", help="콤마 list 또는 'all' (default v3-r6 1 view)")
    parser.add_argument("--out", type=Path, default=Path(".claude/snaps"), help="출력 디렉토리")
    parser.add_argument("--base", default="http://127.0.0.1:5400", help="frontend dev server URL")
    parser.add_argument("--period", default="quarterly", choices=["annual", "quarterly"])
    parser.add_argument("--width", type=int, default=1920)
    parser.add_argument("--height", type=int, default=1200)
    parser.add_argument("--wait", type=int, default=2500, help="screenshot 전 대기 ms")
    parser.add_argument(
        "--measure", action="store_true", help="카드별 metric JSON 동시 저장 (PNG 어림짐작 금지)"
    )
    args = parser.parse_args()

    if args.views == "all":
        views = ["financial"] + list(LEGACY_FINANCIAL_VIEWS) + list(ANALYSIS_TABS) + ["all"]
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
            measure=args.measure,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
