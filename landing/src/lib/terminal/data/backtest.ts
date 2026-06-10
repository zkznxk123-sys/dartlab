// 차트 내 백테스팅 엔진 — 순수함수 (svelte/klinecharts/DOM import 0).
// 체결 모델: 신호 t일 종가 확정 → t+1일 시가 체결. 엔진이 target 을 1봉 shift 해 적용하므로
// 전략 코드가 실수해도 look-ahead 가 구조적으로 불가능하다. 거래정지(v=0) 봉은 체결 자동 이연.
// B&H = 같은 엔진에 target≡1 주입 — 체결·비용·이연 로직이 동등해 공정 비교가 코드로 보장된다.
// 수량은 자본 비례 연속 수량(정수 반올림 생략) — % 수익률 비교 목적.
import { sma, rsi, macd, bollinger } from './indicators';
import type { Candle } from './priceSeries';

export type BtPresetKey = 'maCross' | 'rsiRevert' | 'bbRevert' | 'macdCross';

export interface BtParamDef {
	name: string;
	kr: string;
	en: string;
	min: number;
	max: number;
	step: number;
	def: number;
}
export interface BtPresetDef {
	key: BtPresetKey;
	kr: string;
	en: string;
	descKr: string;
	descEn: string;
	params: BtParamDef[];
	warmup: (p: Record<string, number>) => number;
	// 당일 종가까지의 데이터만으로 계산한 목표 포지션 (0|1). trailing window 만 사용.
	signal: (closes: number[], p: Record<string, number>) => Int8Array;
}

// 비용 기본값 (bp) — opts.costsBp 로 편집 가능. 수수료 양측 + 매도 거래세 + 슬리피지.
export const BT_COSTS = { commissionBp: 1.5, sellTaxBp: 15, slippageBp: 10 };
export type BtCostsBp = { commissionBp: number; sellTaxBp: number; slippageBp: number };

export const BT_PRESETS: BtPresetDef[] = [
	{
		key: 'maCross',
		kr: '골든크로스',
		en: 'MA Cross',
		descKr: '단기 이평 > 장기 이평이면 보유',
		descEn: 'hold while fast SMA > slow SMA',
		params: [
			{ name: 'fast', kr: '단기', en: 'fast', min: 5, max: 50, step: 5, def: 20 },
			{ name: 'slow', kr: '장기', en: 'slow', min: 20, max: 200, step: 10, def: 60 }
		],
		warmup: (p) => p.slow,
		signal: (c, p) => {
			const f = sma(c, p.fast);
			const s = sma(c, p.slow);
			const t = new Int8Array(c.length);
			for (let i = 0; i < c.length; i++) t[i] = f[i] != null && s[i] != null && (f[i] as number) > (s[i] as number) ? 1 : 0;
			return t;
		}
	},
	{
		key: 'rsiRevert',
		kr: 'RSI 과매도 반등',
		en: 'RSI Revert',
		descKr: 'RSI < 매수선 진입, > 매도선 청산',
		descEn: 'enter RSI < buy, exit > sell',
		params: [
			{ name: 'period', kr: '기간', en: 'period', min: 7, max: 28, step: 7, def: 14 },
			{ name: 'buyTh', kr: '매수선', en: 'buy', min: 10, max: 40, step: 5, def: 30 },
			{ name: 'sellTh', kr: '매도선', en: 'sell', min: 55, max: 80, step: 5, def: 70 }
		],
		warmup: (p) => p.period + 1,
		signal: (c, p) => {
			const r = rsi(c, p.period);
			const t = new Int8Array(c.length);
			let state = 0;
			for (let i = 0; i < c.length; i++) {
				const v = r[i];
				if (v != null) state = state === 0 ? (v < p.buyTh ? 1 : 0) : v > p.sellTh ? 0 : 1;
				t[i] = state;
			}
			return t;
		}
	},
	{
		key: 'bbRevert',
		kr: '볼린저 하단회귀',
		en: 'BB Revert',
		descKr: '종가 < 하단밴드 진입, ≥ 중심선 청산',
		descEn: 'enter below lower band, exit at mid',
		params: [
			{ name: 'period', kr: '기간', en: 'period', min: 10, max: 60, step: 5, def: 20 },
			{ name: 'mult', kr: '승수', en: 'mult', min: 1, max: 4, step: 0.5, def: 2 }
		],
		warmup: (p) => p.period,
		signal: (c, p) => {
			const bb = bollinger(c, p.period, p.mult);
			const t = new Int8Array(c.length);
			let state = 0;
			for (let i = 0; i < c.length; i++) {
				const lo = bb.lower[i];
				const mid = bb.mid[i];
				if (lo != null && mid != null) state = state === 0 ? (c[i] < lo ? 1 : 0) : c[i] >= mid ? 0 : 1;
				t[i] = state;
			}
			return t;
		}
	},
	{
		key: 'macdCross',
		kr: 'MACD 시그널',
		en: 'MACD Cross',
		descKr: 'MACD선 > 시그널선이면 보유',
		descEn: 'hold while MACD > signal',
		params: [
			{ name: 'fast', kr: '단기', en: 'fast', min: 5, max: 20, step: 1, def: 12 },
			{ name: 'slow', kr: '장기', en: 'slow', min: 20, max: 60, step: 1, def: 26 },
			{ name: 'sig', kr: '시그널', en: 'sig', min: 5, max: 15, step: 1, def: 9 }
		],
		warmup: (p) => p.slow + p.sig,
		signal: (c, p) => {
			const m = macd(c, p.fast, p.slow, p.sig);
			const t = new Int8Array(c.length);
			const start = p.slow + p.sig;
			for (let i = start; i < c.length; i++) t[i] = m.line[i] > m.signal[i] ? 1 : 0;
			return t;
		}
	}
];

export interface BtTrade {
	entryT: string; // YYYYMMDD
	exitT: string | null; // null = 미청산
	entryPx: number; // 비용 반영 유효체결가
	exitPx: number | null;
	retPct: number;
	holdDays: number; // 거래일(봉) 수
	open: boolean;
}
export interface BtWarning {
	kind: 'fewTrades' | 'shortRange' | 'splitSuspect' | 'costsOff';
	date?: string;
}
export interface BtMetrics {
	retPct: number;
	cagrPct: number | null; // windowBars < 252 → null (연환산 거짓말 차단)
	mddPct: number;
	winRatePct: number | null;
	profitFactor: number | null;
	tradeCount: number;
	avgHoldDays: number | null;
	exposurePct: number;
	costDragPct: number; // 비용 ON 수익률 − 비용 OFF 수익률 (≤0)
}
export interface BtResult {
	startIdx: number; // 평가창 시작 (candles 인덱스)
	equity: (number | null)[]; // candles 와 같은 길이, 창 밖 = null, equity[startIdx]=100
	bhEquity: (number | null)[];
	trades: BtTrade[];
	metrics: BtMetrics;
	bh: { retPct: number; cagrPct: number | null; mddPct: number };
	warnings: BtWarning[];
}

interface Costs {
	comm: number;
	tax: number;
	slip: number;
}
const ZERO_COSTS: Costs = { comm: 0, tax: 0, slip: 0 };
const toCosts = (bp: BtCostsBp = BT_COSTS): Costs => ({ comm: bp.commissionBp / 1e4, tax: bp.sellTaxBp / 1e4, slip: bp.slippageBp / 1e4 });

interface PassOut {
	equity: (number | null)[];
	trades: BtTrade[];
	heldBars: number;
}

// 단일 패스 — target[i-1] 을 i 봉 시가에 적용 (1봉 shift). 4,000봉 < 1ms.
function runPass(candles: Candle[], target: Int8Array, startIdx: number, k: Costs): PassOut {
	const n = candles.length;
	const equity: (number | null)[] = new Array(n).fill(null);
	const trades: BtTrade[] = [];
	let pos = 0;
	let cash = 100;
	let shares = 0;
	let entryCash = 0;
	let entryIdx = -1;
	let entryPx = 0;
	let heldBars = 0;
	equity[startIdx] = 100;
	for (let i = startIdx + 1; i < n; i++) {
		const b = candles[i];
		const want = target[i - 1];
		if (want !== pos && b.v > 0 && b.o > 0) {
			if (want === 1) {
				const px = b.o * (1 + k.slip);
				entryPx = px * (1 + k.comm);
				entryCash = cash;
				shares = cash / entryPx;
				cash = 0;
				pos = 1;
				entryIdx = i;
			} else {
				const px = b.o * (1 - k.slip);
				const exitPx = px * (1 - k.comm - k.tax);
				cash = shares * exitPx;
				shares = 0;
				pos = 0;
				trades.push({
					entryT: candles[entryIdx].t,
					exitT: b.t,
					entryPx,
					exitPx,
					retPct: (cash / entryCash - 1) * 100,
					holdDays: i - entryIdx,
					open: false
				});
			}
		}
		if (pos === 1) heldBars++;
		equity[i] = cash + shares * b.c;
	}
	if (pos === 1) {
		// 미청산 — 마지막 종가에 가상 매도비용 차감 평가
		const last = candles[n - 1];
		const virtual = shares * last.c * (1 - k.slip) * (1 - k.comm - k.tax);
		trades.push({
			entryT: candles[entryIdx].t,
			exitT: null,
			entryPx,
			exitPx: null,
			retPct: (virtual / entryCash - 1) * 100,
			holdDays: n - 1 - entryIdx,
			open: true
		});
	}
	return { equity, trades, heldBars };
}

function mdd(equity: (number | null)[]): number {
	let peak = -Infinity;
	let worst = 0;
	for (const e of equity) {
		if (e == null) continue;
		if (e > peak) peak = e;
		else if (peak > 0) worst = Math.min(worst, (e / peak - 1) * 100);
	}
	return worst;
}

function endRet(equity: (number | null)[]): number {
	for (let i = equity.length - 1; i >= 0; i--) if (equity[i] != null) return (equity[i]! / 100 - 1) * 100;
	return 0;
}

function cagr(retPct: number, windowBars: number): number | null {
	if (windowBars < 252) return null;
	return (Math.pow(1 + retPct / 100, 252 / windowBars) - 1) * 100;
}

// 무수정주가 분할 의심 — 전봉 종가/당봉 시가 비가 정수배(상대 ±2%) & ≥1.5배.
// 상대 오차라야 50:1 같은 대비율도 잡힌다. 일일 가격제한 ±30%(r≤1.43)는 구조적으로 안전.
function findSplitSuspect(candles: Candle[], startIdx: number): string | null {
	for (let i = Math.max(1, startIdx + 1); i < candles.length; i++) {
		const prev = candles[i - 1].c;
		const o = candles[i].o;
		if (!(prev > 0) || !(o > 0)) continue;
		const r = prev / o;
		const rr = r >= 1 ? r : 1 / r;
		const near = Math.round(rr);
		if (rr >= 1.5 && near >= 2 && Math.abs(rr - near) / near < 0.02) return candles[i].t;
	}
	return null;
}

/** 백테스트 실행 — 전략(선택 비용)·전략(비용 OFF, 비용드래그용)·B&H(동일 비용) 3패스. null = candles 부족. */
export function runBacktest(
	candles: Candle[],
	preset: BtPresetKey,
	params: Record<string, number>,
	opts: { windowBars: number; withCosts: boolean; costsBp?: BtCostsBp }
): BtResult | null {
	const def = BT_PRESETS.find((d) => d.key === preset);
	if (!def) return null;
	const n = candles.length;
	if (n < def.warmup(params) + 5) return null;
	const closes = candles.map((c) => c.c);
	// 신호는 전체 이력로 계산(워밍업 자동 확보), 체결·평가는 평가창 안에서만.
	const target = def.signal(closes, params);
	const startIdx = Math.max(0, n - Math.max(2, opts.windowBars));
	const windowBars = n - startIdx;
	const full = toCosts(opts.costsBp);
	const costs = opts.withCosts ? full : ZERO_COSTS;

	const strat = runPass(candles, target, startIdx, costs);
	const stratOn = opts.withCosts ? strat : runPass(candles, target, startIdx, full);
	const stratOff = opts.withCosts ? runPass(candles, target, startIdx, ZERO_COSTS) : strat;
	const hold = new Int8Array(n).fill(1);
	const bhPass = runPass(candles, hold, startIdx, costs);

	const retPct = endRet(strat.equity);
	const closedAndOpen = strat.trades;
	const wins = closedAndOpen.filter((t) => t.retPct > 0);
	const losses = closedAndOpen.filter((t) => t.retPct < 0);
	const gainSum = wins.reduce((a, t) => a + t.retPct, 0);
	const lossSum = Math.abs(losses.reduce((a, t) => a + t.retPct, 0));

	const warnings: BtWarning[] = [];
	if (closedAndOpen.length < 10) warnings.push({ kind: 'fewTrades' });
	if (windowBars < 120) warnings.push({ kind: 'shortRange' });
	const splitDate = findSplitSuspect(candles, startIdx);
	if (splitDate) warnings.push({ kind: 'splitSuspect', date: splitDate });
	if (!opts.withCosts) warnings.push({ kind: 'costsOff' });

	const bhRet = endRet(bhPass.equity);
	return {
		startIdx,
		equity: strat.equity,
		bhEquity: bhPass.equity,
		trades: closedAndOpen,
		metrics: {
			retPct,
			cagrPct: cagr(retPct, windowBars),
			mddPct: mdd(strat.equity),
			winRatePct: closedAndOpen.length ? (wins.length / closedAndOpen.length) * 100 : null,
			profitFactor: lossSum > 0 ? gainSum / lossSum : null,
			tradeCount: closedAndOpen.length,
			avgHoldDays: closedAndOpen.length ? closedAndOpen.reduce((a, t) => a + t.holdDays, 0) / closedAndOpen.length : null,
			exposurePct: (strat.heldBars / Math.max(1, windowBars - 1)) * 100,
			costDragPct: endRet(stratOn.equity) - endRet(stratOff.equity)
		},
		bh: { retPct: bhRet, cagrPct: cagr(bhRet, windowBars), mddPct: mdd(bhPass.equity) },
		warnings
	};
}
