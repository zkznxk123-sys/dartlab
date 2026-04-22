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

// 로컬 우선 · HF 폴백 (landing 이 prebuild 한 파일이 HF 에 미러링 됨)
async function fetchLocalOrHf(path: string, fetchFn: typeof fetch) {
	const local = await fetchJson(`${base}/${path}`, fetchFn);
	if (local) return local;
	return await fetchJson(`${HF}/landing/${path}`, fetchFn);
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

	// 회사 메타
	const companyMetaP = fetchLocalOrHf(`map/companies/${stockCode}.json`, fetch);

	const [[ecosystem, finance, quarters, meta, macro], companyMeta] = await Promise.all([
		globalP,
		companyMetaP
	]);

	// industry 추출 — companyMeta.ego.industry 우선, 없으면 ecosystem node lookup
	const industryId =
		companyMeta?.ego?.industry ??
		ecosystem?.nodes?.find((n: any) => n.id === stockCode)?.industry ??
		null;

	// 업종 파일 fetch (100% 커버 — 34 업종 모두 prebuild 되어 있음)
	const industryMeta = industryId
		? await fetchLocalOrHf(`map/industries/${industryId}.json`, fetch)
		: null;

	return {
		stockCode,
		ecosystem: ecosystem ?? { nodes: [], links: [] },
		finance: finance ?? { companies: {}, years: [] },
		quarters: quarters ?? { companies: {}, periods: [] },
		meta: meta ?? { engines: [], blog: {}, thesisTemplates: {} },
		macro,
		companyMeta,
		industryMeta,
		industryId,
		version: 'v23'
	};
};
