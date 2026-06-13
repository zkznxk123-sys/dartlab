<script lang="ts">
	import type { Lang, TrendSeries } from '../lib/types';
	import { fmtNum } from '../ui/helpers';

	interface Props {
		trend: TrendSeries;
		lang: Lang;
	}
	let { trend, lang }: Props = $props();
	let wrap: HTMLDivElement | null = $state(null);
	let canvas: HTMLCanvasElement | null = $state(null);
	let hover = $state<number | null>(null);
	let dims = $state({ w: 800, h: 136 });

	$effect(() => {
		if (!wrap) return;
		const ro = new ResizeObserver((es) => {
			for (const e of es) {
				const cr = e.contentRect;
				dims = { w: Math.max(280, cr.width), h: Math.max(120, cr.height) };
			}
		});
		ro.observe(wrap);
		return () => ro.disconnect();
	});

	const C = {
		rev: '#fb923c', revDim: 'rgba(251,146,60,0.30)', op: '#60a5fa',
		margin: '#34d399', grid: '#1b2130', axis: '#2a3142', text: '#a3a8b3'
	};

	$effect(() => {
		const cv = canvas;
		if (!cv) return;
		const t = trend;
		const hv = hover;
		const dpr = window.devicePixelRatio || 1;
		const W = dims.w;
		const H = dims.h;
		cv.width = W * dpr;
		cv.height = H * dpr;
		cv.style.width = W + 'px';
		cv.style.height = H + 'px';
		const ctx = cv.getContext('2d');
		if (!ctx) return;
		ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
		ctx.clearRect(0, 0, W, H);

		const padR = 40;
		const padL = 38;
		const padT = 16;
		const padB = 16;
		const plotW = W - padR - padL;
		const plotH = H - padT - padB;
		const n = t.periods.length;
		if (!n) return;

		const sales = t.sales;
		const op = t.op;
		const margins = t.opMargin;
		const maxV = Math.max(1, ...sales.map((v) => (v == null ? 0 : v)), ...op.map((v) => (v == null ? 0 : Math.abs(v))));
		const minV = Math.min(0, ...op.map((v) => (v == null ? 0 : v)));
		const Y = (v: number) => padT + plotH - ((v - minV) / (maxV - minV)) * plotH;
		const slot = plotW / n;
		const X = (i: number) => padL + i * slot + slot / 2;

		// y grid (left, KRW)
		ctx.font = '8px "JetBrains Mono", monospace';
		ctx.textBaseline = 'middle';
		const ticks = 3;
		for (let k = 0; k <= ticks; k++) {
			const v = minV + ((maxV - minV) * k) / ticks;
			const y = Y(v);
			ctx.strokeStyle = C.grid;
			ctx.lineWidth = 1;
			ctx.beginPath();
			ctx.moveTo(padL, y);
			ctx.lineTo(padL + plotW, y);
			ctx.stroke();
			ctx.fillStyle = C.text;
			ctx.textAlign = 'right';
			ctx.fillText(fmtNum(v, 0), padL - 3, y);
		}
		// zero line emphasis
		ctx.strokeStyle = C.axis;
		ctx.beginPath();
		ctx.moveTo(padL, Y(0));
		ctx.lineTo(padL + plotW, Y(0));
		ctx.stroke();

		// margin axis (right) 0..maxMargin
		const mAbs = Math.max(1, ...margins.map((m) => (m == null ? 0 : Math.abs(m))));
		const MY = (m: number) => padT + plotH / 2 - (m / mAbs) * (plotH / 2 - 2);

		// bars: revenue (back) + op (front narrower)
		const bwR = Math.max(2, slot * 0.62);
		const bwO = Math.max(1, slot * 0.32);
		t.periods.forEach((_, i) => {
			const x = X(i);
			const s = sales[i];
			if (s != null) {
				const y = Y(Math.max(0, s));
				ctx.fillStyle = i === hv ? C.rev : C.revDim;
				ctx.fillRect(x - bwR / 2, y, bwR, Y(0) - y);
			}
			const o = op[i];
			if (o != null) {
				const y = Y(Math.max(0, o));
				const y0 = Y(Math.min(0, o));
				ctx.fillStyle = o >= 0 ? C.op : '#1d64dc';
				ctx.fillRect(x - bwO / 2, Math.min(y, Y(0)), bwO, Math.abs(y0 - y) || Math.abs(Y(0) - y));
			}
		});

		// opMargin line (right axis)
		ctx.strokeStyle = C.margin;
		ctx.lineWidth = 1.4;
		ctx.beginPath();
		let started = false;
		margins.forEach((m, i) => {
			if (m == null) return;
			const x = X(i);
			const y = MY(m);
			started ? ctx.lineTo(x, y) : ((ctx.moveTo(x, y), (started = true)));
		});
		ctx.stroke();
		margins.forEach((m, i) => {
			if (m == null) return;
			ctx.fillStyle = C.margin;
			ctx.beginPath();
			ctx.arc(X(i), MY(m), 1.6, 0, 7);
			ctx.fill();
		});

		// x labels (every step)
		ctx.fillStyle = C.text;
		ctx.font = '8px "JetBrains Mono", monospace';
		ctx.textAlign = 'center';
		const step = Math.ceil(n / (t.freq === 'quarter' ? 7 : n)) || 1;
		t.periods.forEach((p, i) => {
			if (i % step === 0 || i === n - 1) ctx.fillText(p, X(i), H - 5);
		});

		// hover crosshair
		if (hv != null && hv >= 0 && hv < n) {
			ctx.strokeStyle = 'rgba(251,146,60,0.5)';
			ctx.setLineDash([3, 3]);
			ctx.beginPath();
			ctx.moveTo(X(hv), padT);
			ctx.lineTo(X(hv), padT + plotH);
			ctx.stroke();
			ctx.setLineDash([]);
		}
	});

	function onMove(e: MouseEvent) {
		const cv = canvas;
		if (!cv) return;
		const r = cv.getBoundingClientRect();
		const padL = 38;
		const padR = 40;
		const plotW = dims.w - padL - padR;
		const n = trend.periods.length;
		const i = Math.floor((e.clientX - r.left - padL) / (plotW / n));
		hover = i >= 0 && i < n ? i : null;
	}
	const hv = $derived(hover != null ? hover : trend.periods.length - 1);
	const unit = $derived(lang === 'en' ? 'T KRW' : '조 KRW');
</script>

<div class="chartWrap" bind:this={wrap} role="img" aria-label="financial trend"
	onmousemove={onMove} onmouseleave={() => (hover = null)}>
	<canvas bind:this={canvas}></canvas>
	{#if trend.periods[hv]}
		<div class="ohlcTag">
			<span>{trend.periods[hv]}</span>
			<span>{lang === 'en' ? 'REV' : '매출'} <b>{fmtNum(trend.sales[hv], 1)}</b></span>
			<span>{lang === 'en' ? 'OP' : '영업이익'} <b>{fmtNum(trend.op[hv], 1)}</b></span>
			<span>{lang === 'en' ? 'OPM' : '이익률'} <b style="color:#34d399">{trend.opMargin[hv] == null ? '—' : trend.opMargin[hv]!.toFixed(1) + '%'}</b></span>
		</div>
	{/if}
	<div class="legendTag">
		<span style="color:#fb923c">■ {lang === 'en' ? 'Revenue' : '매출'}</span>
		<span style="color:#60a5fa">■ {lang === 'en' ? 'Op income' : '영업이익'}</span>
		<span style="color:#34d399">━ {lang === 'en' ? 'OP margin' : '영업이익률'}</span>
		<span class="dim">{unit}</span>
	</div>
</div>
