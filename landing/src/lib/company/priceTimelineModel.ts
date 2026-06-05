import type { RegularFiling } from '$lib/data/companyFilingsRuntime';

export interface CompanyPriceRawRow extends Record<string, unknown> {
	date?: unknown;
	stockCode?: unknown;
	name?: unknown;
	market?: unknown;
	open?: unknown;
	high?: unknown;
	low?: unknown;
	close?: unknown;
	priceChange?: unknown;
	fluctuationRate?: unknown;
	volume?: unknown;
	tradedValue?: unknown;
	marketCap?: unknown;
	listedShares?: unknown;
}

export interface PricePoint {
	date: string;
	stockCode: string;
	name: string;
	market: string;
	open: number | null;
	high: number | null;
	low: number | null;
	close: number | null;
	priceChange: number | null;
	fluctuationRate: number | null;
	volume: number | null;
	tradedValue: number | null;
	marketCap: number | null;
	listedShares: number | null;
}

export interface TimelineMarker {
	filing: RegularFiling;
	point: PricePoint | null;
	index: number;
}

export interface TimelineStats {
	latest: PricePoint | null;
	first: PricePoint | null;
	returnPct: number | null;
	high: number | null;
	low: number | null;
	avgVolume: number | null;
}

export function normalizePriceRows(rows: CompanyPriceRawRow[], stockCode: string): PricePoint[] {
	const wanted = cleanCode(stockCode);
	const points = rows
		.map((row) => {
			const code = cleanCode(str(row.stockCode));
			const date = normalizeDate(str(row.date));
			return {
				date,
				stockCode: code,
				name: str(row.name),
				market: str(row.market),
				open: num(row.open),
				high: num(row.high),
				low: num(row.low),
				close: num(row.close),
				priceChange: num(row.priceChange),
				fluctuationRate: num(row.fluctuationRate),
				volume: num(row.volume),
				tradedValue: num(row.tradedValue),
				marketCap: num(row.marketCap),
				listedShares: num(row.listedShares)
			};
		})
		.filter((row) => row.date.length === 8 && (!wanted || row.stockCode === wanted))
		.sort((a, b) => a.date.localeCompare(b.date));

	const dedup = new Map<string, PricePoint>();
	for (const point of points) dedup.set(point.date, point);
	return Array.from(dedup.values());
}

export function alignFilingsToPrices(points: PricePoint[], filings: RegularFiling[]): TimelineMarker[] {
	if (!points.length || !filings.length) return [];
	return filings
		.filter((filing) => normalizeDate(filing.rceptDate).length === 8)
		.map((filing) => {
			const date = normalizeDate(filing.rceptDate);
			const idx = nearestTradingIndex(points, date);
			return { filing, point: points[idx] ?? null, index: idx };
		})
		.filter((marker) => marker.point != null);
}

export function summarizeTimeline(points: PricePoint[]): TimelineStats {
	const priced = points.filter((point) => point.close != null && point.close > 0);
	const latest = priced.at(-1) ?? null;
	const first = priced[0] ?? null;
	const returnPct =
		latest?.close != null && first?.close != null && first.close !== 0
			? (latest.close / first.close - 1) * 100
			: null;
	const highs = points.map((point) => point.high).filter(isFiniteNumber);
	const lows = points.map((point) => point.low).filter((value): value is number => isFiniteNumber(value) && value > 0);
	const volumes = points.map((point) => point.volume).filter(isFiniteNumber);
	return {
		latest,
		first,
		returnPct,
		high: highs.length ? Math.max(...highs) : null,
		low: lows.length ? Math.min(...lows) : null,
		avgVolume: volumes.length ? volumes.reduce((sum, value) => sum + value, 0) / volumes.length : null
	};
}

function nearestTradingIndex(points: PricePoint[], date: string): number {
	let lo = 0;
	let hi = points.length - 1;
	let best = points.length - 1;
	while (lo <= hi) {
		const mid = Math.floor((lo + hi) / 2);
		if (points[mid].date >= date) {
			best = mid;
			hi = mid - 1;
		} else {
			lo = mid + 1;
		}
	}
	return best;
}

function cleanCode(value: string): string {
	return value.trim().replace(/^A/, '');
}

function normalizeDate(value: string): string {
	return value.replace(/[^0-9]/g, '').slice(0, 8);
}

function str(value: unknown): string {
	return value == null ? '' : String(value).trim();
}

function num(value: unknown): number | null {
	if (value == null || value === '') return null;
	if (typeof value === 'number') return Number.isFinite(value) ? value : null;
	if (typeof value === 'bigint') return Number(value);
	const n = Number(String(value).replace(/,/g, '').trim());
	return Number.isFinite(n) ? n : null;
}

function isFiniteNumber(value: number | null): value is number {
	return typeof value === 'number' && Number.isFinite(value);
}
