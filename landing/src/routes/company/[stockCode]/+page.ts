import type { PageLoad } from './$types';
import { error } from '@sveltejs/kit';
import { base } from '$app/paths';

export const prerender = true;

export const load: PageLoad = async ({ params, fetch }) => {
	const { stockCode } = params;
	const res = await fetch(`${base}/map/companies/${stockCode}.json`);
	if (!res.ok) {
		throw error(404, `회사 데이터 없음: ${stockCode}`);
	}
	const data = await res.json();
	return { stockCode, data };
};
