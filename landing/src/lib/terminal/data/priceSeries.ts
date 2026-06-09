// 일별 OHLCV 시계열 — krx/prices/raw-{year}.parquet 을 hyparquet HTTP-range 로 직독.
// DuckDB-WASM 제거 (init 수초 + whole-file serial scan = 느림). hyparquet 는 컬럼 projection
// (7 컬럼) + ISU_CD 필터 pushdown + 병렬 range → 첫 페인트 비차단·sub-second. 회사별 캐시.
// 현재+직전 연도 병렬 로드 (1Y/MAX window). 실패 시 빈 배열 → 호출측 EOD snapshot fallback.
import { browser } from '$app/environment';
import { readParquetRows } from '$lib/data/hfRange';

export interface Candle {
	t: string; // YYYYMMDD
	o: number;
	h: number;
	l: number;
	c: number;
	v: number;
}

const OHLCV_COLUMNS = [
	'ISU_CD',
	'BAS_DD',
	'TDD_OPNPRC',
	'TDD_HGPRC',
	'TDD_LWPRC',
	'TDD_CLSPRC',
	'ACC_TRDVOL'
];

const cache = new Map<string, Candle[] | null>();

interface KrxRow extends Record<string, unknown> {
	ISU_CD?: string | null;
	BAS_DD?: string | number | null;
	TDD_OPNPRC?: string | number | null;
	TDD_HGPRC?: string | number | null;
	TDD_LWPRC?: string | number | null;
	TDD_CLSPRC?: string | number | null;
	ACC_TRDVOL?: string | number | null;
}

function num(v: unknown): number | null {
	if (typeof v === 'number') return Number.isFinite(v) ? v : null;
	if (typeof v === 'bigint') {
		const n = Number(v);
		return Number.isFinite(n) ? n : null;
	}
	if (typeof v === 'string' && v.trim()) {
		const n = Number(v.replace(/,/g, ''));
		return Number.isFinite(n) ? n : null;
	}
	return null;
}

function toCandle(r: KrxRow): Candle | null {
	const c = num(r.TDD_CLSPRC);
	if (c == null || c <= 0) return null;
	const t = r.BAS_DD == null ? '' : String(r.BAS_DD);
	if (!t) return null;
	return {
		t,
		o: num(r.TDD_OPNPRC) ?? c,
		h: num(r.TDD_HGPRC) ?? c,
		l: num(r.TDD_LWPRC) ?? c,
		c,
		v: num(r.ACC_TRDVOL) ?? 0
	};
}

// ISU_CD 는 KRX 주식 = 'A' + 6 자리 (예: A005930). 드물게 prefix 없는 경우 대비 $in.
async function readYearCandles(year: number, isuA: string, isuPlain: string): Promise<Candle[]> {
	const path = `krx/prices/raw-${year}.parquet`;
	try {
		const { rows } = await readParquetRows<KrxRow>(path, {
			columns: OHLCV_COLUMNS,
			filter: { ISU_CD: { $in: [isuA, isuPlain] } }
		});
		return rows.map(toCandle).filter((x): x is Candle => x != null);
	} catch {
		return [];
	}
}

/** 회사 일별 OHLCV (오름차순). 빈 배열 = 데이터 없음/실패 → 호출측 EOD fallback. */
export async function loadDailyOHLCV(stockCode: string, year: number): Promise<Candle[] | null> {
	if (!browser) return null;
	const code = stockCode.trim();
	if (cache.has(code)) return cache.get(code) ?? null;
	const c = code.replace(/[^0-9A-Za-z]/g, '');
	const isuA = `A${c}`;

	// 현재+직전 연도 병렬 — 1Y/MAX window 커버. 병렬 range → 직렬 DuckDB 대비 빠름.
	const [curr, prev] = await Promise.all([
		readYearCandles(year, isuA, c),
		readYearCandles(year - 1, isuA, c)
	]);
	const merged = [...prev, ...curr];
	if (merged.length === 0) {
		cache.set(code, null);
		return null;
	}
	// 날짜 오름차순 + 중복 일자 제거 (연도 경계 안전)
	merged.sort((a, b) => a.t.localeCompare(b.t));
	const out: Candle[] = [];
	let lastT = '';
	for (const k of merged) {
		if (k.t === lastT) continue;
		out.push(k);
		lastT = k.t;
	}
	cache.set(code, out);
	return out;
}
