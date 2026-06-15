// 정량재무제표 IO — 공식 dart/finance/{code}.parquet 을 DuckDB-WASM(워커)으로 query → financePivot 로 pivot.
// 순수 SQL빌더·pivot·merge 는 financePivot.ts(테스트 가능). 본 모듈은 duckdb 등록+query 만.

import { buildSceMatrix, buildSql, num, pivot, sceComponent, type QueryRow, type SceQueryRow } from './financePivot';

// duckdb 접근은 셸이 주입한다 — surfaces(vanilla svelte)는 SvelteKit/Vite 전용 $lib/data/duckdb
// ($app/environment·@vite-ignore·OPFS)에 직접 결합하지 않는다. landing 컴포지션 루트가 provideDuckDb(loadDartDb)로
// 주입. 미주입(또는 기기 제약) = null → 정직 빈 재무(throw 금지, 02 §3 silent fallback 아님 — 단일 경로 + 명시 null).
export interface ViewerDuckDb {
	query<T = Record<string, unknown>>(sql: string): Promise<T[]>;
	registerHfParquet(viewName: string, hfPath: string): Promise<void>;
}
let duckDbProvider: (() => Promise<ViewerDuckDb | null>) | null = null;
export function provideDuckDb(provider: () => Promise<ViewerDuckDb | null>): void {
	duckDbProvider = provider;
}
function loadDartDb(): Promise<ViewerDuckDb | null> {
	return duckDbProvider ? duckDbProvider() : Promise.resolve(null);
}
// SQL 단일인용 escape — 1줄 순수 유틸(옛 $lib/data/duckdb.sqlEscape 인라인 — 결합 절제).
function sqlEscape(value: string): string {
	return value.replace(/'/g, "''");
}
import type { FinanceFreq, FinanceKind, FinanceScope, FinanceStatement, SceMatrixData } from './types';

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

export interface FinanceAvailability {
	scopes: FinanceScope[]; // 실제 보고된 범위(CFS/OFS) — 별도 없는 회사는 OFS 토글 숨김. CFS 우선 정렬 = 연결 우선 기본.
	byScope: Record<string, FinanceKind[]>; // scope → 가용 statement (단일 포괄손익 회사는 IS 없음)
}

// 회사의 (scope × statement) 가용 조합을 한 번에 probe — 빈 scope 토글·빈 statement 탭 제거. dart/finance 인코딩이
// 회사별로 다른 현실 반영(연결/별도 유무 + 별도 2표 vs 단일 포괄손익). scopes 는 CFS 우선 정렬이라 기본 = 연결 우선.
export async function financeAvailability(stockCode: string, market: 'KR' | 'US'): Promise<FinanceAvailability> {
	const fallback: FinanceAvailability = { scopes: ['CFS', 'OFS'], byScope: { CFS: ALL_KINDS, OFS: ALL_KINDS } };
	if (market !== 'KR') return { scopes: [], byScope: {} };
	return serialize(async () => {
		const db = await loadDartDb();
		if (!db) return fallback; // 기기 제약 — 일단 전부 노출
		await db.registerHfParquet('companyFinance', `dart/finance/${stockCode}.parquet`);
		const rows = await db.query<{ fs_div: string; sj_div: string }>(
			`SELECT DISTINCT fs_div, sj_div FROM companyFinance WHERE stock_code = '${sqlEscape(stockCode)}' AND fs_div IS NOT NULL AND sj_div IS NOT NULL`
		);
		const present: Record<string, Set<string>> = {};
		for (const r of rows) (present[r.fs_div] ??= new Set()).add(r.sj_div);
		const scopes = (['CFS', 'OFS'] as FinanceScope[]).filter((s) => present[s]?.size); // CFS 우선 정렬 유지
		const byScope: Record<string, FinanceKind[]> = {};
		for (const s of scopes) byScope[s] = ALL_KINDS.filter((k) => present[s].has(k));
		return scopes.length ? { scopes, byScope } : fallback;
	});
}

// 자본변동표(SCE) — 변동유형×자본구성요소 matrix (연간 11011). account×period 표가 아닌 전용.
export async function loadSceMatrix(stockCode: string, market: 'KR' | 'US', scope: FinanceScope): Promise<SceMatrixData | null> {
	if (market !== 'KR') return null;
	return serialize(async () => {
		const db = await loadDartDb();
		if (!db) return null;
		await db.registerHfParquet('companyFinance', `dart/finance/${stockCode}.parquet`);
		const raw = await db.query<{ period: string; label: string; detail: string | null; val: number | null; ord: number | null }>(
			`SELECT bsns_year AS period, account_nm AS label, CAST(account_detail AS VARCHAR) AS detail,
			        ${num('thstrm_amount')} AS val, TRY_CAST(ord AS INTEGER) AS ord
			 FROM companyFinance
			 WHERE stock_code = '${sqlEscape(stockCode)}' AND sj_div = 'SCE' AND fs_div = '${sqlEscape(scope)}'
			   AND reprt_code = '11011' AND account_nm IS NOT NULL`
		);
		if (raw.length === 0) return { scope, periods: [], components: [], byPeriod: {}, unit: 'KRW' };
		const rows: SceQueryRow[] = raw.map((r) => ({ period: r.period, label: r.label, comp: sceComponent(r.detail), val: r.val, ord: r.ord }));
		return buildSceMatrix(rows, scope);
	});
}

// DuckDB 로 dart/finance/{code}.parquet 등록 후 한 statement(연결/별도·freq) pivot. EDGAR(us)는 v1 미지원(null).
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
