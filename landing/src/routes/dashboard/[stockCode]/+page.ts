import type { PageLoad } from './$types';
import { redirect } from '@sveltejs/kit';
import { base } from '$app/paths';

export const prerender = 'auto';
export const ssr = false;

export const load: PageLoad = async ({ params }) => {
	throw redirect(307, `${base}/company/${params.stockCode}`);
};
