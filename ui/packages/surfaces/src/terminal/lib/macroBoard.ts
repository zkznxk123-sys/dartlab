// 매크로 상황판 — 결정론 계산 SSOT (순수 함수·svelte 무관). 변환 렌즈·역사 위치·국면 모멘텀 궤적·
// 카테고리 매핑·NBER 침체구간. UI(MacroSeriesChart·MacroBoard·MacroGridTrail)가 소비.
//
// ⛔ 무판정: 여기엔 "호재/악재/비중확대" 판정 0. 데이터 변환·위치 계산만. 색·라벨은 컴포넌트가 중립으로.
// ⛔ 정직: YoY 는 level 시리즈에만 의미(이미 yoy 인 시리즈는 identity). 침체음영은 US NBER 정적 구간만.

import type { MacroPoint, MacroSeriesDef } from '@dartlab/ui-contracts';

export type MacroTransform = 'level' | 'yoy' | 'z';

const DAY = 86_400_000;

/** YYYYMMDD → epoch ms (UTC). 입력은 항상 8자리 숫자열. */
export function ymdToMs(d: string): number {
	const y = Number(d.slice(0, 4));
	const m = Number(d.slice(4, 6));
	const day = Number(d.slice(6, 8));
	return Date.UTC(y, m - 1, day);
}

/** 마지막 관측 기준 최근 `years` 년 윈도로 자른다(years<=0 이면 전체). */
export function windowSlice(points: MacroPoint[], years: number): MacroPoint[] {
	if (!points.length || years <= 0) return points;
	const last = ymdToMs(points[points.length - 1].d);
	const cutoff = last - years * 365.25 * DAY;
	return points.filter((p) => ymdToMs(p.d) >= cutoff);
}

/** 전년비 % 변화 — 각 점에서 ~365일 이전 최근 관측 대비 (v/vPrev-1)*100.
 *  level 시리즈(금리·지수·환율·원자재·가격)에만 의미. 이미 yoy 인 시리즈엔 호출 금지(컴포넌트가 def.yoy 로 가드). */
export function toYoY(points: MacroPoint[]): MacroPoint[] {
	const out: MacroPoint[] = [];
	let j = 0;
	for (let i = 0; i < points.length; i++) {
		const t = ymdToMs(points[i].d);
		const target = t - 365 * DAY;
		// j 를 target 이하 최신 관측까지 전진(단조 — 두 포인터).
		while (j + 1 < points.length && ymdToMs(points[j + 1].d) <= target) j++;
		const prev = points[j];
		if (prev && ymdToMs(prev.d) <= target && prev.v !== 0) {
			out.push({ d: points[i].d, v: (points[i].v / prev.v - 1) * 100 });
		}
	}
	return out;
}

/** z-score — 주어진 점들의 평균·표준편차로 표준화. 표본<2 또는 std=0 이면 [](미정의 안전). */
export function toZScore(points: MacroPoint[]): MacroPoint[] {
	if (points.length < 2) return [];
	const vals = points.map((p) => p.v);
	const mean = vals.reduce((a, b) => a + b, 0) / vals.length;
	const variance = vals.reduce((a, b) => a + (b - mean) ** 2, 0) / vals.length;
	const std = Math.sqrt(variance);
	if (std === 0) return [];
	return points.map((p) => ({ d: p.d, v: (p.v - mean) / std }));
}

/** 변환 렌즈 적용 — level/yoy/z. def.yoy(이미 전년비) 시리즈는 'yoy' 요청해도 level(identity).
 *  z 는 윈도 내 표준화(현재가 역사 대비 몇 σ). 항상 윈도 슬라이스 후 반환. */
export function applyTransform(points: MacroPoint[], transform: MacroTransform, def: MacroSeriesDef, years: number): MacroPoint[] {
	if (!points.length) return [];
	if (transform === 'yoy' && !def.yoy) return windowSlice(toYoY(points), years);
	if (transform === 'z') return toZScore(windowSlice(points, years));
	return windowSlice(points, years); // level (또는 이미-yoy 시리즈의 yoy 요청)
}

/** 시리즈 전체 최저·최고 (역사 범위 — "역사 최저↔최고" 막대용). */
export function historyExtent(points: MacroPoint[]): { min: number; max: number } | null {
	if (!points.length) return null;
	let min = points[0].v;
	let max = points[0].v;
	for (const p of points) {
		if (p.v < min) min = p.v;
		if (p.v > max) max = p.v;
	}
	return { min, max };
}

/** 현재값의 역사 범위 내 위치 0..1 (min=0, max=1). 범위 0 이면 0.5. */
export function currentPosition(points: MacroPoint[]): number | null {
	const ext = historyExtent(points);
	if (!ext) return null;
	const cur = points[points.length - 1].v;
	const span = ext.max - ext.min;
	return span === 0 ? 0.5 : (cur - ext.min) / span;
}

/** 방향(가속/감속) — 최신값 vs lookbackMonths 이전값 부호. breadth 집계용. 표본 부족=flat.
 *  yoy 시리즈는 값=rate 라 상승=가속, level 시리즈는 상승=오름. 무판정(사실: 오르나/내리나). */
export function momentumSign(points: MacroPoint[], lookbackMonths = 3): 'up' | 'down' | 'flat' {
	if (points.length < 2) return 'flat';
	const last = points[points.length - 1];
	const target = ymdToMs(last.d) - lookbackMonths * 30.44 * DAY;
	let prior = points[0];
	for (const p of points) {
		if (ymdToMs(p.d) <= target) prior = p;
		else break;
	}
	const diff = last.v - prior.v;
	if (Math.abs(diff) < 1e-9) return 'flat';
	return diff > 0 ? 'up' : 'down';
}

/** 축 방향집계 — 시리즈 묶음의 up/down/flat 개수(breadth). "물가 6개 중 6개 가속" 한 줄용. */
export function directionBreadth(seriesList: MacroPoint[][], lookbackMonths = 3): { up: number; down: number; flat: number; total: number } {
	let up = 0, down = 0, flat = 0;
	for (const pts of seriesList) {
		const s = momentumSign(pts, lookbackMonths);
		if (s === 'up') up++;
		else if (s === 'down') down++;
		else flat++;
	}
	return { up, down, flat, total: seriesList.length };
}

/** 현재 z-격차 — 두 시리즈를 각각 표준화한 *최신* z 차이(A−B). 발산 쌍의 "지금 얼마나 벌어졌나"(절대 임계 아님·롤링상관 베이스라인 아님).
 *  표본 부족 시 null. 부호=A가 자기 역사 대비 B보다 위/아래. */
export function zGap(a: MacroPoint[], b: MacroPoint[]): number | null {
	const za = toZScore(a);
	const zb = toZScore(b);
	if (!za.length || !zb.length) return null;
	return za[za.length - 1].v - zb[zb.length - 1].v;
}

export interface MomentumPoint {
	ym: string; // YYYYMM
	g: number; // 성장 z (세로축 — 높을수록 위)
	i: number; // 물가 z (가로축 — 높을수록 오른쪽)
}

/** 국면 모멘텀 궤적 — 성장률·물가율 시리즈를 각각 z-표준화해 최근 n개월 (성장 z, 물가 z) 경로.
 *  입력은 *이미 rate 형태*(성장=CLI YoY 등, 물가=CPI YoY). 월(YYYYMM) 교집합으로 정렬·결합.
 *  표본 부족(공통<3) 이면 []. Hedgeye/42Macro GRID 의 모멘텀 좌표를 우리 데이터로 — 추천 0·궤적만. */
export function growthInflationMomentum(growthRate: MacroPoint[], inflRate: MacroPoint[], n = 12): MomentumPoint[] {
	const gz = toZScore(growthRate);
	const iz = toZScore(inflRate);
	if (gz.length < 3 || iz.length < 3) return [];
	const iByYm = new Map<string, number>();
	for (const p of iz) iByYm.set(p.d.slice(0, 6), p.v);
	const merged: MomentumPoint[] = [];
	for (const p of gz) {
		const ym = p.d.slice(0, 6);
		const iv = iByYm.get(ym);
		if (iv !== undefined) merged.push({ ym, g: p.v, i: iv });
	}
	return merged.slice(-n);
}

/** 성장 z·물가 z → GIP 사분면 키. 성장↑물가↑=reflation, 성장↑물가↓=goldilocks, 성장↓물가↑=stagflation, 성장↓물가↓=deflation. */
export function quadOf(g: number, i: number): 'goldilocks' | 'reflation' | 'stagflation' | 'deflation' {
	if (g >= 0) return i >= 0 ? 'reflation' : 'goldilocks';
	return i >= 0 ? 'stagflation' : 'deflation';
}

/** US NBER 침체 구간 (정적 사실·YYYYMMDD [start,end]). KR 은 공식 monthly dating 부재 → 음영 생략. */
export const NBER_RECESSIONS: [string, string][] = [
	['19900701', '19910301'],
	['20010301', '20011101'],
	['20071201', '20090601'],
	['20200201', '20200401']
];

export type BoardCategory = '성장·경기' | '물가' | '금리·통화' | '신용·곡선' | '시장·원자재' | '부동산';

export const BOARD_CATEGORIES: { key: BoardCategory; en: string }[] = [
	{ key: '성장·경기', en: 'Growth' },
	{ key: '물가', en: 'Inflation' },
	{ key: '금리·통화', en: 'Rates' },
	{ key: '신용·곡선', en: 'Credit & Curve' },
	{ key: '시장·원자재', en: 'Markets' },
	{ key: '부동산', en: 'Housing' }
];

const GROUP_TO_CATEGORY: Record<string, BoardCategory> = {
	'경기·심리': '성장·경기', '한국생산': '성장·경기', '수출': '성장·경기', '미국고용·생산': '성장·경기',
	'한국물가': '물가', '미국물가': '물가', '생산자물가': '물가',
	'한국금리': '금리·통화', '미국금리': '금리·통화', '통화': '금리·통화',
	'미국신용': '신용·곡선',
	'미국증시': '시장·원자재', '환율': '시장·원자재', '원자재': '시장·원자재',
	'부동산': '부동산'
};

/** 시리즈 → 보드 카테고리. 곡선 스프레드(장단기차)는 group='미국금리' 이지만 신용·곡선으로 특례. */
export function categoryOf(def: MacroSeriesDef): BoardCategory {
	if (def.id === 'T10Y2Y' || def.id === 'T10Y3M') return '신용·곡선';
	return GROUP_TO_CATEGORY[def.group ?? ''] ?? '시장·원자재';
}

/** 국가 필터 — KR=ecos, US=fred(미국·글로벌), both=전체. */
export function matchesCountry(def: MacroSeriesDef, country: 'KR' | 'US' | 'both'): boolean {
	if (country === 'both') return true;
	return country === 'KR' ? def.src === 'ecos' : def.src === 'fred';
}
