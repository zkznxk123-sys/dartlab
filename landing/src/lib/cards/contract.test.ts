import { describe, it, expect, vi, beforeEach } from 'vitest';

// origins 레지스트리는 mock — vitest 워크스페이스 해석 비의존 + URL 예측 가능.
vi.mock('@dartlab/ui-runtime/data/origins/registry', () => ({
	originUrl: (_id: string, path: string) => `https://media.test/${path}`
}));

/** path 부분일치로 JSON 응답하는 fetch 목. 미스 = 404(ok:false). */
function mockFetch(map: Record<string, unknown>) {
	return vi.fn(async (url: string) => {
		const key = Object.keys(map).find((k) => url.includes(k));
		if (key) return { ok: true, json: async () => map[key] } as unknown as Response;
		return { ok: false, json: async () => ({}) } as unknown as Response;
	});
}

describe('contract 슬러그-키', () => {
	beforeEach(() => vi.resetModules()); // 모듈 캐시(_posts/_cache) 리셋

	it('loadContractPosts 는 index.json posts[] 를 순서대로 파싱', async () => {
		vi.stubGlobal(
			'fetch',
			mockFetch({
				'carousels/index.json': {
					posts: [
						{ code: '005930', slug: '005930-samsung', title: '삼성', date: '2026-01-02' },
						{ code: '000660', slug: '000660-skhynix', date: '2026-01-01' }
					]
				}
			})
		);
		const { loadContractPosts } = await import('./contract');
		const posts = await loadContractPosts();
		expect(posts.map((p) => p.slug)).toEqual(['005930-samsung', '000660-skhynix']);
		expect(posts[0].title).toBe('삼성');
	});

	it('loadContract 는 슬러그 경로(carousels/{slug}.json)로 fetch', async () => {
		const f = mockFetch({
			'carousels/003230-samyang-foods.json': { code: '003230', slug: '003230-samyang-foods', name: '삼양식품', slides: [] }
		});
		vi.stubGlobal('fetch', f);
		const { loadContract } = await import('./contract');
		const c = await loadContract('003230-samyang-foods');
		expect(c?.code).toBe('003230');
		expect(c?.slug).toBe('003230-samyang-foods');
		expect(String(f.mock.calls[0][0])).toContain('carousels/003230-samyang-foods.json');
	});

	it('미게시(404) 면 posts 빈 배열·계약 null(빈 화면 방지)', async () => {
		vi.stubGlobal('fetch', mockFetch({}));
		const { loadContractPosts, loadContract } = await import('./contract');
		expect(await loadContractPosts()).toEqual([]);
		expect(await loadContract('nope')).toBeNull();
	});
});
