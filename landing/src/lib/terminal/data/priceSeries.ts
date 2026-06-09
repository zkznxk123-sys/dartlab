// 일별 OHLCV 시계열 — krx/prices/raw-{year}.parquet 을 DuckDB-WASM 으로 브라우저 쿼리.
// 온디맨드(가격차트 마운트 시)·회사별 캐시. DuckDB-WASM 은 내부 Worker → 메인스레드 안 막음.
// iOS Safari / 실패 시 db=null → 호출측은 EOD 스냅샷만 표시 (graceful).
import { browser } from '$app/environment';
import { loadDartDb, type DartDb } from '$lib/data/duckdb';

export interface Candle {
	t: string; // YYYYMMDD
	o: number;
	h: number;
	l: number;
	c: number;
	v: number;
}

const cache = new Map<string, Candle[] | null>();
let viewReady: Promise<DartDb | null> | null = null;

// 현재+직전 연도 parquet 을 krxOhlc view 로 1회 등록 (1Y+ window).
async function ensureView(year: number): Promise<DartDb | null> {
	if (viewReady) return viewReady;
	viewReady = (async () => {
		const db = await loadDartDb();
		if (!db) return null; // iOS Safari 등 — 호출측 EOD fallback
		await db.registerHfParquet('krxOhlcCurr', `krx/prices/raw-${year}.parquet`);
		let hasPrev = false;
		try {
			await db.registerHfParquet('krxOhlcPrev', `krx/prices/raw-${year - 1}.parquet`);
			hasPrev = true;
		} catch {
			hasPrev = false;
		}
		const cols = 'ISU_CD, BAS_DD, TDD_OPNPRC, TDD_HGPRC, TDD_LWPRC, TDD_CLSPRC, ACC_TRDVOL';
		await db.query(
			hasPrev
				? `CREATE OR REPLACE VIEW krxOhlc AS SELECT ${cols} FROM krxOhlcCurr UNION ALL SELECT ${cols} FROM krxOhlcPrev`
				: `CREATE OR REPLACE VIEW krxOhlc AS SELECT ${cols} FROM krxOhlcCurr`
		);
		return db;
	})();
	return viewReady;
}

/** 회사 일별 OHLCV (오름차순). null = DuckDB 불가(iOS 등) → 호출측 EOD fallback. */
export async function loadDailyOHLCV(stockCode: string, year: number): Promise<Candle[] | null> {
	if (!browser) return null;
	const code = stockCode.trim();
	const c = code.replace(/[^0-9A-Za-z]/g, '');
	if (cache.has(code)) return cache.get(code) ?? null;
	const db = await ensureView(year);
	if (!db) {
		cache.set(code, null);
		return null;
	}
	try {
		const rows = await db.query<{
			t: string;
			o: number;
			h: number;
			l: number;
			c: number;
			v: number;
		}>(
			`SELECT CAST(BAS_DD AS VARCHAR) t,
				CAST(TDD_OPNPRC AS DOUBLE) o, CAST(TDD_HGPRC AS DOUBLE) h,
				CAST(TDD_LWPRC AS DOUBLE) l, CAST(TDD_CLSPRC AS DOUBLE) c,
				CAST(ACC_TRDVOL AS DOUBLE) v
			FROM krxOhlc
			WHERE ISU_CD = 'A${c}' OR ISU_CD = '${c}'
			ORDER BY BAS_DD`
		);
		const candles = rows.filter((r) => r.c != null && r.c > 0);
		cache.set(code, candles);
		return candles;
	} catch (e) {
		console.warn('[terminal/price] OHLCV query failed', code, e);
		cache.set(code, null);
		return null;
	}
}
