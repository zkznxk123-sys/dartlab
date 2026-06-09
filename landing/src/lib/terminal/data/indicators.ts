// 보조지표 — OHLCV close 배열에서 클라이언트 계산 (gather 지표는 Python 서버용이라 브라우저는 직접 산출).
export function sma(a: number[], p: number): (number | null)[] {
	const o: (number | null)[] = [];
	for (let i = 0; i < a.length; i++) {
		if (i < p - 1) {
			o.push(null);
			continue;
		}
		let s = 0;
		for (let j = i - p + 1; j <= i; j++) s += a[j];
		o.push(s / p);
	}
	return o;
}
export function ema(a: number[], p: number): number[] {
	const k = 2 / (p + 1);
	const o: number[] = [];
	let pr = 0;
	a.forEach((v, i) => {
		pr = i === 0 ? v : v * k + pr * (1 - k);
		o.push(pr);
	});
	return o;
}
export function rsi(a: number[], p = 14): (number | null)[] {
	const o: (number | null)[] = [null];
	let g = 0;
	let l = 0;
	for (let i = 1; i < a.length; i++) {
		const c = a[i] - a[i - 1];
		const u = Math.max(c, 0);
		const d = Math.max(-c, 0);
		if (i <= p) {
			g += u;
			l += d;
			if (i === p) {
				g /= p;
				l /= p;
				o.push(100 - 100 / (1 + g / (l || 1e-9)));
			} else o.push(null);
		} else {
			g = (g * (p - 1) + u) / p;
			l = (l * (p - 1) + d) / p;
			o.push(100 - 100 / (1 + g / (l || 1e-9)));
		}
	}
	return o;
}
export interface Macd {
	line: number[];
	signal: number[];
	hist: number[];
}
export function macd(a: number[]): Macd {
	const e12 = ema(a, 12);
	const e26 = ema(a, 26);
	const line = e12.map((v, i) => v - e26[i]);
	const signal = ema(line, 9);
	const hist = line.map((v, i) => v - signal[i]);
	return { line, signal, hist };
}
export interface Bollinger {
	mid: (number | null)[];
	upper: (number | null)[];
	lower: (number | null)[];
}
export function bollinger(a: number[], p = 20, mult = 2): Bollinger {
	const mid = sma(a, p);
	const upper: (number | null)[] = [];
	const lower: (number | null)[] = [];
	for (let i = 0; i < a.length; i++) {
		const m = mid[i];
		if (m == null) {
			upper.push(null);
			lower.push(null);
			continue;
		}
		let s = 0;
		for (let j = i - p + 1; j <= i; j++) s += (a[j] - m) ** 2;
		const sd = Math.sqrt(s / p);
		upper.push(m + mult * sd);
		lower.push(m - mult * sd);
	}
	return { mid, upper, lower };
}
