<script lang="ts">
	// 고성능 주가 캔들 (Canvas2D) — 멀티 보조지표 패널(동시 다중) + 멀티 MA + 적정밴드·실적 마커.
	import type { Candle } from '../data/priceSeries';
	import type { Lang } from '../data/types';
	import { sma, rsi, macd, bollinger, stochastic, obv } from '../data/indicators';
	import { fmtNum, fmtAbbr } from '../ui/helpers';

	export type SubKey = 'VOL' | 'RSI' | 'MACD' | 'STOCH' | 'OBV';
	interface Props {
		candles: Candle[];
		lang: Lang;
		period: '3M' | '5M' | '6M' | '1Y' | 'MAX';
		overlay: 'MA' | 'BB' | 'NONE';
		subs: SubKey[]; // 동시 표시할 보조지표 패널 (스택)
		events?: { date: string; label: string }[];
		valBand?: { lo: number; mid: number; hi: number } | null;
	}
	let { candles, lang, period, overlay, subs, events, valBand }: Props = $props();

	let wrap: HTMLDivElement | null = $state(null);
	let canvas: HTMLCanvasElement | null = $state(null);
	let hover = $state<number | null>(null);
	let dims = $state({ w: 800, h: 420 });

	const C = {
		up: '#34d399', dn: '#f0616f', ma5: '#e879f9', ma20: '#fb923c', ma60: '#60a5fa', ma120: '#a78bfa',
		bb: 'rgba(167,139,250,0.5)', grid: '#1b2130', axis: '#2a3142', text: '#a3a8b3',
		macdUp: 'rgba(52,211,153,0.6)', macdDn: 'rgba(240,97,111,0.6)', stochK: '#fb923c', stochD: '#60a5fa', obv: '#22d3ee'
	};
	const PERIOD_N: Record<string, number> = { '3M': 66, '5M': 110, '6M': 132, '1Y': 252, MAX: 100000 };
	const SUBH = 46;
	const SUBGAP = 6;

	// 차트 높이 = 가격영역 + 보조패널 수만큼 (보조지표 늘리면 차트가 커짐)
	const wrapH = $derived(330 + subs.length * (SUBH + SUBGAP));

	$effect(() => {
		if (!wrap) return;
		const ro = new ResizeObserver((es) => {
			for (const e of es) {
				const cr = e.contentRect;
				dims = { w: Math.max(280, cr.width), h: Math.max(200, cr.height) };
			}
		});
		ro.observe(wrap);
		return () => ro.disconnect();
	});

	const slice = $derived(candles.slice(-Math.min(candles.length, PERIOD_N[period] || candles.length)));

	$effect(() => {
		const cv = canvas;
		if (!cv) return;
		const s = slice;
		const hv = hover;
		const ov = overlay;
		const sbs = subs;
		void events;
		void valBand;
		const dpr = window.devicePixelRatio || 1;
		const W = dims.w;
		const H = dims.h;
		cv.width = W * dpr;
		cv.height = H * dpr;
		cv.style.width = W + 'px';
		cv.style.height = H + 'px';
		const ctx = cv.getContext('2d');
		if (!ctx || !s.length) {
			if (ctx) ctx.clearRect(0, 0, W, H);
			return;
		}
		ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
		ctx.clearRect(0, 0, W, H);
		ctx.font = '8px "JetBrains Mono", monospace';
		ctx.textBaseline = 'middle';

		const padR = 48;
		const padL = 4;
		const padT = 6;
		const xLblH = 14;
		const subsBlock = sbs.length ? SUBGAP + sbs.length * SUBH + (sbs.length - 1) * SUBGAP : 0;
		const priceH = H - padT - subsBlock - xLblH;
		const plotW = W - padR - padL;
		const n = s.length;
		const closes = s.map((c) => c.c);
		const highs = s.map((c) => c.h);
		const lows = s.map((c) => c.l);
		const vols = s.map((c) => c.v);

		const lo = Math.min(...lows);
		const hi = Math.max(...highs);
		const pad = (hi - lo) * 0.04 || 1;
		const yMin = lo - pad;
		const yMax = hi + pad;
		const Y = (v: number) => padT + priceH - ((v - yMin) / (yMax - yMin)) * priceH;
		const cw = plotW / n;
		const X = (i: number) => padL + i * cw + cw / 2;

		// price grid + y labels
		for (let k = 0; k <= 4; k++) {
			const v = yMin + ((yMax - yMin) * k) / 4;
			const y = Y(v);
			ctx.strokeStyle = C.grid;
			ctx.lineWidth = 1;
			ctx.beginPath();
			ctx.moveTo(padL, y);
			ctx.lineTo(padL + plotW, y);
			ctx.stroke();
			ctx.fillStyle = C.text;
			ctx.textAlign = 'left';
			ctx.fillText(fmtNum(v, 0), padL + plotW + 4, y);
		}

		// 적정주가 밴드 (캔들 뒤)
		if (valBand && valBand.hi > valBand.lo) {
			const cl = (v: number) => Math.max(yMin, Math.min(yMax, v));
			const yHi = Y(cl(valBand.hi));
			const yLo = Y(cl(valBand.lo));
			ctx.fillStyle = 'rgba(96,165,250,0.08)';
			ctx.fillRect(padL, Math.min(yHi, yLo), plotW, Math.abs(yLo - yHi));
			if (valBand.mid >= yMin && valBand.mid <= yMax) {
				ctx.strokeStyle = 'rgba(96,165,250,0.55)';
				ctx.setLineDash([4, 3]);
				ctx.lineWidth = 1;
				ctx.beginPath();
				ctx.moveTo(padL, Y(valBand.mid));
				ctx.lineTo(padL + plotW, Y(valBand.mid));
				ctx.stroke();
				ctx.setLineDash([]);
			}
			ctx.fillStyle = 'rgba(96,165,250,0.85)';
			ctx.textAlign = 'left';
			ctx.fillText(lang === 'en' ? 'fair' : '적정', padL + 2, Math.min(yHi, yLo) + 5);
		}

		const drawLine = (arr: (number | null)[], color: string, top: (v: number) => number, w = 1.2) => {
			ctx.strokeStyle = color;
			ctx.lineWidth = w;
			ctx.beginPath();
			let st = false;
			arr.forEach((v, i) => {
				if (v == null) return;
				const x = X(i);
				const y = top(v);
				st ? ctx.lineTo(x, y) : ((ctx.moveTo(x, y), (st = true)));
			});
			ctx.stroke();
		};

		// Bollinger (캔들 뒤)
		if (ov === 'BB') {
			const bb = bollinger(closes, 20, 2);
			drawLine(bb.upper, C.bb, Y);
			drawLine(bb.lower, C.bb, Y);
			drawLine(bb.mid, 'rgba(167,139,250,0.85)', Y);
		}

		// candles
		s.forEach((c, i) => {
			const x = X(i);
			const up = c.c >= c.o;
			const col = up ? C.up : C.dn;
			ctx.strokeStyle = col;
			ctx.fillStyle = col;
			ctx.lineWidth = 1;
			ctx.beginPath();
			ctx.moveTo(x, Y(c.h));
			ctx.lineTo(x, Y(c.l));
			ctx.stroke();
			const bw = Math.max(1, cw * 0.62);
			const yo = Y(c.o);
			const yc = Y(c.c);
			ctx.fillRect(x - bw / 2, Math.min(yo, yc), bw, Math.max(1, Math.abs(yc - yo)));
		});

		// 실적·공시 시점 마커
		if (events && events.length) {
			const first = s[0].t;
			const last = s[n - 1].t;
			for (const ev of events) {
				if (ev.date < first || ev.date > last) continue;
				let j = 0;
				let best = Infinity;
				for (let i = 0; i < n; i++) {
					const d = Math.abs(Number(s[i].t) - Number(ev.date));
					if (d < best) { best = d; j = i; }
				}
				const x = X(j);
				ctx.strokeStyle = 'rgba(251,146,60,0.4)';
				ctx.setLineDash([2, 2]);
				ctx.lineWidth = 1;
				ctx.beginPath();
				ctx.moveTo(x, padT + 9);
				ctx.lineTo(x, padT + priceH);
				ctx.stroke();
				ctx.setLineDash([]);
				ctx.fillStyle = 'rgba(251,146,60,0.9)';
				ctx.beginPath();
				ctx.moveTo(x, padT + priceH - 2);
				ctx.lineTo(x - 3, padT + priceH + 3);
				ctx.lineTo(x + 3, padT + priceH + 3);
				ctx.closePath();
				ctx.fill();
				ctx.fillStyle = C.text;
				ctx.textAlign = 'center';
				ctx.fillText(ev.label, x, padT + 5);
			}
		}

		// MA 오버레이 (5·20·60·120 다중)
		if (ov === 'MA') {
			drawLine(sma(closes, 5), C.ma5, Y, 1);
			drawLine(sma(closes, 20), C.ma20, Y);
			drawLine(sma(closes, 60), C.ma60, Y);
			drawLine(sma(closes, 120), C.ma120, Y);
			ctx.fillStyle = C.text;
			ctx.textAlign = 'left';
			ctx.fillText('MA 5·20·60·120', padL + 2, padT + 6);
		}

		// ── 보조지표 패널 (스택) ──
		sbs.forEach((sb, idx) => {
			const top = padT + priceH + SUBGAP + idx * (SUBH + SUBGAP);
			const bot = top + SUBH;
			ctx.strokeStyle = C.grid;
			ctx.lineWidth = 1;
			ctx.beginPath();
			ctx.moveTo(padL, top);
			ctx.lineTo(padL + plotW, top);
			ctx.stroke();
			const label = (t: string) => {
				ctx.fillStyle = C.text;
				ctx.textAlign = 'left';
				ctx.fillText(t, padL + 2, top + 6);
			};
			if (sb === 'VOL') {
				const vMax = Math.max(...vols, 1);
				s.forEach((c, i) => {
					const x = X(i);
					const up = c.c >= c.o;
					const h = (c.v / vMax) * (SUBH - 4);
					ctx.fillStyle = up ? 'rgba(52,211,153,0.45)' : 'rgba(240,97,111,0.45)';
					ctx.fillRect(x - Math.max(1, cw * 0.62) / 2, bot - h, Math.max(1, cw * 0.62), h);
				});
				label('VOL');
			} else if (sb === 'RSI') {
				const r = rsi(closes, 14);
				const SY = (v: number) => bot - (v / 100) * SUBH;
				[30, 70].forEach((lv) => {
					ctx.strokeStyle = 'rgba(251,146,60,0.18)';
					ctx.beginPath();
					ctx.moveTo(padL, SY(lv));
					ctx.lineTo(padL + plotW, SY(lv));
					ctx.stroke();
				});
				drawLine(r, C.ma20, SY, 1.1);
				label('RSI 14');
			} else if (sb === 'MACD') {
				const m = macd(closes);
				const all = m.line.concat(m.signal, m.hist).filter((v) => Number.isFinite(v));
				const mx = Math.max(...all.map(Math.abs), 1);
				const SY = (v: number) => top + SUBH / 2 - (v / mx) * (SUBH / 2 - 3);
				m.hist.forEach((v, i) => {
					const x = X(i);
					ctx.fillStyle = v >= 0 ? C.macdUp : C.macdDn;
					const y0 = SY(0);
					const y1 = SY(v);
					ctx.fillRect(x - Math.max(1, cw * 0.5) / 2, Math.min(y0, y1), Math.max(1, cw * 0.5), Math.abs(y1 - y0));
				});
				drawLine(m.line, C.ma20, SY, 1);
				drawLine(m.signal, C.ma60, SY, 1);
				label('MACD 12/26/9');
			} else if (sb === 'STOCH') {
				const st = stochastic(highs, lows, closes, 14, 3);
				const SY = (v: number) => bot - (v / 100) * SUBH;
				[20, 80].forEach((lv) => {
					ctx.strokeStyle = 'rgba(251,146,60,0.18)';
					ctx.beginPath();
					ctx.moveTo(padL, SY(lv));
					ctx.lineTo(padL + plotW, SY(lv));
					ctx.stroke();
				});
				drawLine(st.k, C.stochK, SY, 1.1);
				drawLine(st.d, C.stochD, SY, 1);
				label('STOCH 14/3');
			} else if (sb === 'OBV') {
				const o = obv(closes, vols);
				const omin = Math.min(...o);
				const omax = Math.max(...o);
				const rng = omax - omin || 1;
				const SY = (v: number) => bot - ((v - omin) / rng) * (SUBH - 4) - 2;
				drawLine(o, C.obv, SY, 1.1);
				label('OBV');
			}
		});

		// x labels
		ctx.fillStyle = C.text;
		ctx.textAlign = 'center';
		const step = Math.floor(n / 7) || 1;
		for (let i = 0; i < n; i += step) {
			const d = s[i].t;
			ctx.fillText(`${d.slice(4, 6)}/${d.slice(6, 8)}`, X(i), H - 4);
		}

		// hover crosshair (전체 높이)
		if (hv != null && hv >= 0 && hv < n) {
			ctx.strokeStyle = 'rgba(251,146,60,0.5)';
			ctx.setLineDash([3, 3]);
			ctx.lineWidth = 1;
			ctx.beginPath();
			ctx.moveTo(X(hv), padT);
			ctx.lineTo(X(hv), padT + priceH + subsBlock);
			ctx.stroke();
			ctx.setLineDash([]);
		}
	});

	function onMove(e: MouseEvent) {
		const cv = canvas;
		if (!cv) return;
		const r = cv.getBoundingClientRect();
		const plotW = dims.w - 48 - 4;
		const n = slice.length;
		const i = Math.floor((e.clientX - r.left - 4) / (plotW / n));
		hover = i >= 0 && i < n ? i : null;
	}
	const hv = $derived(hover != null && hover < slice.length ? slice[hover] : slice[slice.length - 1]);
</script>

<div class="chartWrap" bind:this={wrap} role="img" aria-label="price chart"
	onmousemove={onMove} onmouseleave={() => (hover = null)} style="height:{wrapH}px;min-height:300px;">
	<canvas bind:this={canvas}></canvas>
	{#if hv}
		<div class="ohlcTag">
			<span>{hv.t.slice(0, 4)}-{hv.t.slice(4, 6)}-{hv.t.slice(6, 8)}</span>
			<span>O <b>{fmtNum(hv.o)}</b></span>
			<span>H <b>{fmtNum(hv.h)}</b></span>
			<span>L <b>{fmtNum(hv.l)}</b></span>
			<span>C <b style="color:{hv.c >= hv.o ? C.up : C.dn}">{fmtNum(hv.c)}</b></span>
			<span>V <b>{fmtAbbr(hv.v)}</b></span>
		</div>
	{/if}
</div>
