import type { PageLoad } from './$types';
import { error } from '@sveltejs/kit';
import { base } from '$app/paths';

export const prerender = true;

export const load: PageLoad = async ({ params, fetch }) => {
	const { id } = params;
	const [detailRes, statsRes, moversRes, metaRes] = await Promise.all([
		fetch(`${base}/map/industries/${id}.json`),
		fetch(`${base}/map/industryStats.json`),
		fetch(`${base}/map/movers.json`),
		fetch(`${base}/map/meta.json`)
	]);
	if (!detailRes.ok) {
		throw error(404, `산업 데이터 없음: ${id}`);
	}
	const data = await detailRes.json();
	const industryStats = statsRes.ok ? await statsRes.json() : {};
	const allMovers = moversRes.ok ? await moversRes.json() : null;
	const meta = metaRes.ok ? await metaRes.json() : null;

	// 이 산업 소속 회사의 movers만 필터
	const indMovers: Record<string, any[]> = {};
	if (allMovers?.categories) {
		for (const [catKey, cat] of Object.entries(allMovers.categories) as [string, any][]) {
			indMovers[catKey] = (cat.entries || []).filter((e: any) => e.industry === id);
		}
	}

	return {
		id,
		data,
		stats: industryStats[id] || null,
		movers: indMovers,
		moversDisclaimer: allMovers?.disclaimer || '',
		meta
	};
};
