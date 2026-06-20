import type { PageLoad } from './$types';

// dev 격리 라우트 — 데이터 작업대 리얼타임. 정적 story JSON fetch 폐기(조회 시점 조립).
export const ssr = false;
export const prerender = false;

export const load: PageLoad = ({ url }) => {
	const sym = url.searchParams.get('sym') || '005930';
	// 관점 키 — 레거시 'type=full' 은 첫 관점(수익체력)으로 매핑.
	const raw = url.searchParams.get('view') || url.searchParams.get('type') || 'earningsPower';
	const perspective = raw === 'full' ? 'earningsPower' : raw;
	return { sym, perspective };
};
