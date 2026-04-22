import type { PageLoad } from './$types';
import { base } from '$app/paths';

export const prerender = 'auto';
export const ssr = false;

const HF = 'https://huggingface.co/datasets/eddmpython/dartlab-data/resolve/main';

async function fetchJson(url: string, fetchFn: typeof fetch) {
	try {
		const r = await fetchFn(url);
		return r.ok ? await r.json() : null;
	} catch {
		return null;
	}
}

export const load: PageLoad = async ({ params, fetch }) => {
	const { stockCode } = params;

	// 글로벌 정적 파일 (GitHub Pages, 모든 대시보드 페이지가 캐시 공유)
	const globalP = Promise.all([
		fetchJson(`${base}/map/ecosystem.json`, fetch),
		fetchJson(`${base}/dashboards/finance.json`, fetch),
		fetchJson(`${base}/dashboards/quarters.json`, fetch),
		fetchJson(`${base}/dashboards/meta.json`, fetch),
		fetchJson(`${base}/dashboards/macro.json`, fetch)
	]);

	// 회사 메타 — 로컬 우선, HF CDN 폴백 (dartlab CI 가 매번 prebuild 후 HF 업로드)
	const companyMetaP = (async () => {
		const local = await fetchJson(`${base}/map/companies/${stockCode}.json`, fetch);
		if (local) return local;
		return await fetchJson(`${HF}/landing/map/companies/${stockCode}.json`, fetch);
	})();

	const [[ecosystem, finance, quarters, meta, macro], companyMeta] = await Promise.all([
		globalP,
		companyMetaP
	]);

	return {
		stockCode,
		ecosystem: ecosystem ?? { nodes: [], links: [] },
		finance: finance ?? { companies: {}, years: [] },
		quarters: quarters ?? { companies: {}, periods: [] },
		meta: meta ?? { engines: [], blog: {}, thesisTemplates: {} },
		macro,
		companyMeta,
		version: 'v22'
	};
};
