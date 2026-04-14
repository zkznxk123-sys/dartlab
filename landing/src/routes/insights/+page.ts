import type { PageLoad } from './$types';
import { base } from '$app/paths';

export const prerender = true;

export const load: PageLoad = async ({ fetch }) => {
	const res = await fetch(`${base}/map/insights.json`);
	const data = await res.json();
	return { data };
};
