import { readParquetMetadata, readParquetRows, type RangeRequestStat } from './hfRange';

export interface PriceRuntimeMetrics {
	currentPrice: number | null;
	marketCap: number | null;
	ma20: number | null;
	high60: number | null;
	low60: number | null;
	week52High: number | null;
	week52Low: number | null;
	volumeAvg30d: number | null;
	volatility1y: number | null;
	return1m: number | null;
	return3m: number | null;
	return1y: number | null;
	spark30: number[];
	spark60: number[];
	spark: number[];
}

export interface PriceRuntimeResult {
	metrics: Record<string, PriceRuntimeMetrics>;
	latestDate: string;
	sourcePaths: string[];
	bytes: number;
	requests: number;
	durationMs: number;
	partial: boolean;
}

interface KrxPriceRow extends Record<string, unknown> {
	BAS_DD?: string | number | null;
	ISU_CD?: string | null;
	TDD_CLSPRC?: string | number | null;
	TDD_HGPRC?: string | number | null;
	TDD_LWPRC?: string | number | null;
	ACC_TRDVOL?: string | number | null;
	MKTCAP?: string | number | null;
}

interface NormalizedPriceRow {
	date: string;
	code: string;
	close: number;
	high: number | null;
	low: number | null;
	volume: number | null;
	marketCap: number | null;
}

export interface PriceTailOptions {
	year?: number;
	currentTailRows?: number;
	previousTailRows?: number;
	fetchFn?: typeof fetch;
}

const PRICE_COLUMNS = [
	'BAS_DD',
	'ISU_CD',
	'TDD_CLSPRC',
	'TDD_HGPRC',
	'TDD_LWPRC',
	'ACC_TRDVOL',
	'MKTCAP'
];

const DEFAULT_CURRENT_TAIL_ROWS = 180_000;
const DEFAULT_PREVIOUS_TAIL_ROWS = 500_000;

export async function loadCurrentPriceTail(
	options: PriceTailOptions = {}
): Promise<PriceRuntimeResult & { rows: NormalizedPriceRow[] }> {
	const year = options.year ?? new Date().getFullYear();
	return loadPriceTailYear(year, options.currentTailRows ?? DEFAULT_CURRENT_TAIL_ROWS, true, options.fetchFn);
}

export async function loadOneYearPriceTail(
	currentRows: NormalizedPriceRow[],
	options: PriceTailOptions = {}
): Promise<PriceRuntimeResult> {
	const year = options.year ?? new Date().getFullYear();
	const prev = await loadPriceTailYear(
		year - 1,
		options.previousTailRows ?? DEFAULT_PREVIOUS_TAIL_ROWS,
		false,
		options.fetchFn
	);
	const rows = [...prev.rows, ...currentRows];
	const result = buildPriceResult(rows, [prev.sourcePaths[0], `krx/prices/raw-${year}.parquet`], false);
	return {
		...result,
		bytes: prev.bytes,
		requests: prev.requests,
		durationMs: prev.durationMs
	};
}

async function loadPriceTailYear(
	year: number,
	tailRows: number,
	partial: boolean,
	fetchFn?: typeof fetch
): Promise<PriceRuntimeResult & { rows: NormalizedPriceRow[] }> {
	const t0 = performance.now();
	const path = `krx/prices/raw-${year}.parquet`;
	const metadata = await readParquetMetadata(path, fetchFn ?? fetch);
	const rowEnd = metadata.rows;
	const rowStart = Math.max(0, rowEnd - tailRows);
	const data = await readParquetRows<KrxPriceRow>(path, {
		columns: PRICE_COLUMNS,
		rowStart,
		rowEnd,
		fetchFn: fetchFn ?? fetch
	});
	const requests = [...metadata.requests, ...data.requests];
	const rows = data.rows.map(normalizeRow).filter((row): row is NormalizedPriceRow => row != null);
	const result = buildPriceResult(rows, [path], partial);
	return {
		...result,
		rows,
		bytes: sumBytes(requests),
		requests: requests.length,
		durationMs: performance.now() - t0
	};
}

function buildPriceResult(
	rows: NormalizedPriceRow[],
	sourcePaths: string[],
	partial: boolean
): PriceRuntimeResult {
	const byCode = new Map<string, NormalizedPriceRow[]>();
	let latestDate = '';
	for (const row of rows) {
		if (row.date > latestDate) latestDate = row.date;
		let bucket = byCode.get(row.code);
		if (!bucket) {
			bucket = [];
			byCode.set(row.code, bucket);
		}
		bucket.push(row);
	}
	const metrics: Record<string, PriceRuntimeMetrics> = {};
	for (const [code, values] of byCode.entries()) {
		values.sort((a, b) => a.date.localeCompare(b.date));
		metrics[code] = buildMetrics(values, partial);
	}
	return {
		metrics,
		latestDate,
		sourcePaths,
		bytes: 0,
		requests: 0,
		durationMs: 0,
		partial
	};
}

function buildMetrics(rows: NormalizedPriceRow[], partial: boolean): PriceRuntimeMetrics {
	const latest = rows[rows.length - 1];
	const closes = rows.map((row) => row.close).filter((value) => Number.isFinite(value));
	const last60 = rows.slice(-60);
	const last252 = rows.slice(-252);
	const currentPrice = latest?.close ?? null;
	return {
		currentPrice,
		marketCap: latest?.marketCap ?? null,
		ma20: average(rows.slice(-20).map((row) => row.close)),
		high60: max(last60.map((row) => row.high)),
		low60: min(last60.map((row) => row.low)),
		week52High: partial ? null : max(last252.map((row) => row.high)),
		week52Low: partial ? null : min(last252.map((row) => row.low)),
		volumeAvg30d: average(rows.slice(-30).map((row) => row.volume)),
		volatility1y: partial ? null : annualizedVolatility(closes.slice(-252)),
		return1m: pctReturn(currentPrice, nthFromEnd(closes, 21)),
		return3m: pctReturn(currentPrice, nthFromEnd(closes, 63)),
		return1y: partial ? null : pctReturn(currentPrice, nthFromEnd(closes, 252)),
		spark30: rows.slice(-30).map((row) => row.close),
		spark60: last60.map((row) => row.close),
		spark: partial ? [] : downsample(last252.map((row) => row.close), 50)
	};
}

function normalizeRow(row: KrxPriceRow): NormalizedPriceRow | null {
	const code = stockCode(row.ISU_CD);
	const close = numberOrNull(row.TDD_CLSPRC);
	if (!code || close == null) return null;
	return {
		date: row.BAS_DD == null ? '' : String(row.BAS_DD),
		code,
		close,
		high: numberOrNull(row.TDD_HGPRC),
		low: numberOrNull(row.TDD_LWPRC),
		volume: numberOrNull(row.ACC_TRDVOL),
		marketCap: numberOrNull(row.MKTCAP)
	};
}

function stockCode(isuCd: string | null | undefined): string {
	if (!isuCd) return '';
	return isuCd.startsWith('A') ? isuCd.slice(1) : isuCd;
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

function nthFromEnd(values: number[], offset: number): number | null {
	if (values.length <= offset) return null;
	return values[values.length - 1 - offset] ?? null;
}

function pctReturn(current: number | null, past: number | null): number | null {
	if (current == null || past == null || past === 0) return null;
	return (current / past - 1) * 100;
}

function average(values: Array<number | null>): number | null {
	const valid = values.filter((value): value is number => typeof value === 'number' && Number.isFinite(value));
	if (valid.length === 0) return null;
	return valid.reduce((sum, value) => sum + value, 0) / valid.length;
}

function max(values: Array<number | null>): number | null {
	const valid = values.filter((value): value is number => typeof value === 'number' && Number.isFinite(value));
	return valid.length > 0 ? Math.max(...valid) : null;
}

function min(values: Array<number | null>): number | null {
	const valid = values.filter((value): value is number => typeof value === 'number' && Number.isFinite(value));
	return valid.length > 0 ? Math.min(...valid) : null;
}

function annualizedVolatility(closes: number[]): number | null {
	const returns: number[] = [];
	for (let i = 1; i < closes.length; i += 1) {
		const prev = closes[i - 1];
		const curr = closes[i];
		if (prev > 0 && curr > 0) returns.push(Math.log(curr / prev));
	}
	if (returns.length < 2) return null;
	const mean = returns.reduce((sum, value) => sum + value, 0) / returns.length;
	const variance =
		returns.reduce((sum, value) => sum + Math.pow(value - mean, 2), 0) / (returns.length - 1);
	return Math.sqrt(variance) * Math.sqrt(252) * 100;
}

function downsample(values: number[], maxPoints: number): number[] {
	if (values.length <= maxPoints) return values;
	const result: number[] = [];
	const step = (values.length - 1) / (maxPoints - 1);
	for (let i = 0; i < maxPoints; i += 1) {
		result.push(values[Math.round(i * step)]);
	}
	return result;
}

function sumBytes(requests: RangeRequestStat[]): number {
	return requests.reduce((sum, req) => sum + req.bytes, 0);
}
