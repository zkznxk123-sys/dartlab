import { defineConfig, devices } from '@playwright/test';

/**
 * plan snazzy-wibbling-origami v4 PR-3.4 — sections viewer visual baseline.
 *
 * dev server 전제:
 *   - backend: `uv run python -m dartlab.server` (port 8400)
 *   - frontend: `npm run dev` (port 5400, /api → 8400 proxy)
 *
 * baseline screenshot: tests/__screenshots__/ (gitignore 제외, repo 동봉).
 * 회귀 가드: 후속 run 에서 diff > 0.1% 시 fail (toHaveScreenshot threshold).
 */
export default defineConfig({
	testDir: './tests',
	timeout: 30_000,
	expect: { toHaveScreenshot: { maxDiffPixelRatio: 0.001 } },
	use: {
		baseURL: 'http://localhost:5400',
		trace: 'on-first-retry',
		viewport: { width: 1280, height: 800 },
	},
	projects: [
		{ name: 'chromium', use: { ...devices['Desktop Chrome'] } },
	],
	// dev server 자동 시작 비활성 — 별도 start 필요 (backend + frontend 분리).
});
