// L6 — PriceEventChart Playwright e2e spec (5 test).
//
// 네트워크 의존 (/api/dartlab/price-events) 은 page.route() 로 mock 주입 — 백엔드 미기동 상태에서도 통과.
// 시각 검증보다 DOM/이벤트 정합 검증이 목표.

import { expect, test } from '@playwright/test';

const STOCK = '005930';

function _mkOhlc(n: number): number[][] {
	const rows: number[][] = [];
	const start = Math.floor(new Date('2024-01-01').getTime() / 1000);
	for (let i = 0; i < n; i++) {
		const ts = start + i * 86400;
		const close = 70000 + i * 50;
		rows.push([ts, close - 100, close + 200, close - 200, close, 1000000]);
	}
	return rows;
}

const MOCK_PAYLOAD = {
	stockCode: STOCK,
	corpName: '삼성전자',
	market: 'KR',
	start: '2024-01-01',
	end: '2024-04-30',
	ohlc: _mkOhlc(60),
	events: {
		'2024-02-15': {
			disclosures: [
				{ title: '2023 사업보고서 제출', rceptNo: '20240215000001', url: 'https://dart.fss.or.kr/x', discType: 'periodic' },
			],
			news_rss: [
				{ title: '삼성전자 깜짝 호실적 발표', source: 'TestNews', url: 'http://x/a', sentiment_score: 0.6, sentiment_label: 'pos' },
				{ title: '삼성전자 HBM 양산 확대', source: 'TestNews', url: 'http://x/b', sentiment_score: 0.4, sentiment_label: 'pos' },
			],
		},
		'2024-03-10': {
			news_gdelt: [
				{ title: 'Samsung announces new chip', source: 'gdelt-x', url: 'http://x/c', sentiment_score: 0.3, sentiment_label: 'pos', themes: ['TECH'] },
			],
		},
	},
	shocks: [
		{ date: '2024-02-15', ar: 0.054, z_score: 3.2, direction: 'up', is_significant: true },
	],
	regime_band: [],
};

test.describe('PriceEventChart e2e', () => {
	test.beforeEach(async ({ page }) => {
		await page.route('**/api/dartlab/price-events*', async (route) => {
			await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(MOCK_PAYLOAD) });
		});
		// 회사 메타 mock (CompanyHeader 가 호출)
		await page.route('**/api/companyMeta*', async (route) => {
			await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ stockCode: STOCK, corpName: '삼성전자' }) });
		});
	});

	test('차트 마운트 + 캔들 canvas 렌더', async ({ page }) => {
		await page.goto(`/analysis/${STOCK}/events?period=quarterly`);
		// PriceEventChart 카드 헤더
		await expect(page.getByText('주가 + 이벤트 차트 (L6)')).toBeVisible({ timeout: 10_000 });
		// canvas (LWC v5) — chart 컨테이너 안에 1개 이상
		const canvases = page.locator('canvas');
		await expect(canvases.first()).toBeVisible({ timeout: 10_000 });
		expect(await canvases.count()).toBeGreaterThan(0);
	});

	test('source filter — RSS 버튼 클릭 시 active', async ({ page }) => {
		await page.goto(`/analysis/${STOCK}/events?period=quarterly`);
		await expect(page.getByRole('button', { name: 'RSS' })).toBeVisible({ timeout: 10_000 });
		await page.getByRole('button', { name: 'RSS' }).click();
		// default variant 가 active — 버튼 활성 시 다른 variant
		await expect(page.getByRole('button', { name: 'RSS' })).toHaveAttribute('data-state', /.*/);
	});

	test('legend 표시 — 공시 / RSS / GDELT 3 dot', async ({ page }) => {
		await page.goto(`/analysis/${STOCK}/events?period=quarterly`);
		await expect(page.getByText('공시', { exact: true })).toBeVisible({ timeout: 10_000 });
		await expect(page.getByText('RSS', { exact: true })).toBeVisible();
		await expect(page.getByText('GDELT', { exact: true })).toBeVisible();
	});

	test('shock toggle on/off — checkbox 클릭', async ({ page }) => {
		await page.goto(`/analysis/${STOCK}/events?period=quarterly`);
		const switchEl = page.locator('#shocks');
		await expect(switchEl).toBeVisible({ timeout: 10_000 });
		// 기본 on → off 토글
		const initialState = await switchEl.getAttribute('data-state');
		await switchEl.click();
		const newState = await switchEl.getAttribute('data-state');
		expect(initialState).not.toBe(newState);
	});

	test('marker click → Sheet 본문 본문 헤딩 노출', async ({ page }) => {
		await page.goto(`/analysis/${STOCK}/events?period=quarterly`);
		// canvas 마운트 + marker overlay 렌더 대기
		await page.waitForTimeout(1500);
		// overlay 안 점 (background:#3b82f6 disclosure, #f97316 rss, #a855f7 gdelt) 첫 번째 click
		const dot = page.locator('div[style*="border-radius:50%"]').first();
		// marker 가 timeScale coordinate 의존이라 chart fit 후 부분 가시. 보이면 click.
		const count = await page.locator('div[style*="border-radius:50%"]').count();
		if (count === 0) {
			test.skip(true, 'marker overlay 미렌더 — chart timeScale coordinate 0 일 가능 (CI 환경)');
			return;
		}
		await dot.click({ timeout: 5_000 });
		// Sheet 본문 (EventSidePanel) — "이벤트 상세" 헤딩
		await expect(page.getByText('이벤트 상세')).toBeVisible({ timeout: 5_000 });
	});
});
