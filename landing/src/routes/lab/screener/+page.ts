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
	const ecosystem = await fetchJson(`${base}/map/ecosystem.json`, fetch);
	return { ecosystem: ecosystem ?? { nodes: [], industries: [] } };
};
