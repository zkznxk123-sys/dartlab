import type { PageLoad } from './$types';
import { base } from '$app/paths';

export const prerender = true;

export const load: PageLoad = async ({ fetch }) => {
	const [moversRes, metaRes] = await Promise.all([
		fetch(`${base}/map/movers.json`),
		fetch(`${base}/map/meta.json`)
	]);
	const movers = moversRes.ok ? await moversRes.json() : { categories: {}, disclaimer: '' };
	const meta = metaRes.ok ? await metaRes.json() : null;
	return { movers, meta };
};
