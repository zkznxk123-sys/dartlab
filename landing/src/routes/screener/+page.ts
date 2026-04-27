import type { PageLoad } from './$types';
import { base } from '$app/paths';

export const prerender = true;
export const ssr = false;

/**
 * Screener — 5 종 메타 JSON 병렬 fetch.
 *
 * 가격·시총·1Y 수익률 등은 page.svelte 가 DuckDB-WASM 으로 HF KRX parquet 을
 * 직접 query 하여 즉석 계산. prices-snapshot.json 같은 중간 prebuild 산출물 없음.
 *
 * - ecosystem.json: 회사 노드 41 필드 (scan 20 축 + 정량·등급·변화)
 * - industryStats.json: 산업별 분포 (p10~p90, avgRoe 등)
 * - quarters.json: 20 분기 IS/CF/BS (분기 derived 메트릭) — v2 후속에서 finance-lite.parquet 로 이전
 * - movers.json: 변화 감지 6 카테고리 (이상 신호 프리셋)
 * - meta.json: dataAsOf 신선도
 *
 * stockCode 로 frontend join 은 +page.svelte 에서.
 */
export const load: PageLoad = async ({ fetch }) => {
	const [ecoRes, statsRes, quartersRes, moversRes, metaRes] = await Promise.all([
		fetch(`${base}/map/ecosystem.json`),
		fetch(`${base}/map/industryStats.json`),
		fetch(`${base}/dashboards/quarters.json`),
		fetch(`${base}/map/movers.json`),
		fetch(`${base}/map/meta.json`)
	]);

	const ecosystem = ecoRes.ok ? await ecoRes.json() : { nodes: [], industries: [] };
	const industryStats = statsRes.ok ? await statsRes.json() : {};
	const quarters = quartersRes.ok ? await quartersRes.json() : { periods: [], companies: {} };
	const movers = moversRes.ok ? await moversRes.json() : { categories: {} };
	const meta = metaRes.ok ? await metaRes.json() : null;

	return { ecosystem, industryStats, quarters, movers, meta };
};
