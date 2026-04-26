import type { PageLoad } from './$types';
import { base } from '$app/paths';

export const prerender = true;
export const ssr = false;

/**
 * Screener — 6 종 데이터 병렬 fetch.
 *
 * - ecosystem.json: 회사 노드 41 필드 (scan 20 축 + 정량·등급·변화)
 * - industryStats.json: 산업별 분포 (p10~p90, avgRoe 등)
 * - prices-snapshot.json: 회사별 시총·1Y 수익률·52주 H/L (매일 갱신)
 * - quarters.json: 20 분기 IS/CF/BS (PR-2 분기 derived 메트릭에서 활용)
 * - movers.json: 변화 감지 6 카테고리 (이상 신호 프리셋)
 * - meta.json: dataAsOf 신선도
 *
 * stockCode 로 frontend join 은 +page.svelte 에서.
 */
export const load: PageLoad = async ({ fetch }) => {
	const [ecoRes, statsRes, pricesRes, quartersRes, moversRes, metaRes] = await Promise.all([
		fetch(`${base}/map/ecosystem.json`),
		fetch(`${base}/map/industryStats.json`),
		fetch(`${base}/map/prices-snapshot.json`),
		fetch(`${base}/dashboards/quarters.json`),
		fetch(`${base}/map/movers.json`),
		fetch(`${base}/map/meta.json`)
	]);

	const ecosystem = ecoRes.ok ? await ecoRes.json() : { nodes: [], industries: [] };
	const industryStats = statsRes.ok ? await statsRes.json() : {};
	const pricesSnapshot = pricesRes.ok ? await pricesRes.json() : { data: {}, count: 0 };
	const quarters = quartersRes.ok ? await quartersRes.json() : { periods: [], companies: {} };
	const movers = moversRes.ok ? await moversRes.json() : { categories: {} };
	const meta = metaRes.ok ? await metaRes.json() : null;

	return { ecosystem, industryStats, pricesSnapshot, quarters, movers, meta };
};
