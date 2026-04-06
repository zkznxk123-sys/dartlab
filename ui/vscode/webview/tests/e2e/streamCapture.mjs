/**
 * dartlab webview 스트리밍 시각 검증.
 *
 * 사용법:
 *   node tests/e2e/streamCapture.mjs <label>
 *
 * 환경:
 *   - Term A: npm run dev (vite watch build)
 *   - Term B: python -m http.server 5400 (webview 디렉토리에서)
 *
 * 출력:
 *   screenshots/{label}_{fixture}.png  — 3 fixture × 1 viewport
 *
 * harness URL: http://localhost:5400/dev/harness.html?fixture=table&autoplay=1
 */
import { chromium } from "playwright";
import { mkdirSync, existsSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const SCREENSHOTS_DIR = join(__dirname, "..", "..", "screenshots");
const BASE = process.env.HARNESS_URL || "http://localhost:5400/webview/dev/harness.html";
const FIXTURES = ["table", "chart", "mixed"];
const VIEWPORT = { width: 920, height: 1400 };

const label = process.argv[2] || "snapshot";

if (!existsSync(SCREENSHOTS_DIR)) mkdirSync(SCREENSHOTS_DIR, { recursive: true });

async function captureFixture(browser, fixture, opts = {}) {
  const { pauseAt, suffix = "" } = opts;
  const ctx = await browser.newContext({
    viewport: VIEWPORT,
    deviceScaleFactor: 2,
    bypassCSP: true,
  });
  await ctx.route("**/*", (route) => route.continue());
  const page = await ctx.newPage();
  await page.context().clearCookies();
  // 캐시 무효화: HTTP 캐시 비활성화
  const client = await ctx.newCDPSession(page);
  await client.send("Network.setCacheDisabled", { cacheDisabled: true });
  const params = new URLSearchParams({ fixture, autoplay: "1" });
  if (pauseAt != null) params.set("pauseAt", String(pauseAt));
  const url = `${BASE}?${params}`;
  console.log(`  → ${url}`);

  page.on("console", (m) => {
    if (m.type() === "error") console.error(`    [console.error] ${m.text()}`);
  });
  page.on("pageerror", (e) => console.error(`    [pageerror] ${e.message}`));

  await page.goto(url, { waitUntil: "domcontentloaded" });
  const targetState = pauseAt != null ? "paused" : "done";
  await page.waitForFunction(
    (s) => document.body.dataset.playState === s,
    targetState,
    { timeout: 30_000 },
  );
  await page.waitForTimeout(300);

  const fname = suffix ? `${label}_${fixture}_${suffix}.png` : `${label}_${fixture}.png`;
  const out = join(SCREENSHOTS_DIR, fname);
  await page.screenshot({ path: out, fullPage: true });
  console.log(`    saved: ${out}`);
  await ctx.close();
}

(async () => {
  console.log(`[streamCapture] label="${label}"`);
  const browser = await chromium.launch();
  try {
    for (const fx of FIXTURES) {
      console.log(`[fixture] ${fx}`);
      try {
        await captureFixture(browser, fx);
      } catch (e) {
        console.error(`  ✗ ${fx} 실패:`, e.message);
      }
    }
    // mid-stream 캡처 — table fixture 의 절반 지점
    console.log(`[fixture] table (mid-stream)`);
    try {
      await captureFixture(browser, "table", { pauseAt: 9, suffix: "mid" });
    } catch (e) {
      console.error(`  ✗ table mid 실패:`, e.message);
    }
  } finally {
    await browser.close();
  }
})();
