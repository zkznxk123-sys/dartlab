// 종목 뉴스 헤드라인 로더 — 네이버 검색 API archive(private, 언론사 저작권)를 CF 워커가 read 토큰으로
// 서버사이드 read 해 반환(라이브 표시 = 의도된 용도, 공개 벌크 재배포 아님). 브라우저는 private 직독 불가라
// 워커 경유가 유일 경로 — 공개·로컬 동일(price·macro 와 같은 "공통 배선": 워커/HF 단일 소스).
//   모든 환경 = CF 워커 /news 라우트(VITE_DARTLAB_NEWS_PROXY). 미설정 시 [] (정직한 미배선).
// (옛 dev /__news 미들웨어 분기는 구현된 적 없어 로컬을 빈 상태로 만들었다 — 제거하고 워커로 통일.)
import type { NewsItem } from '@dartlab/ui-contracts';

const browser = typeof window !== 'undefined';
const viteEnv = (import.meta as { env?: Record<string, string | boolean | undefined> }).env;

const cache = new Map<string, NewsItem[]>();

// 프로덕션 프록시 URL (CF 워커 /news 라우트). 미설정 시 프로덕션에선 빈배열. origin.ts HF_RESOLVE ·
// naverPriceSource NAVER_PROXY 와 동일 게이트(가역, 비우면 즉시 미동작).
const NEWS_PROXY = ((viteEnv?.VITE_DARTLAB_NEWS_PROXY as string | undefined) ?? '').replace(/\/+$/, '');

/** CF 워커 /news 라우트(공개·로컬 공통). NEWS_PROXY 미설정 시 null(미동작=빈 섹션). */
function newsEndpoint(code: string): string | null {
	if (!NEWS_PROXY) return null;
	return `${NEWS_PROXY}?code=${encodeURIComponent(code)}`;
}

interface NewsFile {
	code: string;
	asOf?: string;
	items?: NewsItem[];
}

/** 종목별 최근 뉴스 (date 내림차순). [] = 미지원·실패·미배선·해당없음. */
export function loadCompanyNews(code: string): Promise<NewsItem[]> {
	if (!browser) return Promise.resolve([]);
	const c = code.trim();
	const url = newsEndpoint(c);
	if (!url) return Promise.resolve([]); // 프로덕션 + 프록시 미설정 → 빈 섹션
	const hit = cache.get(c);
	if (hit) return Promise.resolve(hit);
	return (async () => {
		try {
			const res = await fetch(url);
			if (!res.ok) {
				cache.set(c, []);
				return [];
			}
			const j = (await res.json()) as NewsFile;
			const items = Array.isArray(j.items) ? j.items : [];
			cache.set(c, items);
			return items;
		} catch {
			cache.set(c, []);
			return [];
		}
	})();
}
