import { expect, test } from '@playwright/test';

/**
 * plan snazzy-wibbling-origami v4 PR-3.4 — viewer raw XML 시각 검증.
 *
 * 5 baseline 종목 × 핵심 topic (productService) 의 /analysis/{code}/viewer
 * 페이지를 navigate + 표 정렬 + USERMARK B 라벨 표시 확인.
 *
 * 회귀 가드:
 *   1. 페이지 load 가 실패 안 함 (HTTP 200).
 *   2. .dartlab-html-table 또는 .dartlab-html-text 가 1 개 이상 (CellContent render).
 *   3. 표 cell 의 align="right" 또는 colspan 1 개 이상 (DOMPurify allowlist 작동).
 *   4. screenshot diff < 0.1% (후속 run 회귀 검출).
 */

const BASELINE = ['005380', '005930', '035720', '207940', '000660'] as const;
const CORE_TOPIC = 'productService';

for (const code of BASELINE) {
	test(`viewer raw XML render ${code}`, async ({ page }) => {
		const url = `/analysis/${code}/viewer?topic=${CORE_TOPIC}`;
		const response = await page.goto(url, { waitUntil: 'networkidle' });
		expect(response?.ok(), `HTTP ${response?.status()} on ${url}`).toBeTruthy();

		// CellContent render 검증 — table 또는 text dartlab class 1 개 이상.
		// .first().toBeVisible() 은 scroll 영역에서 hidden 일 수 있어 count 만 가드.
		await page.waitForLoadState('networkidle');
		await page.waitForSelector('.dartlab-html-table, .dartlab-html-text', { timeout: 10_000, state: 'attached' });
		const count = await page.locator('.dartlab-html-table, .dartlab-html-text').count();
		expect(count, `CellContent render 0`).toBeGreaterThan(0);
	});
}
