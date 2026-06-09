<script lang="ts">
	import type { Candle } from '../data/priceSeries';
	import type { Lang } from '../data/types';
	import { sma, rsi, macd, bollinger } from '../data/indicators';
	import { fmtNum, fmtAbbr } from '../ui/helpers';

	interface Props {
		candles: Candle[];
		lang: Lang;
		period: '3M' | '5M' | '6M' | '1Y' | 'MAX';
		overlay: 'MA' | 'BB' | 'NONE';
		sub: 'VOL' | 'RSI' | 'MACD';
	}
	let { candles, lang, period, overlay, sub }: Props = $props();

	let wrap: HTMLDivElement | null = $state(null);
	let canvas: HTMLCanvasElement | null = $state(null);
	let hover = $state<number | null>(null);
	let dims = $state({ w: 800, h: 300 });

	const C = {
		up: '#d65b56', dn: '#5681c4', ma20: '#fb923c', ma60: '#60a5fa', bb: 'rgba(167,139,250,0.55)',
		grid: '#1b2130', axis: '#2a3142', text: '#a3a8b3', macdUp: 'rgba(214,91,86,0.6)', macdDn: 'rgba(86,129,196,0.6)'
	};
	const PERIOD_N: Record<string, number> = { '3M': 66, '5M': 110, '6M': 132, '1Y': 252, MAX: 100000 };

	$effect(() => {
		if (!wrap) return;
		const ro = new ResizeObserver((es) => {
			for (const e of es) {
				const cr = e.contentRect;
				dims = { w: Math.max(280, cr.width), h: Math.max(150, cr.height) };
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
		const sb = sub;
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

		const padR = 46;
		const padL = 4;
		const padT = 4;
		const subH = 30;
		const gap = 4;
		const xLblH = 12;
		const priceH = H - padT - subH - gap - xLblH;
		const plotW = W - padR - padL;
		const n = s.length;
		const closes = s.map((c) => c.c);

		const lo = Math.min(...s.map((c) => c.l));
		const hi = Math.max(...s.map((c) => c.h));
		const pad = (hi - lo) * 0.04 || 1;
		const yMin = lo - pad;
		const yMax = hi + pad;
		const Y = (v: number) => padT + priceH - ((v - yMin) / (yMax - yMin)) * priceH;
		const cw = plotW / n;
		const X = (i: number) => padL + i * cw + cw / 2;

		ctx.font = '8px "JetBrains Mono", monospace';
		ctx.textBaseline = 'middle';
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

		// Bollinger band fill (behind candles)
		if (ov === 'BB') {
			const bb = bollinger(closes, 20, 2);
			const drawBand = (arr: (number | null)[], col: string) => {
				ctx.strokeStyle = col;
				ctx.lineWidth = 1;
				ctx.beginPath();
				let st = false;
				arr.forEach((v, i) => {
					if (v == null) return;
					const x = X(i);
					const y = Y(v);
					st ? ctx.lineTo(x, y) : ((ctx.moveTo(x, y), (st = true)));
				});
				ctx.stroke();
			};
			drawBand(bb.upper, C.bb);
			drawBand(bb.lower, C.bb);
			drawBand(bb.mid, 'rgba(167,139,250,0.8)');
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

		// MA overlays
		if (ov === 'MA') {
			const drawLine = (arr: (number | null)[], color: string) => {
				ctx.strokeStyle = color;
				ctx.lineWidth = 1.2;
				ctx.beginPath();
				let st = false;
				arr.forEach((v, i) => {
					if (v == null) return;
					const x = X(i);
					const y = Y(v);
					st ? ctx.lineTo(x, y) : ((ctx.moveTo(x, y), (st = true)));
				});
				ctx.stroke();
			};
			drawLine(sma(closes, 20), C.ma20);
			drawLine(sma(closes, 60), C.ma60);
		}

		// sub pane
		const subTop = padT + priceH + gap;
		ctx.strokeStyle = C.grid;
		ctx.beginPath();
		ctx.moveTo(padL, subTop);
		ctx.lineTo(padL + plotW, subTop);
		ctx.stroke();
		if (sb === 'MACD') {
			const m = macd(closes);
			const all = m.line.concat(m.signal, m.hist).filter((v) => v != null);
			const mx = Math.max(...all.map(Math.abs)) || 1;
			const SY = (v: number) => subTop + subH / 2 - (v / mx) * (subH / 2 - 3);
			m.hist.forEach((v, i) => {
				const x = X(i);
				ctx.fillStyle = v >= 0 ? C.macdUp : C.macdDn;
				const y0 = SY(0);
				const y1 = SY(v);
				ctx.fillRect(x - Math.max(1, cw * 0.5) / 2, Math.min(y0, y1), Math.max(1, cw * 0.5), Math.abs(y1 - y0));
			});
			const dl = (arr: number[], col: string) => {
				ctx.strokeStyle = col;
				ctx.lineWidth = 1;
				ctx.beginPath();
				let st = false;
				arr.forEach((v, i) => {
					const x = X(i);
					const y = SY(v);
					st ? ctx.lineTo(x, y) : ((ctx.moveTo(x, y), (st = true)));
				});
				ctx.stroke();
			};
			dl(m.line, C.ma20);
			dl(m.signal, C.ma60);
			ctx.fillStyle = C.text;
			ctx.textAlign = 'left';
			ctx.fillText('MACD 12/26/9', padL + 2, subTop + 6);
		} else if (sb === 'RSI') {
			const r = rsi(closes, 14);
			const SY = (v: number) => subTop + subH - (v / 100) * subH;
			[30, 70].forEach((lv) => {
				ctx.strokeStyle = 'rgba(251,146,60,0.18)';
				ctx.beginPath();
				ctx.moveTo(padL, SY(lv));
				ctx.lineTo(padL + plotW, SY(lv));
				ctx.stroke();
			});
			ctx.strokeStyle = C.ma20;
			ctx.lineWidth = 1.1;
			ctx.beginPath();
			let st = false;
			r.forEach((v, i) => {
				if (v == null) return;
				const x = X(i);
				const y = SY(v);
				st ? ctx.lineTo(x, y) : ((ctx.moveTo(x, y), (st = true)));
			});
			ctx.stroke();
			ctx.fillStyle = C.text;
			ctx.textAlign = 'left';
			ctx.fillText('RSI 14', padL + 2, subTop + 6);
		} else {
			const vMax = Math.max(...s.map((c) => c.v), 1);
			s.forEach((c, i) => {
				const x = X(i);
				const up = c.c >= c.o;
				const h = (c.v / vMax) * subH;
				ctx.fillStyle = up ? 'rgba(214,91,86,0.45)' : 'rgba(86,129,196,0.45)';
				ctx.fillRect(x - Math.max(1, cw * 0.62) / 2, subTop + subH - h, Math.max(1, cw * 0.62), h);
			});
			ctx.fillStyle = C.text;
			ctx.textAlign = 'left';
			ctx.fillText('VOL', padL + 2, subTop + 6);
		}

		// x labels
		ctx.fillStyle = C.text;
		ctx.textAlign = 'center';
		const step = Math.floor(n / 6) || 1;
		for (let i = 0; i < n; i += step) {
			const d = s[i].t;
			ctx.fillText(`${d.slice(4, 6)}/${d.slice(6, 8)}`, X(i), H - 4);
		}

		// hover crosshair
		if (hv != null && hv >= 0 && hv < n) {
			ctx.strokeStyle = 'rgba(251,146,60,0.5)';
			ctx.setLineDash([3, 3]);
			ctx.lineWidth = 1;
			ctx.beginPath();
			ctx.moveTo(X(hv), padT);
			ctx.lineTo(X(hv), padT + priceH);
			ctx.stroke();
			ctx.setLineDash([]);
		}
	});

	function onMove(e: MouseEvent) {
		const cv = canvas;
		if (!cv) return;
		const r = cv.getBoundingClientRect();
		const plotW = dims.w - 46 - 4;
		const n = slice.length;
		const i = Math.floor((e.clientX - r.left - 4) / (plotW / n));
		hover = i >= 0 && i < n ? i : null;
	}
	const hv = $derived(hover != null && hover < slice.length ? slice[hover] : slice[slice.length - 1]);
</script>

<div class="chartWrap" bind:this={wrap} role="img" aria-label="price chart"
	onmousemove={onMove} onmouseleave={() => (hover = null)} style="height:300px;min-height:280px;">
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
