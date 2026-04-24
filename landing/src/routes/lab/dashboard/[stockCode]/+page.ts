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

async function fetchLocalOrHf(path: string, fetchFn: typeof fetch) {
	const local = await fetchJson(`${base}/${path}`, fetchFn);
	if (local) return local;
	return await fetchJson(`${HF}/landing/${path}`, fetchFn);
}

export const load: PageLoad = async ({ params, fetch }) => {
	const { stockCode } = params;

	const [ecosystem, finance, quarters, meta, macro] = await Promise.all([
		fetchJson(`${base}/map/ecosystem.json`, fetch),
		fetchJson(`${base}/dashboards/finance.json`, fetch),
		fetchJson(`${base}/dashboards/quarters.json`, fetch),
		fetchJson(`${base}/dashboards/meta.json`, fetch),
		fetchJson(`${base}/dashboards/macro.json`, fetch)
	]);

	const companyMeta = await fetchLocalOrHf(`map/companies/${stockCode}.json`, fetch);
	const industryId =
		companyMeta?.ego?.industry ??
		ecosystem?.nodes?.find((n: any) => n.id === stockCode)?.industry ??
		null;
	const industryMeta = industryId
		? await fetchLocalOrHf(`map/industries/${industryId}.json`, fetch)
		: null;

	return {
		stockCode,
		ecosystem: ecosystem ?? { nodes: [], links: [], industries: [] },
		finance: finance ?? { companies: {}, years: [] },
		quarters: quarters ?? { companies: {}, periods: [] },
		meta: meta ?? null,
		macro,
		companyMeta,
		industryMeta,
		industryId
	};
};
