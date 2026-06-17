import { readParquetRows, type FetchLike, type RangeRequestStat } from '@dartlab/ui-runtime/data/parquet/hfRange';
import {
	FINANCE_ACCOUNTS,
	FINANCE_COMPLETED_YEARS,
	financeGrowthKey,
	financeMetricKey,
	financeRatioKey,
	type FinanceAccountSpec
} from './financeAccounts';

const FINANCE_LITE_PATH = 'dart/scan/finance-lite.parquet';

type FinanceLiteRow = Record<string, unknown> & {
	stockCode?: unknown;
	bsns_year?: unknown;
	reprt_nm?: unknown;
	sj_div?: unknown;
	fs_nm?: unknown;
	account_id?: unknown;
	account_nm?: unknown;
	thstrm_amount?: unknown;
	thstrm_add_amount?: unknown;
};

export interface FinanceLiteRuntimeResult {
	rows: Array<Record<string, unknown> & { id: string }>;
	years: string[];
	requests: RangeRequestStat[];
	sourcePath: string;
}

export interface CompanyFinancePeriodRow {
	period: string;
	label: string;
	year: string;
	quarter: number;
	values: Record<string, number>;
}

const ACCOUNT_BY_ID = new Map<string, FinanceAccountSpec>();
const ACCOUNT_BY_NAME = new Map<string, FinanceAccountSpec[]>();

for (const account of FINANCE_ACCOUNTS) {
	for (const id of account.ids) ACCOUNT_BY_ID.set(id, account);
	for (const name of account.names) {
		const key = normalizeName(name);
		const list = ACCOUNT_BY_NAME.get(key) ?? [];
		list.push(account);
		ACCOUNT_BY_NAME.set(key, list);
	}
}

let financePromise: Promise<FinanceLiteRuntimeResult> | null = null;
const companyFinancePromises = new Map<string, Promise<CompanyFinancePeriodRow[]>>();
const MAX_COMPANY_FINANCE_CACHE = 24;

export async function loadFinanceLiteRuntime(
	fetchFn: FetchLike = fetch
): Promise<FinanceLiteRuntimeResult> {
	if (fetchFn === fetch) {
		financePromise ??= readFinanceLite(fetchFn);
		return financePromise;
	}
	return readFinanceLite(fetchFn);
}

async function readFinanceLite(fetchFn: FetchLike): Promise<FinanceLiteRuntimeResult> {
	const data = await readParquetRows<FinanceLiteRow>(FINANCE_LITE_PATH, {
		columns: [
			'stockCode',
			'bsns_year',
			'reprt_nm',
			'sj_div',
			'fs_nm',
			'account_id',
			'account_nm',
			'thstrm_amount',
			'thstrm_add_amount'
		],
		filter: { reprt_nm: { $eq: '4분기' } },
		fetchFn
	});
	return {
		rows: buildFinanceRows(data.rows),
		years: [...FINANCE_COMPLETED_YEARS],
		requests: data.requests,
		sourcePath: FINANCE_LITE_PATH
	};
}

export async function loadCompanyFinanceLitePeriods(
	stockCode: string,
	fetchFn: FetchLike = fetch,
	limit = 8
): Promise<CompanyFinancePeriodRow[]> {
	const code = stockCode.trim();
	if (!code) return [];
	if (fetchFn === fetch) {
		const key = `${code}:${limit}`;
		let promise = companyFinancePromises.get(key);
		if (!promise) {
			promise = readCompanyFinanceLitePeriods(code, fetchFn, limit);
			rememberCompanyFinancePromise(key, promise);
		}
		return promise;
	}
	return readCompanyFinanceLitePeriods(code, fetchFn, limit);
}

function rememberCompanyFinancePromise(key: string, promise: Promise<CompanyFinancePeriodRow[]>): void {
	if (companyFinancePromises.size >= MAX_COMPANY_FINANCE_CACHE) {
		const oldestKey = companyFinancePromises.keys().next().value;
		if (oldestKey) companyFinancePromises.delete(oldestKey);
	}
	companyFinancePromises.set(key, promise);
}

async function readCompanyFinanceLitePeriods(
	stockCode: string,
	fetchFn: FetchLike,
	limit: number
): Promise<CompanyFinancePeriodRow[]> {
	const data = await readParquetRows<FinanceLiteRow>(FINANCE_LITE_PATH, {
		columns: [
			'stockCode',
			'bsns_year',
			'reprt_nm',
			'sj_div',
			'fs_nm',
			'account_id',
			'account_nm',
			'thstrm_amount',
			'thstrm_add_amount'
		],
		filter: { stockCode: { $eq: stockCode } },
		fetchFn
	});
	return buildCompanyFinancePeriods(data.rows, limit);
}

type CompanyFinancePeriodWork = CompanyFinancePeriodRow & {
	cumulativeValues: Record<string, number>;
};

export function buildCompanyFinancePeriods(rows: FinanceLiteRow[], limit = 8): CompanyFinancePeriodRow[] {
	const byPeriod = new Map<string, CompanyFinancePeriodWork>();
	const seenPriority = new Map<string, number>();
	for (const row of rows) {
		const year = String(row.bsns_year ?? '');
		const quarter = quarterOf(row.reprt_nm);
		if (!year || quarter == null) continue;
		const account = matchAccount(row);
		if (!account) continue;
		const amount = numberOrNull(row.thstrm_amount);
		if (amount == null) continue;
		const cumulativeAmount = numberOrNull(row.thstrm_add_amount);
		const period = `${year}Q${quarter}`;
		const priority = rowPriority(account, row);
		const priorityKey = `${period}:${account.id}`;
		if ((seenPriority.get(priorityKey) ?? 0) >= priority) continue;
		seenPriority.set(priorityKey, priority);
		const out =
			byPeriod.get(period) ??
			({
				period,
				label: `${year.slice(2)}.${quarter}Q`,
				year,
				quarter,
				values: {},
				cumulativeValues: {}
			} satisfies CompanyFinancePeriodWork);
		out.values[account.id] = amount;
		if (cumulativeAmount != null) out.cumulativeValues[account.id] = cumulativeAmount;
		else if (quarter === 4 && account.statement !== 'BS') out.cumulativeValues[account.id] = amount;
		byPeriod.set(period, out);
	}
	for (const period of byPeriod.values()) {
		if (period.quarter !== 4) continue;
		const q3 = byPeriod.get(`${period.year}Q3`);
		if (!q3) continue;
		for (const account of FINANCE_ACCOUNTS) {
			if (account.statement === 'BS') continue;
			const fullYear = period.cumulativeValues[account.id];
			const throughQ3 = q3.cumulativeValues[account.id];
			if (typeof fullYear === 'number' && typeof throughQ3 === 'number') {
				period.values[account.id] = fullYear - throughQ3;
			}
		}
	}
	return Array.from(byPeriod.values())
		.sort((a, b) => Number(a.year) * 4 + a.quarter - (Number(b.year) * 4 + b.quarter))
		.slice(-limit)
		.map(({ period, label, year, quarter, values }) => ({ period, label, year, quarter, values }));
}

export function buildFinanceRows(rows: FinanceLiteRow[]): Array<Record<string, unknown> & { id: string }> {
	const byStock = new Map<string, Record<string, unknown> & { id: string }>();
	const seenPriority = new Map<string, number>();
	for (const row of rows) {
		if (String(row.reprt_nm ?? '') !== '4분기') continue;
		const year = String(row.bsns_year ?? '');
		if (!(FINANCE_COMPLETED_YEARS as readonly string[]).includes(year)) continue;
		const stockCode = String(row.stockCode ?? '').trim();
		if (!stockCode) continue;
		const account = matchAccount(row);
		if (!account) continue;
		const amount = numberOrNull(row.thstrm_amount);
		if (amount == null) continue;
		const metricKey = financeMetricKey(account.id, year);
		const priority = rowPriority(account, row);
		const priorityKey = `${stockCode}:${metricKey}`;
		if ((seenPriority.get(priorityKey) ?? 0) >= priority) continue;
		seenPriority.set(priorityKey, priority);
		const out = byStock.get(stockCode) ?? ({ id: stockCode } as Record<string, unknown> & { id: string });
		out[metricKey] = amount;
		byStock.set(stockCode, out);
	}
	for (const row of byStock.values()) addDerivedMetrics(row);
	return Array.from(byStock.values());
}

function matchAccount(row: FinanceLiteRow): FinanceAccountSpec | null {
	const accountId = String(row.account_id ?? '').trim();
	const nameMatches = ACCOUNT_BY_NAME.get(normalizeName(row.account_nm));
	const named = nameMatches?.find((account) => statementMatches(account, row)) ?? null;
	if (named) return named;
	const direct = ACCOUNT_BY_ID.get(accountId);
	if (direct && statementMatches(direct, row) && directAccountNameCompatible(direct, row)) return direct;
	return null;
}

function directAccountNameCompatible(account: FinanceAccountSpec, row: FinanceLiteRow): boolean {
	if (account.id !== 'net_income') return true;
	const name = normalizeName(row.account_nm);
	if (!name) return true;
	return name.includes('순이익') || name.includes('순손익') || name.includes('순손실');
}

function rowPriority(account: FinanceAccountSpec, row: FinanceLiteRow): number {
	const fsName = String(row.fs_nm ?? '');
	const sjDiv = String(row.sj_div ?? '').toUpperCase();
	const accountName = normalizeName(row.account_nm);
	let priority = fsName.includes('연결') ? 100 : 0;
	if (account.statement === 'IS') priority += sjDiv === 'IS' ? 20 : sjDiv === 'CIS' ? 10 : 0;
	else priority += sjDiv === account.statement ? 20 : 0;
	if (account.id === 'net_income') {
		if (accountName.includes('지배') || accountName.includes('비지배') || accountName.includes('귀속')) priority -= 30;
		if (
			accountName.startsWith('당기순') ||
			accountName.startsWith('분기순') ||
			accountName.startsWith('반기순') ||
			accountName.startsWith('당분기순')
		) {
			priority += 5;
		}
	}
	return priority;
}

function statementMatches(account: FinanceAccountSpec, row: FinanceLiteRow): boolean {
	const sjDiv = String(row.sj_div ?? '').toUpperCase();
	if (account.statement === 'IS') return sjDiv === 'IS' || sjDiv === 'CIS';
	return sjDiv === account.statement;
}

function quarterOf(value: unknown): number | null {
	const text = String(value ?? '');
	const match = text.match(/^([1-4])분기$/);
	if (!match) return null;
	return Number(match[1]);
}

function addDerivedMetrics(row: Record<string, unknown>) {
	for (const year of FINANCE_COMPLETED_YEARS) {
		const sales = num(row[financeMetricKey('sales', year)]);
		const op = num(row[financeMetricKey('operating_profit', year)]);
		const net = num(row[financeMetricKey('net_income', year)]);
		const equity = num(row[financeMetricKey('total_stockholders_equity', year)]);
		const currentAssets = num(row[financeMetricKey('current_assets', year)]);
		const currentLiabilities = num(row[financeMetricKey('current_liabilities', year)]);
		const noncurrentLiabilities = num(row[financeMetricKey('noncurrent_liabilities', year)]);
		const opexKey = financeMetricKey('operating_expenses', year);
		const opex = num(row[opexKey]);
		const gross = num(row[financeMetricKey('gross_profit', year)]);
		const derivedOpex = gross != null && op != null ? gross - op : null;
		if (opex == null && derivedOpex != null && derivedOpex >= 0) row[opexKey] = derivedOpex;

		row[financeRatioKey('op_margin', year)] = ratio(op, sales);
		row[financeRatioKey('net_margin', year)] = ratio(net, sales);
		row[financeRatioKey('roe', year)] = ratio(net, equity);
		row[financeRatioKey('debt_ratio', year)] = ratio(sum(currentLiabilities, noncurrentLiabilities), equity);
		row[financeRatioKey('current_ratio', year)] = ratio(currentAssets, currentLiabilities);
	}
	row[financeGrowthKey('sales_cagr')] = cagr(row, 'sales');
	row[financeGrowthKey('operating_profit_cagr')] = cagr(row, 'operating_profit');
	row[financeGrowthKey('net_income_cagr')] = cagr(row, 'net_income');
	row[financeGrowthKey('sales_yoy_latest')] = yoyLatest(row, 'sales');
	row[financeGrowthKey('operating_profit_yoy_latest')] = yoyLatest(row, 'operating_profit');
	row[financeGrowthKey('net_income_yoy_latest')] = yoyLatest(row, 'net_income');
}

function normalizeName(value: unknown): string {
	return String(value ?? '')
		.toLowerCase()
		.replace(/[\s()[\]{}·ㆍ,./\\_-]/g, '')
		.replace(/^[0-9ivxlcdmⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩⅰⅱⅲⅳⅴⅵⅶⅷⅸⅹ]+/i, '');
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

function num(value: unknown): number | null {
	return typeof value === 'number' && Number.isFinite(value) ? value : null;
}

function sum(a: number | null, b: number | null): number | null {
	if (a == null && b == null) return null;
	return (a ?? 0) + (b ?? 0);
}

function ratio(numerator: number | null, denominator: number | null): number | null {
	if (numerator == null || denominator == null || denominator === 0) return null;
	return (numerator / denominator) * 100;
}

function seriesValues(row: Record<string, unknown>, accountId: string): Array<number | null> {
	return FINANCE_COMPLETED_YEARS.map((year) => num(row[financeMetricKey(accountId, year)]));
}

function cagr(row: Record<string, unknown>, accountId: string): number | null {
	const values = seriesValues(row, accountId);
	const firstIdx = values.findIndex((v) => v != null && v > 0);
	let lastIdx = -1;
	for (let i = values.length - 1; i >= 0; i -= 1) {
		const v = values[i];
		if (v != null && v > 0) {
			lastIdx = i;
			break;
		}
	}
	if (firstIdx < 0 || lastIdx <= firstIdx) return null;
	const first = values[firstIdx] as number;
	const last = values[lastIdx] as number;
	const periods = lastIdx - firstIdx;
	return (Math.pow(last / first, 1 / periods) - 1) * 100;
}

function yoyLatest(row: Record<string, unknown>, accountId: string): number | null {
	const values = seriesValues(row, accountId);
	let lastIdx = -1;
	for (let i = values.length - 1; i >= 0; i -= 1) {
		if (values[i] != null) {
			lastIdx = i;
			break;
		}
	}
	if (lastIdx <= 0) return null;
	const curr = values[lastIdx];
	const prev = values[lastIdx - 1];
	if (curr == null || prev == null || prev === 0) return null;
	return (curr / prev - 1) * 100;
}
