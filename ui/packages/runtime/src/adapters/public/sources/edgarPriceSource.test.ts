// US(EDGAR) 주가 source 정규화 단위 테스트 — date(YYYY-MM-DD/YYYYMMDD/epoch 방어)→Candle.t(YYYYMMDD)
// 변환·오름차순 정렬·일자 dedup·null/비정상 close 행 제외를 네트워크 없이 검증(parseEdgarPriceRows 순수 함수).
// bake schema(date/open/high/low/close/volume)는 KR gov company 와 동형 — close=수정주가라 r/tv=null.
import { describe, it, expect } from 'vitest';
import { parseEdgarPriceRows } from './edgarPriceSource';

function row(o: Partial<Record<string, unknown>>): Record<string, unknown> {
	return { date: '2026-06-24', open: 1, high: 1, low: 1, close: 1, volume: 1, ...o };
}

describe('parseEdgarPriceRows', () => {
	it("date 'YYYY-MM-DD'(gather 출력) → Candle.t 'YYYYMMDD'", () => {
		const out = parseEdgarPriceRows([row({ date: '2017-05-31', close: 38.5 })]);
		expect(out).toHaveLength(1);
		expect(out[0]?.t).toBe('20170531');
		expect(out[0]?.c).toBe(38.5);
	});

	it("이미 'YYYYMMDD' 인 date 도 통과(대시 제거 idempotent)", () => {
		const out = parseEdgarPriceRows([row({ date: '20260624', close: 293.08 })]);
		expect(out[0]?.t).toBe('20260624');
	});

	it('OHLCV 매핑 + 수정주가라 r/tv=null', () => {
		const out = parseEdgarPriceRows([row({ date: '2026-06-22', open: 297.31, high: 302.42, low: 296.76, close: 297.01, volume: 44879914 })]);
		expect(out[0]).toEqual({ t: '20260622', o: 297.31, h: 302.42, l: 296.76, c: 297.01, v: 44879914, r: null, tv: null });
	});

	it('오름차순 정렬 + 일자 dedup(연도 경계 안전)', () => {
		const out = parseEdgarPriceRows([
			row({ date: '2026-06-24', close: 3 }),
			row({ date: '2026-06-22', close: 1 }),
			row({ date: '2026-06-24', close: 9 }), // 중복 일자 — keep-first(정렬 후 첫 항목)
			row({ date: '2026-06-23', close: 2 })
		]);
		expect(out.map((k) => k.t)).toEqual(['20260622', '20260623', '20260624']);
		expect(out.find((k) => k.t === '20260624')?.c).toBe(3); // keep-first
	});

	it('null·0·음수 close, 빈 date 행 제외', () => {
		const out = parseEdgarPriceRows([
			row({ date: '2026-06-20', close: null }), // close 없음
			row({ date: '2026-06-21', close: 0 }), // 0 제외
			row({ date: '2026-06-22', close: -5 }), // 음수 제외
			row({ date: '', close: 100 }), // date 없음
			row({ date: '2026-06-23', close: 250.5 }) // 유효
		]);
		expect(out.map((k) => k.t)).toEqual(['20260623']);
	});

	it('open/high/low 결측 시 close 로 폴백(라인 degenerate 방어)', () => {
		const out = parseEdgarPriceRows([row({ date: '2026-06-24', open: null, high: null, low: null, close: 100 })]);
		expect(out[0]).toMatchObject({ o: 100, h: 100, l: 100, c: 100 });
	});
});
