import { readParquetRows } from '@dartlab/ui-runtime/data/parquet/hfRange';
import type { FetchLike } from '@dartlab/ui-runtime/data/dartlabData';

const VALUATION_PATH = 'dart/scan/valuation.parquet';

let valuationPromise: Promise<Map<string, ValuationRuntimeMetrics>> | null = null;

export interface ValuationRuntimeMetrics {
	currentPrice: number | null;
	marketCap: number | null;
	per: number | null;
	pbr: number | null;
	dividendYield: number | null;
}

interface ValuationRow {
	[key: string]: unknown;
	stockCode?: unknown;
	marketCap?: unknown;
	per?: unknown;
	pbr?: unknown;
	dividendYield?: unknown;
	current?: unknown;
}

export async function loadHfValuationMap(
	fetchFn: FetchLike = fetch
): Promise<Map<string, ValuationRuntimeMetrics>> {
	valuationPromise ??= readValuation(fetchFn);
	return valuationPromise;
}

export async function loadHfValuationFor(
	stockCode: string,
	fetchFn: FetchLike = fetch
): Promise<ValuationRuntimeMetrics | null> {
	const map = await loadHfValuationMap(fetchFn);
	return map.get(stockCode) ?? null;
}

async function readValuation(fetchFn: FetchLike): Promise<Map<string, ValuationRuntimeMetrics>> {
	const { rows } = await readParquetRows<ValuationRow>(VALUATION_PATH, {
		fetchFn,
		columns: ['stockCode', 'marketCap', 'per', 'pbr', 'dividendYield', 'current']
	});
	const map = new Map<string, ValuationRuntimeMetrics>();
	for (const row of rows) {
		const stockCode = String(row.stockCode ?? '').trim();
		if (!stockCode) continue;
		map.set(stockCode, {
			currentPrice: numberOrNull(row.current),
			marketCap: numberOrNull(row.marketCap),
			per: numberOrNull(row.per),
			pbr: numberOrNull(row.pbr),
			dividendYield: numberOrNull(row.dividendYield)
		});
	}
	return map;
}

function numberOrNull(value: unknown): number | null {
	if (typeof value === 'number') return Number.isFinite(value) ? value : null;
	if (typeof value === 'bigint') {
		const n = Number(value);
		return Number.isFinite(n) ? n : null;
	}
	if (typeof value === 'string' && value.trim()) {
		const n = Number(value.replace(/,/g, ''));
		return Number.isFinite(n) ? n : null;
	}
	return null;
}
