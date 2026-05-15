// Dashboard visual smoke — Playwright headless 로 5400 페이지 로드 후
// dashboard 모드 + analysis 수익구조 axis 까지 진입, 카드 + 차트 + 테마 토글 검증.
// 결과 스크린샷 저장: tmp/dashboard-{dark,light}.png

import { chromium } from "playwright";
import { mkdirSync, existsSync } from "node:fs";
import path from "node:path";

const BASE = process.env.UI_URL || "http://localhost:5400";
const OUT = path.join(process.cwd(), "tmp");
if (!existsSync(OUT)) mkdirSync(OUT, { recursive: true });

function assert(cond, msg) {
	if (!cond) throw new Error(msg);
}

async function setLocalStorage(page) {
	await page.evaluate(() => {
		localStorage.setItem("dartlab-ui-mode", "dashboard");
		localStorage.setItem("dartlab-theme", "dark");
		localStorage.setItem(
			"dartlab-dashboard-state",
			JSON.stringify({ section: "analysis", stockCode: "000660", axis: "수익구조", period: "TTM" })
		);
	});
}

async function waitForAxisCards(page, label) {
	// 카드 영역 — DashboardShell main 안의 [data-slot="card"] (shadcn).
	// AnalysisHub 는 상단 axis tab card + 본문 N 개 card. 본문 카드 ≥ 1 보여야 함.
	await page.waitForSelector('main [data-slot="card"]', { timeout: 30000 });
	const count = await page.locator('main [data-slot="card"]').count();
	const texts = await page.locator('main [data-slot="card"]').allInnerTexts();
	const joined = texts.join("\n");
	console.log(`[${label}] cards=${count}, total text length=${joined.length}`);
	console.log(`[${label}] first 800 chars of card content:\n${joined.slice(0, 800)}`);
	return { count, text: joined };
}

async function main() {
	const browser = await chromium.launch({ headless: true });
	const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
	const page = await ctx.newPage();
	page.on("pageerror", (e) => console.error("[PAGEERROR]", e.message));
	page.on("console", (msg) => {
		if (msg.type() === "error") console.error("[CONSOLE]", msg.text());
	});

	console.log(`Loading ${BASE} ...`);
	// 첫 로드는 localStorage 가 비어있을 수 있어서 / 로 시작 후 reload
	await page.goto(BASE, { waitUntil: "domcontentloaded" });
	await setLocalStorage(page);
	await page.reload({ waitUntil: "domcontentloaded" });

	// dashboard 진입 확인 — EngineNav 또는 main 의 dashboard header
	await page.waitForSelector("main", { timeout: 10000 });

	// Wait for fetch to complete — dl/call 응답
	await page.waitForResponse(
		(r) => r.url().includes("/api/dl/call") && r.request().method() === "POST",
		{ timeout: 30000 }
	);
	// 마지막 paint
	await page.waitForTimeout(1200);

	const dark = await waitForAxisCards(page, "DARK");
	await page.screenshot({ path: path.join(OUT, "dashboard-dark.png"), fullPage: true });

	// ThemeToggle 클릭 → light
	const toggle = page.locator('button[aria-label*="전환"]').first();
	if ((await toggle.count()) === 0) {
		throw new Error("ThemeToggle (aria-label*='전환') not found");
	}
	await toggle.click();
	await page.waitForTimeout(400);
	const themeAttr1 = await page.evaluate(() => document.documentElement.dataset.theme || null);
	console.log(`[after 1st click] data-theme = ${themeAttr1}`);
	assert(themeAttr1 === "light", `expected data-theme=light after first click, got ${themeAttr1}`);

	const light = await waitForAxisCards(page, "LIGHT");
	await page.screenshot({ path: path.join(OUT, "dashboard-light.png"), fullPage: true });

	// 두번째 클릭 → auto
	await toggle.click();
	await page.waitForTimeout(200);
	const themeAttr2 = await page.evaluate(() => document.documentElement.dataset.theme || null);
	console.log(`[after 2nd click] data-theme = ${themeAttr2}`);
	assert(themeAttr2 === "auto", `expected data-theme=auto after second click, got ${themeAttr2}`);

	// 세번째 클릭 → dark (no attr)
	await toggle.click();
	await page.waitForTimeout(200);
	const themeAttr3 = await page.evaluate(() => document.documentElement.dataset.theme || null);
	console.log(`[after 3rd click] data-theme = ${themeAttr3}`);
	assert(themeAttr3 === null, `expected data-theme cleared (dark) after third click, got ${themeAttr3}`);

	// 다른 axis: 수익성 클릭 (history shape — 차트 가 떠야)
	const profitabilityBtn = page.locator('button:has-text("수익성")').first();
	if ((await profitabilityBtn.count()) > 0) {
		await profitabilityBtn.click();
		await page.waitForResponse(
			(r) => r.url().includes("/api/dl/call") && r.request().method() === "POST",
			{ timeout: 30000 }
		);
		await page.waitForTimeout(800);
		const profitText = await page.locator("main").innerText();
		const hasSvg = (await page.locator("main svg").count()) > 0;
		console.log(`[profitability] svg=${hasSvg}, text contains marginTrend=${profitText.includes("marginTrend")}`);
		await page.screenshot({ path: path.join(OUT, "dashboard-profitability.png"), fullPage: true });
		assert(hasSvg, "수익성 axis: SVG chart not found");
	}

	// 본문 카드 검증
	assert(dark.count >= 2, `dark: too few cards (${dark.count})`);
	assert(dark.text.length > 100, `dark: card text too short`);
	// 빈 박스 회귀 — "분석 결과 없음" 만 나오는 상태 차단 (axis tabs 카드 1 + dashed 1 = count 2 인데 text 짧음)
	// 정상이면 "profile" 또는 "revenueQuality" 또는 "growth" 같은 metric key 가 있어야
	const hasMetricKey =
		dark.text.includes("profile") ||
		dark.text.includes("revenueQuality") ||
		dark.text.includes("growth") ||
		dark.text.includes("cashConversion") ||
		dark.text.includes("grossMargin");
	assert(hasMetricKey, "dark: 수익구조 axis 의 알려진 metric key 가 카드에 보이지 않음 — 빈 박스 회귀");

	console.log("\n✓ dashboard smoke passed");
	console.log(`  screenshots → ${OUT}\\dashboard-{dark,light,profitability}.png`);

	await browser.close();
}

main().catch((e) => {
	console.error(e);
	process.exit(1);
});
