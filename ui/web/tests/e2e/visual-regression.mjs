/**
 * Phase F 시각 회귀 — 재무제표 4 탭 × annual/quarterly × light/dark = 16 화면.
 * 매 화면마다 fresh browser launch (vite dev 서버 메모리 누수 회피).
 */
import { chromium } from "playwright";
import { mkdirSync } from "fs";

const BASE_URL = process.env.DARTLAB_UI_URL || "http://localhost:5400";
const STOCK = "035720";
const TABS = ["is", "bs", "cf", "ratios"];
const MODES = ["annual", "quarterly"];
const THEMES = ["light", "dark"];

mkdirSync("screenshots/financial", { recursive: true });

const log = (...a) => console.log("[visual]", ...a);

async function capture(theme, mode, tab) {
	const browser = await chromium.launch();
	try {
		const ctx = await browser.newContext({
			viewport: { width: 1440, height: 900 },
			deviceScaleFactor: 1,
		});
		const page = await ctx.newPage();
		page.on("console", (msg) => console.log(`[browser:${msg.type()}] ${msg.text().slice(0, 200)}`));
		page.on("pageerror", (err) => console.log(`[browser:error] ${err.message.slice(0, 300)}`));
		page.on("requestfailed", (req) => console.log(`[browser:reqfail] ${req.url()} — ${req.failure()?.errorText}`));
		await page.addInitScript(({ tab, mode, theme, sc }) => {
			try {
				localStorage.setItem("dartlab-dashboard-state-v2", JSON.stringify({ section: tab, stockCode: sc, mode }));
				localStorage.setItem("dartlab-ui-mode", "dashboard");
				localStorage.setItem("dartlab-theme", theme);
			} catch {}
		}, { tab, mode, theme, sc: STOCK });
		await page.goto(BASE_URL, { waitUntil: "domcontentloaded", timeout: 60000 });
		await page.evaluate((t) => {
			document.documentElement.setAttribute("data-theme", t);
			document.documentElement.classList.toggle("dark", t === "dark");
		}, theme);
		await page.waitForTimeout(5000);
		const file = `screenshots/financial/${theme}-${mode}-${tab}.png`;
		await page.screenshot({ path: file, fullPage: true });
		log(`captured ${file}`);
		return true;
	} catch (e) {
		log(`FAIL ${theme}-${mode}-${tab}: ${e.message?.split("\n")[0]}`);
		return false;
	} finally {
		await browser.close().catch(() => {});
	}
}

(async () => {
	let ok = 0;
	for (const theme of THEMES) {
		for (const mode of MODES) {
			for (const tab of TABS) {
				if (await capture(theme, mode, tab)) ok++;
			}
		}
	}
	log(`done — ${ok}/16 captured`);
	process.exit(ok === 16 ? 0 : 1);
})();
