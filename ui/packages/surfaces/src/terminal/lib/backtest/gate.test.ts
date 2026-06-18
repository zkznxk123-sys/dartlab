import { describe, expect, it } from 'vitest';
import { buildGateSeries, ruleUsesGate } from './gate';
import { evalCondition, evalRule } from './conditions';
import { runBacktestRule } from './engine';
import type { Candle } from './types';
import type { Condition, StrategyRule } from './conditions';

describe('buildGateSeries — PIT 계단(look-ahead 0)', () => {
	it('공시일 이후 봉부터 값, 그 전 null · 계단 유지', () => {
		const dates = ['20210101', '20210301', '20210401', '20220301', '20220401'];
		const rows = [
			{ rceptDt: '20210315', piotroski: 4 }, // 2020 사업보고서
			{ rceptDt: '20220318', piotroski: 8 } // 2021 사업보고서
		];
		const g = buildGateSeries(dates, rows);
		// 20210101·20210301 = 첫 공시(0315) 전 → null
		expect(g[0]).toBeNull();
		expect(g[1]).toBeNull();
		// 20210401 = 0315 이후 → 4 (계단)
		expect(g[2]).toBe(4);
		// 20220301 = 아직 0318 전 → 여전히 4
		expect(g[3]).toBe(4);
		// 20220401 = 0318 이후 → 8
		expect(g[4]).toBe(8);
	});
});

describe('fundGate 조건 — 재무 게이트 진입 차단', () => {
	const mkCandles = (n: number): Candle[] =>
		Array.from({ length: n }, (_, i) => ({ t: `2021${String(i + 1).padStart(4, '0')}`, o: 100, h: 101, l: 99, c: 100, v: 1000 }));

	it('evalCondition: fundGate≥6 — gate null/저점=0, 충족=1', () => {
		const cs = mkCandles(4);
		const gate = [null, 4, 7, 8]; // 봉별 Piotroski
		const cond: Condition = { left: 'fundGate', leftParams: {}, op: '>=', right: { kind: 'const', value: 6 } };
		const sat = evalCondition(cs, cond, gate);
		expect(Array.from(sat)).toEqual([0, 0, 1, 1]); // null·4=차단, 7·8=통과
	});

	it('evalRule + 게이트: 공시 전엔 진입 0 (gate=null 봉)', () => {
		const cs = mkCandles(4);
		const gate = [null, null, 7, 7];
		const rule: StrategyRule = {
			entry: [{ left: 'fundGate', leftParams: {}, op: '>=', right: { kind: 'const', value: 6 } }],
			entryCombine: 'AND',
			exit: [],
			exitCombine: 'OR'
		};
		const ev = evalRule(cs, rule, gate);
		expect(Array.from(ev.entryCombined)).toEqual([0, 0, 1, 1]);
		expect(ruleUsesGate(rule)).toBe(true);
	});

	it('runBacktestRule: gate 없으면 fundGate 조건=항상 0(진입 0, 회귀 안전)', () => {
		const cs = mkCandles(40);
		const rule: StrategyRule = {
			entry: [{ left: 'fundGate', leftParams: {}, op: '>=', right: { kind: 'const', value: 6 } }],
			entryCombine: 'AND',
			exit: [],
			exitCombine: 'OR'
		};
		const res = runBacktestRule(cs, rule, { windowBars: 40, withCosts: false, costsBp: { commissionBp: 0, sellTaxBp: 0, slippageBp: 0 } });
		// gate 미주입 → fundGate 항상 null → 진입 0 → 거래 0(엔진 정상 반환)
		expect(res).not.toBeNull();
		expect(res!.trades.length).toBe(0);
	});
});
