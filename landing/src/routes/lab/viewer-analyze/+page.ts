import type { PageLoad } from './$types';

export const ssr = false;
export const prerender = 'auto';

export const load: PageLoad = ({ url }) => {
	return {
		code: (url.searchParams.get('code') || '005930').trim().toUpperCase()
	};
};
