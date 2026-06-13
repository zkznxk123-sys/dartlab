// 로컬 company 포트 — /api/company/{code}/meta. 단일회사 lazy fetch (전 종목 인덱스 미보유 = null).
import type { CompanyPort, CompanyRelations, ProductIndexItem } from '@dartlab/ui-contracts';
import { getJson } from '../fetchJson';
import type { CompanyMeta, LocalCaches } from '../localTypes';

function loadMeta(apiBase: string, caches: LocalCaches, code: string): Promise<CompanyMeta | null> {
	const c = code.trim();
	let p = caches.meta.get(c);
	if (!p) {
		p = getJson<CompanyMeta>(apiBase, `/api/company/${encodeURIComponent(c)}/meta`);
		caches.meta.set(c, p);
	}
	return p;
}

export function localCompanyPort(apiBase: string, caches: LocalCaches): CompanyPort {
	return {
		async products(code) {
			const meta = await loadMeta(apiBase, caches, code);
			if (!meta) return null;
			return {
				product: meta.products.slice(0, 4).join(', '),
				productRaw: meta.products.join(', '),
				latestPeriod: '',
				industry: meta.sector || undefined
			} satisfies ProductIndexItem;
		},
		// 로컬 서버는 전 종목 product 인덱스 미보유 — null = 미지원 정직 표기.
		async productIndex() {
			return null;
		},
		async relations(code) {
			const meta = await loadMeta(apiBase, caches, code);
			if (!meta || !meta.corpName) return null;
			// 로컬 관계망 정규화는 단계-8(scan/map) 영역 — 회사 존재 시 빈 관계 반환(null 아님).
			return {
				suppliers: [],
				customers: [],
				peers: [],
				neighborCount: 0,
				blog: null
			} satisfies CompanyRelations;
		},
		// 라이브 보고서 팩트 — 로컬 미배선. 해당 없음 = [].
		async reportFacts() {
			return [];
		}
	};
}
