// 매크로 경제지표 시계열 — macro/{fred,ecos}/observations.parquet (HF) hyparquet 직독.
// (seriesId, date, value) 가 seriesId+date 정렬이라 seriesId 필터로 row-group pruning.
// 차트 오버레이(ECON)·KPI 티커가 공유하는 단일 로더. 전체 파일 1.5MB 이하 — 시리즈당 첫 로드 수백 ms.
// 화이트리스트·출처표시 정본은 contracts (MACRO_SERIES·MACRO_ATTRIBUTION).
import { MACRO_SERIES, type MacroLatest, type MacroPoint, type MacroPort } from '@dartlab/ui-contracts';
import { readParquetRows } from '../../../data/hfRange';

const browser = typeof window !== 'undefined';

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

/**
 * IndexPort 전용 raw 채널 — fred seriesId 의 원시 (d,v) 점을 yoy 변환·MACRO_SERIES 화이트리스트 *없이* 반환.
 * loadSource('fred') srcCache 를 ECON 오버레이와 공유(파일 1 회 로드) — SP500 등 지수는 yoy 무의미라 raw.
 * 화이트리스트 게이팅은 호출측(fredIndexSource 의 US_INDEX_PRESETS)이 담당 — 임의 ID dump 아님.
 */
export async function loadFredSeriesPoints(seriesId: string): Promise<MacroPoint[] | null> {
	if (!browser) return null;
	const bySeries = await loadSource('fred');
	const pts = bySeries.get(seriesId);
	return pts && pts.length ? pts : null;
}

// 최근 1년(일별 252·월별 12) 구간을 최대 n 점으로 다운샘플 — 스파크라인 폴리라인용.
function sparkOf(pts: MacroPoint[], n = 40): number[] {
	const daily = pts.length > 400; // 일별 시리즈 추정
	const win = pts.slice(-(daily ? 252 : 12));
	if (win.length <= n) return win.map((p) => p.v);
	const out: number[] = [];
	for (let i = 0; i < n; i++) {
		const pt = win[Math.floor((i / (n - 1)) * (win.length - 1))];
		if (pt) out.push(pt.v);
	}
	return out;
}

/** KPI 티커용 — 화이트리스트 전 시리즈의 최신값+직전 대비 변화+스파크라인을 병렬 로드. */
export async function loadMacroLatest(): Promise<MacroLatest[]> {
	const all = await Promise.all(
		MACRO_SERIES.map(async (def) => {
			const pts = await loadMacroSeries(def.id);
			if (!pts || !pts.length) return null;
			const last = pts[pts.length - 1];
			if (!last) return null;
			const prev = pts.length > 1 ? pts[pts.length - 2] : null;
			return { def, v: last.v, d: last.d, chg: prev ? +(last.v - prev.v).toFixed(4) : null, spark: sparkOf(pts) };
		})
	);
	return all.filter((x): x is MacroLatest => x != null);
}

/** HF 공개 데이터 기반 MacroPort — 거시 시계열은 회사·앱 무관이라 local 셸도 본 포트를 명시적으로 재사용한다. */
export function createHfMacroPort(): MacroPort {
	return {
		async listSeries() {
			return MACRO_SERIES;
		},
		getSeries: loadMacroSeries,
		getLatest: loadMacroLatest
	};
}
