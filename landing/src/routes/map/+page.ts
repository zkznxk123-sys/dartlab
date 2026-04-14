import type { PageLoad } from './$types';

export const prerender = true;
export const ssr = false; // WebGL은 서버 렌더 불가 — 클라이언트 전용

export const load: PageLoad = async ({ fetch }) => {
	const res = await fetch('/map/ecosystem.json');
	if (!res.ok) throw new Error('ecosystem.json 로드 실패');
	const data = await res.json();
	return { ecosystem: data };
};
