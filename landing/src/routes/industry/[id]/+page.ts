import type { PageLoad } from './$types';
import { error } from '@sveltejs/kit';
import { base } from '$app/paths';

export const prerender = true;

export const load: PageLoad = async ({ params, fetch }) => {
	const { id } = params;
	const res = await fetch(`${base}/map/industries/${id}.json`);
	if (!res.ok) {
		throw error(404, `산업 데이터 없음: ${id}`);
	}
	const data = await res.json();
	return { id, data };
};
