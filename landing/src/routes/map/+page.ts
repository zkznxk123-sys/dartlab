import type { PageLoad } from './$types';
import { base } from '$app/paths';

export const prerender = true;
export const ssr = false; // WebGL은 서버 렌더 불가 — 클라이언트 전용

export const load: PageLoad = async ({ fetch }) => {
	const [ecoRes, atlasRes] = await Promise.all([
		fetch(`${base}/map/ecosystem.json`),
		fetch(`${base}/map/atlas.json`)
	]);
	if (!ecoRes.ok) throw new Error('ecosystem.json 로드 실패');
	if (!atlasRes.ok) throw new Error('atlas.json 로드 실패');
	const ecosystem = await ecoRes.json();
	const atlas = await atlasRes.json();
	return { ecosystem, atlas };
};
