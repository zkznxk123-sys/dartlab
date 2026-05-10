from __future__ import annotations

import argparse
import json
import statistics
import sys
from dataclasses import asdict, dataclass
from time import perf_counter
from typing import Any

from playwright.sync_api import Page, sync_playwright
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError


@dataclass
class BenchResult:
    name: str
    ok: bool
    duration_ms: float
    detail: dict[str, Any]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="브라우저에서 DartLab HF runtime 화면 성능을 측정한다.")
    parser.add_argument("--base-url", default="http://127.0.0.1:5179")
    parser.add_argument("--iterations", type=int, default=2)
    parser.add_argument("--scan-budget-ms", type=float, default=1500)
    parser.add_argument("--finance-budget-ms", type=float, default=700)
    parser.add_argument("--company-budget-ms", type=float, default=2000)
    parser.add_argument("--price-wait-ms", type=int, default=0)
    parser.add_argument("--report-budget-ms", type=float, default=3000)
    parser.add_argument("--detail-budget-ms", type=float, default=1800)
    parser.add_argument("--include-hf-range-lab", action="store_true")
    parser.add_argument("--hf-range-budget-ms", type=float, default=3000)
    parser.add_argument("--strict", action="store_true", help="budget 실패 시 exit 1")
    parser.add_argument("--json", action="store_true", help="JSON만 출력")
    return parser.parse_args()


def browser_stats(page: Page) -> dict[str, Any]:
    return page.evaluate(
        """() => {
            const resources = performance.getEntriesByType('resource');
            const hf = resources.filter((r) =>
                r.name.includes('huggingface.co') ||
                r.name.includes('hf.co') ||
                r.name.includes('cas-bridge.xethub.hf.co')
            );
            const duck = resources.filter((r) =>
                r.name.includes('duckdb') || r.name.includes('parquet')
            );
            const sum = (items, key) => items.reduce((acc, item) => acc + (item[key] || 0), 0);
            return {
                resourceCount: resources.length,
                hfRequestCount: hf.length,
                duckOrParquetRequestCount: duck.length,
                transferSize: sum(resources, 'transferSize'),
                encodedBodySize: sum(resources, 'encodedBodySize'),
                hfTransferSize: sum(hf, 'transferSize'),
                hfEncodedBodySize: sum(hf, 'encodedBodySize'),
                lastResources: resources.slice(-8).map((r) => ({
                    name: r.name,
                    transferSize: r.transferSize || 0,
                    encodedBodySize: r.encodedBodySize || 0,
                    duration: r.duration || 0
                }))
            };
        }"""
    )


def page_text(page: Page) -> str:
    try:
        return page.locator("body").inner_text(timeout=10_000)
    except PlaywrightTimeoutError:
        return ""


def run_scan(page: Page, baseUrl: str, budget_ms: float) -> BenchResult:
    t0 = perf_counter()
    try:
        resp = page.goto(f"{baseUrl}/scan", wait_until="domcontentloaded", timeout=60_000)
        page.get_by_text("Scan Studio").first.wait_for(timeout=30_000)
        duration_ms = (perf_counter() - t0) * 1000
        page.wait_for_timeout(1000)
        text = page_text(page)
        stats = browser_stats(page)
        detail = {
            "status": resp.status if resp else None,
            "hasScanStudio": "Scan Studio" in text,
            "hasTrendManual": "추세 수동" in text,
            "buttons": page.locator("button").count(),
            "svg": page.locator("svg").count(),
            **stats,
        }
        return BenchResult("scan_initial", duration_ms <= budget_ms, duration_ms, detail)
    except Exception as exc:
        return BenchResult(
            "scan_initial",
            False,
            (perf_counter() - t0) * 1000,
            {"error": str(exc), "bodyText": page_text(page)[:500], **browser_stats(page)},
        )


def run_finance_preset(page: Page, budget_ms: float) -> BenchResult:
    preset_buttons = page.locator(".view-preset-bar button")
    count = preset_buttons.count()
    if count < 2:
        return BenchResult(
            "scan_finance5y",
            False,
            0,
            {"error": f"view preset button 부족: {count}", "presetCount": count},
        )
    t0 = perf_counter()
    preset_buttons.nth(1).click(timeout=10_000)
    page.wait_for_function("() => document.querySelectorAll('.series-wrap').length > 50", timeout=30_000)
    duration_ms = (perf_counter() - t0) * 1000
    detail = {
        "presetCount": count,
        "seriesWrap": page.locator(".series-wrap").count(),
        "svg": page.locator("svg").count(),
        **browser_stats(page),
    }
    return BenchResult("scan_finance5y", duration_ms <= budget_ms, duration_ms, detail)


def run_price_preset(page: Page, wait_ms: int) -> BenchResult:
    preset_buttons = page.locator(".view-preset-bar button")
    count = preset_buttons.count()
    if wait_ms <= 0:
        return BenchResult("scan_price_opt_in", True, 0, {"skipped": True, "reason": "price-wait-ms=0"})
    if count < 7:
        return BenchResult(
            "scan_price_opt_in",
            False,
            0,
            {"error": f"view preset button 부족: {count}", "presetCount": count},
        )
    t0 = perf_counter()
    preset_buttons.nth(6).click(timeout=10_000)
    page.wait_for_timeout(wait_ms)
    duration_ms = (perf_counter() - t0) * 1000
    text = page_text(page)
    detail = {
        "trendReady": "추세 활성" in text,
        "trendLoading": "추세 계산" in text or "추세 계산 중" in text,
        "hasSparkColumnText": "60D" in text or "1Y" in text or "추세" in text,
        "svg": page.locator("svg").count(),
        **browser_stats(page),
    }
    return BenchResult("scan_price_opt_in", True, duration_ms, detail)


def run_report_preset(page: Page, budget_ms: float) -> BenchResult:
    preset_buttons = page.locator(".view-preset-bar button")
    count = preset_buttons.count()
    if count < 8:
        return BenchResult(
            "scan_report",
            False,
            0,
            {"error": f"view preset button 부족: {count}", "presetCount": count},
        )
    t0 = perf_counter()
    preset_buttons.nth(7).click(timeout=10_000)
    page.wait_for_function(
        """() => Array.from(document.querySelectorAll('.cell'))
            .some((el) => /\\d+건/.test(el.textContent || ''))""",
        timeout=30_000,
    )
    duration_ms = (perf_counter() - t0) * 1000
    text = page_text(page)
    detail = {
        "presetCount": count,
        "hasDisclosureColumns": "공시 변경" in text and "최근 변경연도" in text,
        "hasRows": page.locator(".row").count() > 0,
        **browser_stats(page),
    }
    return BenchResult("scan_report", duration_ms <= budget_ms, duration_ms, detail)


def run_scan_detail(page: Page, budget_ms: float) -> BenchResult:
    rows = page.locator(".row")
    if rows.count() == 0:
        return BenchResult("scan_detail", False, 0, {"error": "row 없음"})
    t0 = perf_counter()
    rows.first.click(timeout=10_000)
    page.wait_for_function(
        """() => document.body.innerText.includes('Company 보기') &&
            (document.body.innerText.includes('최근 공시 변경 없음') ||
             document.querySelectorAll('.change-item').length > 0)""",
        timeout=30_000,
    )
    duration_ms = (perf_counter() - t0) * 1000
    text = page_text(page)
    detail = {
        "hasRecentChanges": "최근 공시 변경" in text,
        "hasCompanyCta": "Company 보기" in text,
        "hasInternalDbText": "db 비활성" in text,
        **browser_stats(page),
    }
    return BenchResult("scan_detail", duration_ms <= budget_ms and not detail["hasInternalDbText"], duration_ms, detail)


def run_company(page: Page, baseUrl: str, budget_ms: float) -> BenchResult:
    t0 = perf_counter()
    try:
        resp = page.goto(f"{baseUrl}/company/005930", wait_until="domcontentloaded", timeout=60_000)
        page.get_by_text("PER").first.wait_for(timeout=30_000)
        duration_ms = (perf_counter() - t0) * 1000
        text = page_text(page)
        detail = {
            "status": resp.status if resp else None,
            "hasPer": "PER" in text,
            "hasPbr": "PBR" in text,
            "hasSamsungText": "삼성전자" in text,
            "hasFinanceTable": "재무제표" in text or "매출액" in text,
            "svg": page.locator("svg").count(),
            **browser_stats(page),
        }
        return BenchResult("company_005930", duration_ms <= budget_ms, duration_ms, detail)
    except Exception as exc:
        return BenchResult(
            "company_005930",
            False,
            (perf_counter() - t0) * 1000,
            {"error": str(exc), "bodyText": page_text(page)[:500], **browser_stats(page)},
        )


def run_hf_range_lab(page: Page, baseUrl: str, budget_ms: float) -> BenchResult:
    t0 = perf_counter()
    try:
        resp = page.goto(f"{baseUrl}/lab/hf-range", wait_until="domcontentloaded", timeout=60_000)
        page.get_by_text("HF Parquet Range Probe").first.wait_for(timeout=30_000)
        page.wait_for_timeout(1000)
        page.locator(".head button").first.click(timeout=10_000)
        page.wait_for_function("() => document.body.innerText.includes('done')", timeout=60_000)
        duration_ms = (perf_counter() - t0) * 1000
        text = page_text(page)
        detail = {
            "status": resp.status if resp else None,
            "hasDone": "done" in text,
            "hasMetadata": "Metadata" in text,
            "hasRows": "Sample Rows" in text,
            **browser_stats(page),
        }
        return BenchResult("lab_hf_range", duration_ms <= budget_ms, duration_ms, detail)
    except Exception as exc:
        return BenchResult(
            "lab_hf_range",
            False,
            (perf_counter() - t0) * 1000,
            {"error": str(exc), "bodyText": page_text(page)[:500], **browser_stats(page)},
        )


def summarize(results: list[BenchResult]) -> dict[str, Any]:
    by_name: dict[str, list[BenchResult]] = {}
    for result in results:
        by_name.setdefault(result.name, []).append(result)

    summary: dict[str, Any] = {"ok": all(r.ok for r in results), "results": [asdict(r) for r in results]}
    summary["stats"] = {}
    for name, items in by_name.items():
        durations = [item.duration_ms for item in items if item.duration_ms > 0]
        summary["stats"][name] = {
            "ok": all(item.ok for item in items),
            "count": len(items),
            "medianMs": statistics.median(durations) if durations else 0,
            "minMs": min(durations) if durations else 0,
            "maxMs": max(durations) if durations else 0,
        }
    return summary


def print_human(summary: dict[str, Any]) -> None:
    print(f"HF runtime bench: {'PASS' if summary['ok'] else 'FAIL'}")
    for name, stats in summary["stats"].items():
        status = "PASS" if stats["ok"] else "FAIL"
        print(
            f"- {name}: {status} median={stats['medianMs']:.0f}ms min={stats['minMs']:.0f}ms max={stats['maxMs']:.0f}ms"
        )
    print("\nDetails:")
    for item in summary["results"]:
        print(f"- {item['name']}: {'PASS' if item['ok'] else 'FAIL'} {item['duration_ms']:.0f}ms")
        compact = {
            key: value
            for key, value in item["detail"].items()
            if key
            in {
                "status",
                "hasTrendManual",
                "seriesWrap",
                "hasPer",
                "hasPbr",
                "hfRequestCount",
                "duckOrParquetRequestCount",
                "transferSize",
                "encodedBodySize",
                "skipped",
                "trendReady",
                "trendLoading",
                "hasDone",
                "hasMetadata",
                "hasRows",
            }
        }
        print(f"  {json.dumps(compact, ensure_ascii=False)}")


def main() -> int:
    args = parse_args()
    if args.iterations < 1:
        raise SystemExit("--iterations는 1 이상이어야 합니다.")

    results: list[BenchResult] = []
    console_logs: list[str] = []
    failed_requests: list[str] = []
    bad_responses: list[str] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        for _ in range(args.iterations):
            context = browser.new_context(
                viewport={"width": 1440, "height": 1000},
                ignore_https_errors=True,
            )
            page = context.new_page()
            page.on("console", lambda msg: console_logs.append(f"{msg.type}: {msg.text}"))
            page.on("pageerror", lambda exc: console_logs.append(f"pageerror: {exc}"))
            page.on("requestfailed", lambda req: failed_requests.append(f"{req.method} {req.url} {req.failure}"))
            page.on(
                "response",
                lambda resp: bad_responses.append(f"{resp.status} {resp.url}") if resp.status >= 400 else None,
            )

            results.append(run_scan(page, args.baseUrl, args.scan_budget_ms))
            results.append(run_finance_preset(page, args.finance_budget_ms))
            results.append(run_price_preset(page, args.price_wait_ms))
            results.append(run_report_preset(page, args.report_budget_ms))
            results.append(run_scan_detail(page, args.detail_budget_ms))
            results.append(run_company(page, args.baseUrl, args.company_budget_ms))
            page.wait_for_timeout(750)
            context.close()
            if args.include_hf_range_lab:
                lab_context = browser.new_context(
                    viewport={"width": 1440, "height": 1000},
                    ignore_https_errors=True,
                )
                lab_page = lab_context.new_page()
                lab_page.on("console", lambda msg: console_logs.append(f"{msg.type}: {msg.text}"))
                lab_page.on("pageerror", lambda exc: console_logs.append(f"pageerror: {exc}"))
                lab_page.on(
                    "requestfailed",
                    lambda req: failed_requests.append(f"{req.method} {req.url} {req.failure}"),
                )
                lab_page.on(
                    "response",
                    lambda resp: bad_responses.append(f"{resp.status} {resp.url}") if resp.status >= 400 else None,
                )
                results.append(run_hf_range_lab(lab_page, args.baseUrl, args.hf_range_budget_ms))
                lab_context.close()
        browser.close()

    summary = summarize(results)
    summary["consoleLogs"] = console_logs[:80]
    summary["failedRequests"] = failed_requests[:80]
    summary["badResponses"] = bad_responses[:80]
    blocking_console_logs = [
        line for line in console_logs if line.startswith("error:") or line.startswith("pageerror:")
    ]
    summary["runtimeClean"] = not blocking_console_logs and not failed_requests and not bad_responses
    summary["blockingConsoleLogs"] = blocking_console_logs[:80]

    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print_human(summary)
        if console_logs:
            print("\nConsole:")
            for line in console_logs[:20]:
                print(f"- {line}")
        if failed_requests:
            print("\nFailed requests:")
            for line in failed_requests[:20]:
                print(f"- {line}")
        if bad_responses:
            print("\nHTTP >= 400:")
            for line in bad_responses[:20]:
                print(f"- {line}")

    return 1 if args.strict and (not summary["ok"] or not summary["runtimeClean"]) else 0


if __name__ == "__main__":
    sys.exit(main())
