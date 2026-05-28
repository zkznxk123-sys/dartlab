// Playwright config — ui/web (React 19 + Vite 6 + LWC v5) e2e.
//
// dev server (npm run dev) 자동 기동 + chromium 단일 브라우저. CI 에서는
// reporter=list, 로컬은 list + html.

import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
	testDir: './tests',
	timeout: 30_000,
	expect: { timeout: 5_000 },
	fullyParallel: false, // chart 마운트 + canvas — 시리얼 더 안정
	forbidOnly: !!process.env.CI,
	retries: process.env.CI ? 1 : 0,
	workers: 1,
	reporter: process.env.CI ? 'list' : [['list'], ['html', { open: 'never' }]],
	use: {
		baseURL: 'http://localhost:5400',
		trace: 'on-first-retry',
		video: 'retain-on-failure',
		screenshot: 'only-on-failure',
	},
	projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
	webServer: {
		command: 'npm run dev',
		url: 'http://localhost:5400',
		reuseExistingServer: !process.env.CI,
		timeout: 60_000,
	},
});
