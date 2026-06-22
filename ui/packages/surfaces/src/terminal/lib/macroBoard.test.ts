import { describe, it, expect } from 'vitest';
import type { MacroPoint, MacroSeriesDef } from '@dartlab/ui-contracts';
import {
	ymdToMs, windowSlice, toYoY, toZScore, applyTransform, historyExtent, currentPosition,
	growthInflationMomentum, quadOf, categoryOf, matchesCountry, NBER_RECESSIONS, BOARD_CATEGORIES,
	momentumSign, directionBreadth
} from './macroBoard';

const def = (over: Partial<MacroSeriesDef> = {}): MacroSeriesDef => ({ id: 'X', src: 'fred', kr: 'x', en: 'x', unit: '%', ...over });
// 월별 시리즈 헬퍼 — YYYYMM 01일.
const monthly = (vals: number[], startYm = 202301): MacroPoint[] =>
	vals.map((v, k) => {
		const y = Math.floor(startYm / 100) + Math.floor((((startYm % 100) - 1) + k) / 12);
		const m = (((startYm % 100) - 1 + k) % 12) + 1;
		return { d: `${y}${String(m).padStart(2, '0')}01`, v };
	});

describe('macroBoard — 변환·위치 (결정론)', () => {
	it('ymdToMs parses YYYYMMDD as UTC', () => {
		expect(ymdToMs('20260101')).toBe(Date.UTC(2026, 0, 1));
		expect(ymdToMs('20260622')).toBe(Date.UTC(2026, 5, 22));
	});

	it('windowSlice keeps last N years from the last observation', () => {
		const pts = monthly(Array.from({ length: 36 }, (_, k) => k), 202301); // 36개월(2023-01~2025-12)
		const last1y = windowSlice(pts, 1);
		// 마지막=2025-12. 1년 윈도 → 약 12~13개월.
		expect(last1y.length).toBeGreaterThanOrEqual(12);
		expect(last1y.length).toBeLessThanOrEqual(13);
		expect(last1y[last1y.length - 1].d).toBe('20251201');
		// years<=0 → 전체.
		expect(windowSlice(pts, 0).length).toBe(36);
	});

	it('toYoY computes 12-month percent change', () => {
		// 24개월, 매월 +1 시작 100 → 1년 뒤 112 vs 100 = +12%.
		const pts = monthly(Array.from({ length: 24 }, (_, k) => 100 + k), 202301);
		const yoy = toYoY(pts);
		expect(yoy.length).toBeGreaterThan(0);
		// 2024-01(=112) vs 2023-01(=100) → 12%.
		const jan24 = yoy.find((p) => p.d === '20240101')!;
		expect(jan24.v).toBeCloseTo(12, 5);
		// 첫 12개월은 비교 대상 없어 제외.
		expect(yoy.find((p) => p.d === '20230601')).toBeUndefined();
	});

	it('toZScore standardizes to mean 0 (std-normalized); degenerate → []', () => {
		const pts = monthly([1, 2, 3, 4, 5]);
		const z = toZScore(pts);
		const mean = z.reduce((a, b) => a + b.v, 0) / z.length;
		expect(mean).toBeCloseTo(0, 9);
		// 중앙값(3) → z 0.
		expect(z[2].v).toBeCloseTo(0, 9);
		// 상수 시리즈(std 0) → [].
		expect(toZScore(monthly([5, 5, 5]))).toEqual([]);
		expect(toZScore(monthly([5]))).toEqual([]);
	});

	it('applyTransform: yoy on an already-yoy series is identity(level), not double-transformed', () => {
		const yoySeries = monthly([3.1, 3.0, 2.9, 3.2], 202401);
		const out = applyTransform(yoySeries, 'yoy', def({ yoy: true }), 0);
		// def.yoy=true → level 그대로(이중변환 금지).
		expect(out.map((p) => p.v)).toEqual([3.1, 3.0, 2.9, 3.2]);
	});

	it('applyTransform: yoy on a level series transforms; z standardizes', () => {
		const level = monthly(Array.from({ length: 24 }, (_, k) => 100 + k), 202301);
		const yoy = applyTransform(level, 'yoy', def(), 0);
		expect(yoy.find((p) => p.d === '20240101')!.v).toBeCloseTo(12, 5);
		const z = applyTransform(level, 'z', def(), 0);
		expect(z.reduce((a, b) => a + b.v, 0) / z.length).toBeCloseTo(0, 9);
	});

	it('historyExtent + currentPosition place the latest value in the historical range', () => {
		const pts = monthly([10, 30, 20, 50, 40]); // min 10, max 50, last 40
		expect(historyExtent(pts)).toEqual({ min: 10, max: 50 });
		expect(currentPosition(pts)).toBeCloseTo((40 - 10) / (50 - 10), 9); // 0.75
		expect(currentPosition([])).toBeNull();
		expect(currentPosition(monthly([7, 7, 7]))).toBe(0.5); // 범위 0 → 중앙
	});
});

describe('macroBoard — 방향 집계(breadth)', () => {
	it('momentumSign: 최신값이 ~3개월 전보다 높으면 up, 낮으면 down, 표본부족 flat', () => {
		expect(momentumSign(monthly([1, 2, 3, 4, 5, 6]))).toBe('up'); // 최신 6 > 3개월전 3
		expect(momentumSign(monthly([6, 5, 4, 3, 2, 1]))).toBe('down');
		expect(momentumSign(monthly([5, 5, 5, 5, 5, 5]))).toBe('flat'); // 변화 0
		expect(momentumSign([{ d: '20260101', v: 1 }])).toBe('flat'); // 1점
		expect(momentumSign([])).toBe('flat');
	});
	it('directionBreadth: 묶음의 가속/감속/횡보 개수 집계', () => {
		const up = monthly([1, 2, 3, 4, 5, 6]);
		const down = monthly([6, 5, 4, 3, 2, 1]);
		const flat = monthly([5, 5, 5, 5, 5, 5]);
		const b = directionBreadth([up, up, down, flat]);
		expect(b).toEqual({ up: 2, down: 1, flat: 1, total: 4 });
	});
});

describe('macroBoard — 국면 모멘텀 궤적', () => {
	it('returns a (growth z, inflation z) trail capped at n, monthly-joined', () => {
		const growth = monthly(Array.from({ length: 18 }, (_, k) => k % 5), 202301);
		const infl = monthly(Array.from({ length: 18 }, (_, k) => (k * 2) % 7), 202301);
		const trail = growthInflationMomentum(growth, infl, 12);
		expect(trail.length).toBe(12);
		expect(trail[0]).toHaveProperty('ym');
		expect(trail[0]).toHaveProperty('g');
		expect(trail[0]).toHaveProperty('i');
		// z 라 유한.
		expect(trail.every((p) => Number.isFinite(p.g) && Number.isFinite(p.i))).toBe(true);
	});

	it('is NaN-safe on insufficient/degenerate input', () => {
		expect(growthInflationMomentum([], [], 12)).toEqual([]);
		expect(growthInflationMomentum(monthly([1, 1, 1]), monthly([2, 3, 4]), 12)).toEqual([]); // 성장 std 0
	});

	it('quadOf maps growth/inflation signs to GIP quadrants', () => {
		expect(quadOf(1, 1)).toBe('reflation'); // 성장↑물가↑
		expect(quadOf(1, -1)).toBe('goldilocks'); // 성장↑물가↓
		expect(quadOf(-1, 1)).toBe('stagflation'); // 성장↓물가↑
		expect(quadOf(-1, -1)).toBe('deflation'); // 성장↓물가↓
	});
});

describe('macroBoard — 카테고리·국가·NBER', () => {
	it('categoryOf maps groups; curve spreads special-cased to 신용·곡선', () => {
		expect(categoryOf(def({ id: 'CPI', group: '한국물가' }))).toBe('물가');
		expect(categoryOf(def({ id: 'CLI', group: '경기·심리' }))).toBe('성장·경기');
		expect(categoryOf(def({ id: 'BASE_RATE', group: '한국금리' }))).toBe('금리·통화');
		expect(categoryOf(def({ id: 'BAMLH0A0HYM2', group: '미국신용' }))).toBe('신용·곡선');
		// 곡선 스프레드 — group 은 미국금리지만 신용·곡선.
		expect(categoryOf(def({ id: 'T10Y3M', group: '미국금리' }))).toBe('신용·곡선');
		expect(categoryOf(def({ id: 'T10Y2Y', group: '미국금리' }))).toBe('신용·곡선');
		expect(categoryOf(def({ id: 'DCOILWTICO', group: '원자재' }))).toBe('시장·원자재');
		expect(categoryOf(def({ id: 'HOUSE_PRICE', group: '부동산' }))).toBe('부동산');
	});

	it('matchesCountry filters by source (KR=ecos, US=fred)', () => {
		expect(matchesCountry(def({ src: 'ecos' }), 'KR')).toBe(true);
		expect(matchesCountry(def({ src: 'ecos' }), 'US')).toBe(false);
		expect(matchesCountry(def({ src: 'fred' }), 'US')).toBe(true);
		expect(matchesCountry(def({ src: 'fred' }), 'both')).toBe(true);
		expect(matchesCountry(def({ src: 'ecos' }), 'both')).toBe(true);
	});

	it('NBER_RECESSIONS are well-formed YYYYMMDD [start,end] with start<end', () => {
		expect(NBER_RECESSIONS.length).toBeGreaterThan(0);
		for (const [s, e] of NBER_RECESSIONS) {
			expect(s).toMatch(/^\d{8}$/);
			expect(e).toMatch(/^\d{8}$/);
			expect(ymdToMs(s)).toBeLessThan(ymdToMs(e));
		}
		// 2020 코로나 침체 포함.
		expect(NBER_RECESSIONS.some(([s]) => s.startsWith('2020'))).toBe(true);
	});

	it('BOARD_CATEGORIES covers the six analytical groups', () => {
		expect(BOARD_CATEGORIES.map((c) => c.key)).toEqual(['성장·경기', '물가', '금리·통화', '신용·곡선', '시장·원자재', '부동산']);
	});
});
