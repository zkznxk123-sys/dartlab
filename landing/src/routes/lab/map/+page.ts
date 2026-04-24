import type { PageLoad } from './$types';
import { base } from '$app/paths';

export const prerender = true;
export const ssr = false;

async function fetchJson(url: string, fetchFn: typeof fetch) {
	try {
		const r = await fetchFn(url);
		return r.ok ? await r.json() : null;
	} catch {
		return null;
	}
}

export const load: PageLoad = async ({ fetch }) => {
	const [ecosystem, atlas, movers, insights, industryStats, timeline] = await Promise.all([
		fetchJson(`${base}/map/ecosystem.json`, fetch),
		fetchJson(`${base}/map/atlas.json`, fetch),
		fetchJson(`${base}/map/movers.json`, fetch),
		fetchJson(`${base}/map/insights.json`, fetch),
		fetchJson(`${base}/map/industryStats.json`, fetch),
		fetchJson(`${base}/map/timeline.json`, fetch)
	]);
	return {
		ecosystem: ecosystem ?? { nodes: [], links: [], industries: [] },
		atlas: atlas ?? { industries: [], flows: [] },
		movers,
		insights,
		industryStats,
		timeline
	};
};
