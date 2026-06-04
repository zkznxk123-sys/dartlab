// 정량재무제표 IO — 공식 dart/finance/{code}.parquet 을 DuckDB-WASM(워커)으로 query → financePivot 로 pivot.
// 순수 SQL빌더·pivot·merge 는 financePivot.ts(테스트 가능). 본 모듈은 duckdb 등록+query 만.

import { loadDartDb } from '$lib/data/duckdb';
import { buildSql, pivot, type QueryRow } from './financePivot';
import type { FinanceFreq, FinanceKind, FinanceScope, FinanceStatement } from './types';

// DuckDB 로 dart/finance/{code}.parquet 등록 후 한 statement(연결/개별·freq) pivot. EDGAR(us)는 v1 미지원(null).
export async function loadFinanceStatement(
	stockCode: string,
	market: 'KR' | 'US',
	kind: FinanceKind,
	freq: FinanceFreq,
	scope: FinanceScope
): Promise<FinanceStatement | null> {
	if (market !== 'KR') return null; // EDGAR companyfacts → statement 매핑은 후속(별도 스키마)
	const db = await loadDartDb();
	if (!db) return null; // iOS Safari 등 — 호출측이 안내
	await db.registerHfParquet('companyFinance', `dart/finance/${stockCode}.parquet`);
	const rows = await db.query<QueryRow>(buildSql(stockCode, kind, freq, scope));
	if (rows.length === 0) return { kind, scope, freq, periods: [], rows: [], unit: 'KRW' };
	return pivot(rows, kind, scope, freq);
}
