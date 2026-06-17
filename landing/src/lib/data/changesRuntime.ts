import { readParquetRows, type FetchLike, type RangeRequestStat } from '@dartlab/ui-runtime/data/parquet/hfRange';

const CHANGES_PATH = 'dart/scan/changes.parquet';

let changesMapPromise: Promise<ChangesRuntimeResult> | null = null;
const companyChangesPromises = new Map<string, Promise<CompanyChange[]>>();

export interface ChangeMetrics {
	numericChanges1y: number;
	structuralChanges1y: number;
	totalChanges1y: number;
	recentChangeYear: number | null;
}

export interface CompanyChange {
	fromPeriod: string;
	toPeriod: string;
	sectionTitle: string;
	changeType: string;
	preview: string | null;
}

export interface ChangesRuntimeResult {
	metrics: Record<string, ChangeMetrics>;
	sourcePath: string;
	bytes: number;
	requests: number;
	durationMs: number;
}

interface ChangeMetricRow extends Record<string, unknown> {
	stockCode?: unknown;
	changeType?: unknown;
	toPeriod?: unknown;
}

interface CompanyChangeRow extends ChangeMetricRow {
	fromPeriod?: unknown;
	sectionTitle?: unknown;
	preview?: unknown;
}

export async function loadHfChangesMap(
	options: { year?: number; fetchFn?: FetchLike } = {}
): Promise<ChangesRuntimeResult> {
	if (!options.year && (!options.fetchFn || options.fetchFn === fetch)) {
		changesMapPromise ??= readHfChangesMap(options);
		return changesMapPromise;
	}
	return readHfChangesMap(options);
}

async function readHfChangesMap(
	options: { year?: number; fetchFn?: FetchLike } = {}
): Promise<ChangesRuntimeResult> {
	const t0 = performance.now();
	const currentYear = options.year ?? new Date().getFullYear();
	const lastYear = currentYear - 1;
	const data = await readParquetRows<ChangeMetricRow>(CHANGES_PATH, {
		columns: ['stockCode', 'changeType', 'toPeriod'],
		fetchFn: options.fetchFn ?? fetch
	});
	const metrics: Record<string, ChangeMetrics> = {};
	for (const row of data.rows) {
		const stockCode = String(row.stockCode ?? '').trim();
		const year = Number(row.toPeriod);
		if (!stockCode || !Number.isFinite(year) || year < lastYear) continue;
		const metric =
			metrics[stockCode] ??
			(metrics[stockCode] = {
				numericChanges1y: 0,
				structuralChanges1y: 0,
				totalChanges1y: 0,
				recentChangeYear: null
			});
		const changeType = String(row.changeType ?? '');
		if (changeType === 'numeric') metric.numericChanges1y += 1;
		if (changeType === 'structural') metric.structuralChanges1y += 1;
		metric.totalChanges1y += 1;
		metric.recentChangeYear = metric.recentChangeYear == null ? year : Math.max(metric.recentChangeYear, year);
	}
	return {
		metrics,
		sourcePath: CHANGES_PATH,
		bytes: sumBytes(data.requests),
		requests: data.requests.length,
		durationMs: performance.now() - t0
	};
}

export async function loadHfCompanyChanges(
	stockCode: string,
	limit = 3,
	fetchFn: FetchLike = fetch
): Promise<CompanyChange[]> {
	const cacheKey = fetchFn === fetch ? `${stockCode}:${limit}` : '';
	if (cacheKey) {
		let cached = companyChangesPromises.get(cacheKey);
		if (!cached) {
			cached = readHfCompanyChanges(stockCode, limit, fetchFn);
			companyChangesPromises.set(cacheKey, cached);
		}
		return cached;
	}
	return readHfCompanyChanges(stockCode, limit, fetchFn);
}

async function readHfCompanyChanges(
	stockCode: string,
	limit = 3,
	fetchFn: FetchLike = fetch
): Promise<CompanyChange[]> {
	const data = await readParquetRows<CompanyChangeRow>(CHANGES_PATH, {
		columns: ['stockCode', 'fromPeriod', 'toPeriod', 'sectionTitle', 'changeType', 'preview'],
		filter: { stockCode: { $eq: stockCode } },
		fetchFn
	});
	return data.rows
		.map((row) => ({
			fromPeriod: String(row.fromPeriod ?? ''),
			toPeriod: String(row.toPeriod ?? ''),
			sectionTitle: String(row.sectionTitle ?? ''),
			changeType: String(row.changeType ?? ''),
			preview: row.preview == null ? null : String(row.preview)
		}))
		.sort((a, b) => b.toPeriod.localeCompare(a.toPeriod) || a.sectionTitle.localeCompare(b.sectionTitle, 'ko-KR'))
		.slice(0, limit);
}

function sumBytes(requests: RangeRequestStat[]): number {
	return requests.reduce((sum, req) => sum + req.bytes, 0);
}
