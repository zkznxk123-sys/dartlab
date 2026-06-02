// 공시뷰어 panel SSOT e2e (plan silly-snacking-yeti).
//
// 네트워크 (/api/company/{code}/panel*) 는 page.route() 로 mock — 백엔드 미기동 통과.
// 검증: TOC(chapter>sectionLeaf) 렌더 / sectionLeaf 클릭 URL / raw XML 표 → DOM table /
//       timeline 이동 추가 fetch 0 / diff 배지 프론트 계산.

import { expect, test } from '@playwright/test';

const STOCK = '005930';
const SECTION_KEY = 'I. 회사의 개요␟1. 회사의 개요';

const TOC = {
	stockCode: STOCK,
	corpName: '삼성전자',
	chapters: [
		{
			chapter: 'I. 회사의 개요',
			sections: [
				{ sectionLeaf: '1. 회사의 개요', sectionKey: 'I. 회사의 개요␟1. 회사의 개요', rowCount: 2, blocks: [{ blockLeaf: '연혁표', rowCount: 1 }] },
				{ sectionLeaf: '2. 회사의 연혁', sectionKey: 'I. 회사의 개요␟2. 회사의 연혁', rowCount: 1, blocks: [] },
			],
		},
		{
			chapter: 'III. 재무에 관한 사항',
			sections: [{ sectionLeaf: '2. 연결재무제표', sectionKey: 'III. 재무에 관한 사항␟2. 연결재무제표', rowCount: 1, blocks: [{ blockLeaf: '연결 재무상태표', rowCount: 1 }] }],
		},
	],
	// 9 기간 — cols(3/6/9) 가로폭 확장 검증용. 앞 4 개는 GRID.periods 와 일치해야 init seed 적중.
	periods: ['2026Q1', '2025Q4', '2025Q3', '2024Q4', '2024Q3', '2024Q2', '2024Q1', '2023Q4', '2023Q3'],
};

const GRID = {
	stockCode: STOCK,
	corpName: '삼성전자',
	chapter: 'I. 회사의 개요',
	sectionLeaf: '1. 회사의 개요',
	sectionKey: SECTION_KEY,
	periods: ['2026Q1', '2025Q4', '2025Q3', '2024Q4'],
	rows: [
		{
			chapter: 'I. 회사의 개요',
			sectionLeaf: '1. 회사의 개요',
			blockLeaf: '',
			disclosureKey: null,
			scope: 'consolidated',
			blockType: 'text',
			cells: { '2026Q1': '<P>2026 본문 변경됨</P>', '2025Q4': '<P>옛 본문</P>', '2025Q3': '<P>옛 본문</P>' },
		},
		{
			chapter: 'I. 회사의 개요',
			sectionLeaf: '1. 회사의 개요',
			blockLeaf: '연혁표',
			disclosureKey: null,
			scope: 'consolidated',
			blockType: 'table',
			cells: { '2026Q1': '<TABLE-GROUP><TABLE><TR><TE>연혁 데이터</TE></TR></TABLE></TABLE-GROUP>', '2025Q4': '<TABLE><TR><TE>연혁 데이터</TE></TR></TABLE>' },
		},
	],
	dartUrlByPeriod: { '2026Q1': 'https://dart.fss.or.kr/x', '2025Q4': null, '2025Q3': null },
};

const INIT = {
	stockCode: STOCK,
	corpName: '삼성전자',
	toc: TOC,
	firstChapter: 'I. 회사의 개요',
	firstSectionKey: SECTION_KEY,
	grid: GRID,
};

function json(body: unknown) {
	return { status: 200, contentType: 'application/json', body: JSON.stringify(body) };
}

test.describe('Panel viewer e2e', () => {
	let gridCalls = 0;

	test.beforeEach(async ({ page }) => {
		gridCalls = 0;
		await page.route('**/api/company/**', async (route) => {
			const url = route.request().url();
			if (url.includes('/panel/init')) return route.fulfill(json(INIT));
			if (url.includes('/panel/toc')) return route.fulfill(json(TOC));
			if (/\/panel(\?|$)/.test(url)) {
				gridCalls += 1;
				return route.fulfill(json(GRID));
			}
			if (url.includes('/meta') || url.toLowerCase().includes('meta')) {
				return route.fulfill(json({ stockCode: STOCK, corpName: '삼성전자', market: 'KR', sector: '', products: [], blogPosts: [] }));
			}
			return route.continue();
		});
	});

	test('TOC — chapter > sectionLeaf 렌더', async ({ page }) => {
		await page.goto(`/analysis/${STOCK}/viewer?period=quarterly`);
		await expect(page.getByText('I. 회사의 개요', { exact: true })).toBeVisible({ timeout: 10_000 });
		await expect(page.getByText('III. 재무에 관한 사항', { exact: true })).toBeVisible();
		await expect(page.getByRole('button', { name: '1. 회사의 개요' })).toBeVisible();
		await expect(page.getByRole('button', { name: '2. 연결재무제표' })).toBeVisible();
	});

	test('sectionLeaf 클릭 → ?section= URL 갱신', async ({ page }) => {
		await page.goto(`/analysis/${STOCK}/viewer?period=quarterly`);
		await page.getByRole('button', { name: '2. 회사의 연혁' }).click();
		await page.waitForURL(/section=/, { timeout: 10_000 });
		// URLSearchParams 는 공백을 '+' 로 인코딩 — decode 전에 '+' → ' ' 복원.
		expect(decodeURIComponent(page.url().replace(/\+/g, ' '))).toContain('2. 회사의 연혁');
	});

	test('grid — raw XML 표가 DOM table 로 sanitize 렌더', async ({ page }) => {
		await page.goto(`/analysis/${STOCK}/viewer?period=quarterly`);
		// 3 period 컬럼 헤더
		await expect(page.getByText('2026Q1', { exact: true }).first()).toBeVisible({ timeout: 10_000 });
		// raw <TABLE-GROUP><TABLE> → 정규화 후 DOM <table>
		await expect(page.locator('.dartlab-html-table table').first()).toBeVisible({ timeout: 10_000 });
		await expect(page.getByText('연혁 데이터').first()).toBeVisible();
	});

	test('timeline 이동 → ?windowEnd= 갱신 + window grid 1회 refetch', async ({ page }) => {
		await page.goto(`/analysis/${STOCK}/viewer?period=quarterly`);
		await expect(page.getByText('2026Q1', { exact: true }).first()).toBeVisible({ timeout: 10_000 });
		const before = gridCalls;
		// ChevronRight (더 과거로) — window 이동
		await page.getByTitle('더 과거로').click();
		await page.waitForURL(/windowEnd=/, { timeout: 10_000 });
		// window-scoped fetch: 이동 시 새 window(±1) 만 1 회 재요청 (full-period 덤프 회피 — 성능 정공).
		expect(gridCalls).toBe(before + 1);
	});

	test('cols 6 클릭 → 기간 컬럼 6 개로 가로폭 확장 (수평화)', async ({ page }) => {
		await page.goto(`/analysis/${STOCK}/viewer?period=quarterly`);
		await expect(page.getByText('2026Q1', { exact: true }).first()).toBeVisible({ timeout: 10_000 });
		// 기본 3 컬럼
		await expect(page.locator('main .font-mono.text-xs.font-semibold')).toHaveCount(3);
		await page.getByRole('button', { name: /^6$/ }).click();
		// 6 기간 헤더 (panel 이 9 기간 제공 → 6 노출)
		await expect(page.locator('main .font-mono.text-xs.font-semibold')).toHaveCount(6, { timeout: 10_000 });
	});

	test('항목 레이블 좌측 레일 — blockLeaf 가 sticky 레일에 노출', async ({ page }) => {
		await page.goto(`/analysis/${STOCK}/viewer?period=quarterly`);
		await expect(page.getByText('2026Q1', { exact: true }).first()).toBeVisible({ timeout: 10_000 });
		// 레일 코너 헤더 '항목' (툴바의 '항목 N · 전체 기간' 과 구분 위해 exact)
		await expect(page.getByText('항목', { exact: true })).toBeVisible();
		// blockLeaf '연혁표' 가 본문 좌측 레일에 (TOC chip 은 aside 라 main 으로 스코프)
		await expect(page.locator('main').getByText('연혁표', { exact: true })).toBeVisible();
	});

	test('diff 배지 — 변경 인접 period 에 "변경 포함"', async ({ page }) => {
		await page.goto(`/analysis/${STOCK}/viewer?period=quarterly`);
		await expect(page.getByText('2026Q1', { exact: true }).first()).toBeVisible({ timeout: 10_000 });
		// 2026Q1 본문이 2025Q4 와 달라 changedSet 에 포함 → period header "변경 포함"
		await expect(page.getByText('변경 포함').first()).toBeVisible({ timeout: 10_000 });
	});
});
