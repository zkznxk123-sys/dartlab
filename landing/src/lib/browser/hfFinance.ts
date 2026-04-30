import { browser } from '$app/environment';
import { loadDartDb, sqlEscape } from '$lib/data/duckdb';
import type { BrowserShowFreq, BrowserShowTopic, BrowserTable } from './types';

interface FinanceRow {
	period: string;
	accountKey: string;
	label: string;
	value: number | null;
	ord: number | null;
}

interface DuckColumnInfo {
	name?: string;
	column_name?: string;
}

const STATEMENT_BY_TOPIC: Partial<Record<BrowserShowTopic, string>> = {
	IS: 'IS',
	BS: 'BS',
	CF: 'CF'
};

export async function tryBuildLiveFinanceTable(
	stockCode: string,
	topic: BrowserShowTopic,
	freq: BrowserShowFreq
): Promise<BrowserTable | null> {
	const statement = STATEMENT_BY_TOPIC[topic];
	if (!browser || !statement) return null;

	try {
		const db = await loadDartDb();
		if (!db) return null;

		await db.registerHfParquet('companyFinance', `dart/finance/${stockCode}.parquet`);
		const schema = await db.query<DuckColumnInfo>("PRAGMA table_info('companyFinance')");
		const columns = new Set(
			schema.map((col) => String(col.name ?? col.column_name ?? '').toLowerCase()).filter(Boolean)
		);
		const rows = await db.query<FinanceRow>(liveFinanceSql(stockCode, statement, freq, columns));
		if (rows.length === 0) return null;

		return toTable(stockCode, topic, rows);
	} catch (err) {
		console.warn(`[dartlab-browser] finance parquet fallback: ${stockCode}/${topic}`, err);
		return null;
	}
}

function liveFinanceSql(
	stockCode: string,
	statement: string,
	freq: BrowserShowFreq,
	columns: Set<string>
): string {
	const reportCodes =
		freq === 'Y'
			? "'11011'"
			: statement === 'BS'
				? "'11013','11012','11014'"
				: "'11013','11012','11014'";
	const amountExpr = liveAmountExpr(statement, freq, columns);
	const periodExpr =
		freq === 'Y'
			? 'bsns_year'
			: `CONCAT(bsns_year, '-', CASE reprt_code
					WHEN '11013' THEN 'Q1'
					WHEN '11012' THEN 'Q2'
					WHEN '11014' THEN 'Q3'
					ELSE reprt_nm
				END)`;

	return `
		WITH filtered AS (
			SELECT
				${periodExpr} AS period,
				COALESCE(NULLIF(account_id, ''), account_nm) AS accountKey,
				account_nm AS label,
				${amountExpr} AS value,
				TRY_CAST(ord AS INTEGER) AS ord,
				ROW_NUMBER() OVER (
					PARTITION BY ${periodExpr}, COALESCE(NULLIF(account_id, ''), account_nm)
					ORDER BY
						CASE WHEN account_detail = '-' OR account_detail IS NULL THEN 0 ELSE 1 END,
						TRY_CAST(ord AS INTEGER) NULLS LAST
				) AS rn
			FROM companyFinance
			WHERE stock_code = '${sqlEscape(stockCode)}'
			  AND sj_div = '${sqlEscape(statement)}'
			  AND fs_div = 'CFS'
			  AND reprt_code IN (${reportCodes})
			  AND account_nm IS NOT NULL
			  AND ${amountExpr} IS NOT NULL
		),
		periods AS (
			SELECT DISTINCT period
			FROM filtered
			ORDER BY period DESC
			LIMIT ${freq === 'Y' ? 5 : 8}
		)
		SELECT f.period, f.accountKey, f.label, f.value, f.ord
		FROM filtered f
		JOIN periods p USING (period)
		WHERE f.rn = 1
		ORDER BY f.ord NULLS LAST, f.accountKey, f.period
	`;
}

function liveAmountExpr(statement: string, freq: BrowserShowFreq, columns: Set<string>): string {
	const cast = (column: string) => `TRY_CAST(REPLACE(${column}, ',', '') AS DOUBLE)`;
	if (freq === 'Y' || statement === 'BS') return cast('thstrm_amount');
	if (columns.has('thstrm_q_amount')) {
		return "TRY_CAST(REPLACE(COALESCE(thstrm_q_amount, thstrm_amount), ',', '') AS DOUBLE)";
	}
	if (columns.has('thstrm_amount')) return cast('thstrm_amount');
	if (columns.has('thstrm_add_amount')) return cast('thstrm_add_amount');
	return 'NULL';
}

function toTable(stockCode: string, topic: BrowserShowTopic, rows: FinanceRow[]): BrowserTable {
	const columns = Array.from(new Set(rows.map((r) => r.period))).sort();
	const byAccount = new Map<string, { label: string; ord: number; values: Map<string, number | null> }>();

	for (const row of rows) {
		const key = row.accountKey || row.label;
		let bucket = byAccount.get(key);
		if (!bucket) {
			bucket = {
				label: row.label || key,
				ord: row.ord ?? Number.MAX_SAFE_INTEGER,
				values: new Map()
			};
			byAccount.set(key, bucket);
		}
		bucket.ord = Math.min(bucket.ord, row.ord ?? Number.MAX_SAFE_INTEGER);
		bucket.values.set(row.period, row.value);
	}

	return {
		kind: 'table',
		topic,
		stockCode,
		unit: 'row-specific',
		columns,
		rows: Array.from(byAccount.entries())
			.sort((a, b) => a[1].ord - b[1].ord || a[1].label.localeCompare(b[1].label, 'ko-KR'))
			.slice(0, 80)
			.map(([key, row]) => ({
				key,
				label: row.label,
				unit: 'KRW',
				values: columns.map((col) => row.values.get(col) ?? null)
			})),
		source: `hf://dart/finance/${stockCode}.parquet`
	};
}
