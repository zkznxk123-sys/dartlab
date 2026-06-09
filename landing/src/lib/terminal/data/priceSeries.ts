// 일별 OHLCV 시계열 — krx/prices/raw-{year}.parquet 을 hyparquet HTTP-range 로 직독.
// hyparquet 는 컬럼 projection (7 컬럼) + ISU_CD 필터 pushdown + 병렬 range → 첫 페인트 비차단·sub-second.
// 전체 이력(2010~현재) lazy 로딩: 초기 = 현재+직전 연도, 이후 차트 좌측 팬 시 연도 단위 추가 로드.
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

// KRX raw 파케이 존재 하한 (HF 실측: raw-2010 ~ raw-2026). 이 아래는 404 → lazy 로드 종료.
export const KRX_MIN_YEAR = 2010;

interface CompanyPrices {
	candles: Candle[]; // 오름차순·일자 dedup
	oldestYear: number; // 현재까지 로드한 가장 오래된 연도
}

const OHLCV_COLUMNS = ['ISU_CD', 'BAS_DD', 'TDD_OPNPRC', 'TDD_HGPRC', 'TDD_LWPRC', 'TDD_CLSPRC', 'ACC_TRDVOL'];

const cache = new Map<string, CompanyPrices | null>();

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
	return { t, o: num(r.TDD_OPNPRC) ?? c, h: num(r.TDD_HGPRC) ?? c, l: num(r.TDD_LWPRC) ?? c, c, v: num(r.ACC_TRDVOL) ?? 0 };
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

// 오름차순 병합 + 일자 dedup (연도 경계 안전).
function mergeDedup(...lists: Candle[][]): Candle[] {
	const merged = ([] as Candle[]).concat(...lists);
	merged.sort((a, b) => a.t.localeCompare(b.t));
	const out: Candle[] = [];
	let lastT = '';
	for (const k of merged) {
		if (k.t === lastT) continue;
		out.push(k);
		lastT = k.t;
	}
	return out;
}

/** 초기 로드 — 현재+직전 연도 (빠른 첫 페인트). null = 데이터 없음/실패. */
export async function loadInitialOHLCV(stockCode: string, year: number): Promise<CompanyPrices | null> {
	if (!browser) return null;
	const code = stockCode.trim();
	if (cache.has(code)) return cache.get(code) ?? null;
	const c = code.replace(/[^0-9A-Za-z]/g, '');
	const isuA = `A${c}`;
	const [curr, prev] = await Promise.all([readYearCandles(year, isuA, c), readYearCandles(year - 1, isuA, c)]);
	const candles = mergeDedup(prev, curr);
	if (candles.length === 0) {
		cache.set(code, null);
		return null;
	}
	const rec: CompanyPrices = { candles, oldestYear: year - 1 };
	cache.set(code, rec);
	return rec;
}

/** 좌측 팬 시 더 오래된 연도 1 개 로드 (prepend 용). 캐시에도 병합. 빈 배열 = 데이터 없음. */
export async function loadOlderYear(stockCode: string, targetYear: number): Promise<Candle[]> {
	if (!browser || targetYear < KRX_MIN_YEAR) return [];
	const code = stockCode.trim();
	const c = code.replace(/[^0-9A-Za-z]/g, '');
	const rows = await readYearCandles(targetYear, `A${c}`, c);
	const rec = cache.get(code);
	if (rec) {
		rec.candles = mergeDedup(rows, rec.candles);
		rec.oldestYear = Math.min(rec.oldestYear, targetYear);
	}
	return rows;
}
