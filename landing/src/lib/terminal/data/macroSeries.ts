// 매크로 경제지표 시계열 — macro/{fred,ecos}/observations.parquet (HF) hyparquet 직독.
// (seriesId, date, value) 가 seriesId+date 정렬이라 seriesId 필터로 row-group pruning.
// 차트 오버레이(PriceChart ECON)·KPI 티커가 공유하는 단일 로더. 전체 파일 1.5MB 이하 — 시리즈당 첫 로드 수백 ms.
import { browser } from '$app/environment';
import { readParquetRows } from '$lib/data/hfRange';

export interface MacroPoint {
	d: string; // YYYYMMDD
	v: number;
}

export interface MacroSeriesDef {
	id: string;
	src: 'fred' | 'ecos';
	kr: string;
	en: string;
	unit: string; // 표시 단위 ('원' | '%' | '%p' | 'yoy%' | '$/t' | 'pt')
	yoy?: boolean; // true = 12개월 전 대비 % 로 변환해 표시 (지수형 월간 시리즈)
	digits?: number; // 최신값 표시 소수 자리
}

// 화이트리스트 — 주가와 비교 가치가 큰 핵심 지표만 (덕지덕지 방지).
export const MACRO_SERIES: MacroSeriesDef[] = [
	{ id: 'USDKRW', src: 'ecos', kr: '원/달러', en: 'USD/KRW', unit: '원', digits: 0 },
	{ id: 'BASE_RATE', src: 'ecos', kr: '한은 기준금리', en: 'BOK rate', unit: '%', digits: 2 },
	{ id: 'CPI', src: 'ecos', kr: '소비자물가 YoY', en: 'KR CPI YoY', unit: '%', yoy: true, digits: 1 },
	{ id: 'EXPORT', src: 'ecos', kr: '수출 YoY', en: 'Exports YoY', unit: '%', yoy: true, digits: 1 },
	{ id: 'CLI', src: 'ecos', kr: '경기선행지수', en: 'KR CLI', unit: 'pt', digits: 1 },
	{ id: 'DGS10', src: 'fred', kr: '미국 10Y 금리', en: 'US 10Y', unit: '%', digits: 2 },
	{ id: 'FEDFUNDS', src: 'fred', kr: '연준 기준금리', en: 'Fed funds', unit: '%', digits: 2 },
	{ id: 'T10Y2Y', src: 'fred', kr: '미 장단기차(10Y-2Y)', en: 'US 10Y-2Y', unit: '%p', digits: 2 },
	{ id: 'CPIAUCSL', src: 'fred', kr: '미 CPI YoY', en: 'US CPI YoY', unit: '%', yoy: true, digits: 1 },
	{ id: 'PCOPPUSDM', src: 'fred', kr: '구리 가격', en: 'Copper', unit: '$/t', digits: 0 }
];

export const MACRO_ATTRIBUTION = '출처: 한국은행 ECOS · FRED (St. Louis Fed)';

const defById = new Map(MACRO_SERIES.map((s) => [s.id, s]));
// 소스 파일(166KB·1.4MB)이 작아 통째 1 회 로드 → seriesId 그룹화가 시리즈별 range-read 10회보다 빠르고 단순.
const srcCache = new Map<string, Promise<Map<string, MacroPoint[]>>>();

interface ObsRow extends Record<string, unknown> {
	seriesId?: string | null;
	date?: Date | string | null;
	value?: number | null;
}

function toYmd(d: Date | string | null | undefined): string {
	if (d == null) return '';
	if (d instanceof Date) {
		const y = d.getUTCFullYear();
		const m = String(d.getUTCMonth() + 1).padStart(2, '0');
		const dd = String(d.getUTCDate()).padStart(2, '0');
		return `${y}${m}${dd}`;
	}
	return String(d).replace(/-/g, '').slice(0, 8);
}

function loadSource(src: 'fred' | 'ecos'): Promise<Map<string, MacroPoint[]>> {
	const hit = srcCache.get(src);
	if (hit) return hit;
	const p = (async () => {
		const bySeries = new Map<string, MacroPoint[]>();
		try {
			const { rows } = await readParquetRows<ObsRow>(`macro/${src}/observations.parquet`, {
				columns: ['seriesId', 'date', 'value']
			});
			for (const r of rows) {
				const id = r.seriesId == null ? '' : String(r.seriesId);
				const d = toYmd(r.date);
				const v = Number(r.value);
				if (!id || d.length !== 8 || !Number.isFinite(v)) continue;
				let arr = bySeries.get(id);
				if (!arr) bySeries.set(id, (arr = []));
				arr.push({ d, v });
			}
			for (const arr of bySeries.values()) arr.sort((a, b) => a.d.localeCompare(b.d));
		} catch {
			/* 빈 맵 — 호출측 null 처리 */
		}
		return bySeries;
	})();
	srcCache.set(src, p);
	return p;
}

// 지수형 월간 시리즈 → 12개월 전 대비 YoY %. 월 단위 키(YYYYMM) 매칭.
function toYoy(points: MacroPoint[]): MacroPoint[] {
	const byMonth = new Map(points.map((p) => [p.d.slice(0, 6), p.v]));
	const out: MacroPoint[] = [];
	for (const p of points) {
		const ym = p.d.slice(0, 6);
		const prevY = String(+ym.slice(0, 4) - 1) + ym.slice(4, 6);
		const base = byMonth.get(prevY);
		if (base != null && base !== 0) out.push({ d: p.d, v: +(((p.v - base) / Math.abs(base)) * 100).toFixed(2) });
	}
	return out;
}

/** 시리즈 전체 이력 (오름차순, yoy 정의 시 변환 적용). null = 미존재/실패. 소스 파일 1 회 로드 공유. */
export async function loadMacroSeries(id: string): Promise<MacroPoint[] | null> {
	if (!browser) return null;
	const def = defById.get(id);
	if (!def) return null;
	const bySeries = await loadSource(def.src);
	let pts = bySeries.get(id) ?? [];
	if (def.yoy) pts = toYoy(pts);
	return pts.length ? pts : null;
}

export interface MacroLatest {
	def: MacroSeriesDef;
	v: number;
	d: string; // YYYYMMDD
	chg: number | null; // 직전 관측 대비 변화 (단위 동일)
}

/** KPI 티커용 — 화이트리스트 전 시리즈의 최신값+직전 대비 변화를 병렬 로드. */
export async function loadMacroLatest(): Promise<MacroLatest[]> {
	const all = await Promise.all(
		MACRO_SERIES.map(async (def) => {
			const pts = await loadMacroSeries(def.id);
			if (!pts || !pts.length) return null;
			const last = pts[pts.length - 1];
			const prev = pts.length > 1 ? pts[pts.length - 2] : null;
			return { def, v: last.v, d: last.d, chg: prev ? +(last.v - prev.v).toFixed(4) : null };
		})
	);
	return all.filter((x): x is MacroLatest => x != null);
}
