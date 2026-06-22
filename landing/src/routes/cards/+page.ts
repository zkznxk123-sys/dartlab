import type { PageLoad } from './$types';

// 라이브 카드 캐러셀 — /report 와 동일하게 굽지 않음(조회 시점 조립). HF parquet·hfMedia 를 브라우저가 직독.
export const ssr = false;
export const prerender = false;

export const load: PageLoad = ({ url }) => {
	const sym = url.searchParams.get('sym') || '';
	const perspective = url.searchParams.get('view') || 'earningsPower';
	return { sym, perspective };
};
