// 정량재무제표 IO — 공식 dart/finance/{code}.parquet 을 DuckDB-WASM(워커)으로 query → financePivot 로 pivot.
// 순수 SQL빌더·pivot·merge 는 financePivot.ts(테스트 가능). 본 모듈은 duckdb 등록+query 만.

import { loadDartDb, sqlEscape } from '$lib/data/duckdb';
import { buildSql, pivot, type QueryRow } from './financePivot';
import type { FinanceFreq, FinanceKind, FinanceScope, FinanceStatement } from './types';

const ALL_KINDS: FinanceKind[] = ['IS', 'BS', 'CF', 'CIS', 'SCE'];

// DuckDB-WASM 단일 연결은 동시 query 시 hang — finance 의 모든 DuckDB 접근(probe + 각 statement load)을
// 직렬화. 한 호출이 끝나야 다음이 _conn 을 쓴다(register+query 쌍이 안 겹침).
let dbQueue: Promise<unknown> = Promise.resolve();
function serialize<T>(fn: () => Promise<T>): Promise<T> {
	const run = dbQueue.then(fn, fn);
	dbQueue = run.then(
		() => undefined,
		() => undefined
	);
	return run;
}

// 회사·scope 에 실제 존재하는 statement(sj_div) 집합 — 단일 포괄손익(one-statement) 회사는 IS 가 비어 IS 탭을
// 숨기고 CIS 만 노출(빈 탭 제거). dart/finance 인코딩이 회사별로 다른 현실 반영(별도 2표 vs 단일 1표).
export async function availableStatements(stockCode: string, market: 'KR' | 'US', scope: FinanceScope): Promise<FinanceKind[]> {
	if (market !== 'KR') return [];
	return serialize(async () => {
		const db = await loadDartDb();
		if (!db) return ALL_KINDS; // 기기 제약 — 일단 전부 노출(호출 시 빈 표 안내)
		await db.registerHfParquet('companyFinance', `dart/finance/${stockCode}.parquet`);
		const rows = await db.query<{ sj_div: string }>(
			`SELECT DISTINCT sj_div FROM companyFinance WHERE stock_code = '${sqlEscape(stockCode)}' AND fs_div = '${sqlEscape(scope)}' AND sj_div IS NOT NULL`
		);
		const present = new Set(rows.map((r) => r.sj_div));
		return ALL_KINDS.filter((k) => present.has(k));
	});
}

// DuckDB 로 dart/finance/{code}.parquet 등록 후 한 statement(연결/개별·freq) pivot. EDGAR(us)는 v1 미지원(null).
export async function loadFinanceStatement(
	stockCode: string,
	market: 'KR' | 'US',
	kind: FinanceKind,
	freq: FinanceFreq,
	scope: FinanceScope
): Promise<FinanceStatement | null> {
	if (market !== 'KR') return null; // EDGAR companyfacts → statement 매핑은 후속(별도 스키마)
	return serialize(async () => {
		const db = await loadDartDb();
		if (!db) return null; // iOS Safari 등 — 호출측이 안내
		await db.registerHfParquet('companyFinance', `dart/finance/${stockCode}.parquet`);
		const rows = await db.query<QueryRow>(buildSql(stockCode, kind, freq, scope));
		if (rows.length === 0) return { kind, scope, freq, periods: [], rows: [], unit: 'KRW' };
		return pivot(rows, kind, scope, freq);
	});
}
