import type { PageLoad } from './$types';
import { base } from '$app/paths';
import { error } from '@sveltejs/kit';

export const prerender = 'auto';
export const ssr = false;

export const load: PageLoad = async ({ params, fetch }) => {
	const { stockCode } = params;

	const [dashRes, ecoRes] = await Promise.all([
		fetch(`${base}/dashboards/${stockCode}.json`),
		fetch(`${base}/map/ecosystem.json`)
	]);

	if (!dashRes.ok) {
		throw error(404, `Dashboard not found for ${stockCode}`);
	}

	const dashboard = await dashRes.json();
	const ecosystem = ecoRes.ok ? await ecoRes.json() : null;

	// ecosystem.json에서 회사 기본 정보 merge
	const node = ecosystem?.nodes?.find((n: any) => n.id === stockCode) || null;
	const industry = ecosystem?.industries?.find((i: any) => i.id === node?.industry) || null;

	return { stockCode, dashboard, node, industry };
};
