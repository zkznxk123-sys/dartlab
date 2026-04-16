import type { PageLoad } from './$types';
import { base } from '$app/paths';

export const prerender = false;
export const ssr = false;

export const load: PageLoad = async ({ fetch }) => {
	// ecosystem + industryStats + meta 필요 (회사 lookup + 업종 정규화)
	const [ecoRes, statsRes, metaRes] = await Promise.all([
		fetch(`${base}/map/ecosystem.json`),
		fetch(`${base}/map/industryStats.json`),
		fetch(`${base}/map/meta.json`)
	]);
	const ecosystem = ecoRes.ok ? await ecoRes.json() : { nodes: [] };
	const industryStats = statsRes.ok ? await statsRes.json() : {};
	const meta = metaRes.ok ? await metaRes.json() : null;
	return { ecosystem, industryStats, meta };
};
