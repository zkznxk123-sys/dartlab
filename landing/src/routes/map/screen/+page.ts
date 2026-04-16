import type { PageLoad } from './$types';
import { base } from '$app/paths';

export const prerender = true;
export const ssr = false;

export const load: PageLoad = async ({ fetch }) => {
	const [ecoRes, statsRes, metaRes] = await Promise.all([
		fetch(`${base}/map/ecosystem.json`),
		fetch(`${base}/map/industryStats.json`),
		fetch(`${base}/map/meta.json`)
	]);
	const ecosystem = ecoRes.ok ? await ecoRes.json() : { nodes: [], industries: [] };
	const industryStats = statsRes.ok ? await statsRes.json() : {};
	const meta = metaRes.ok ? await metaRes.json() : null;
	return { ecosystem, industryStats, meta };
};
