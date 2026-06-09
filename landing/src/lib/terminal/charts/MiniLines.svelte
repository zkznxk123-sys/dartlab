<script lang="ts">
	import type { Num } from '../data/types';
	import { fmtNum } from '../ui/helpers';

	interface Series {
		label: string;
		color: string;
		data: Num[];
		unit?: string;
	}
	interface Props {
		series: Series[];
		periods: string[];
		height?: number;
		refLines?: number[];
	}
	let { series, periods, height = 64, refLines = [] }: Props = $props();
	let wrap: HTMLDivElement | null = $state(null);
	let canvas: HTMLCanvasElement | null = $state(null);
	let w = $state(220);

	$effect(() => {
		if (!wrap) return;
		const ro = new ResizeObserver((es) => {
			for (const e of es) w = Math.max(140, e.contentRect.width);
		});
		ro.observe(wrap);
		return () => ro.disconnect();
	});

	$effect(() => {
		const cv = canvas;
		if (!cv) return;
		const ss = series;
		const rl = refLines;
		const dpr = window.devicePixelRatio || 1;
		const W = w;
		const H = height;
		cv.width = W * dpr;
		cv.height = H * dpr;
		cv.style.width = W + 'px';
		cv.style.height = H + 'px';
		const ctx = cv.getContext('2d');
		if (!ctx) return;
		ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
		ctx.clearRect(0, 0, W, H);
		const padR = 4;
		const padL = 4;
		const padT = 4;
		const padB = 10;
		const plotW = W - padL - padR;
		const plotH = H - padT - padB;
		const all = ss.flatMap((s) => s.data).concat(rl).filter((v): v is number => v != null);
		if (!all.length) return;
		let lo = Math.min(...all);
		let hi = Math.max(...all);
		if (lo === hi) {
			lo -= 1;
			hi += 1;
		}
		const pad = (hi - lo) * 0.1;
		lo -= pad;
		hi += pad;
		const n = periods.length;
		const X = (i: number) => padL + (n <= 1 ? plotW / 2 : (i / (n - 1)) * plotW);
		const Y = (v: number) => padT + plotH - ((v - lo) / (hi - lo)) * plotH;
		// ref lines
		rl.forEach((v) => {
			ctx.strokeStyle = 'rgba(255,255,255,0.08)';
			ctx.setLineDash([2, 2]);
			ctx.beginPath();
			ctx.moveTo(padL, Y(v));
			ctx.lineTo(padL + plotW, Y(v));
			ctx.stroke();
			ctx.setLineDash([]);
		});
		// series lines
		ss.forEach((s) => {
			ctx.strokeStyle = s.color;
			ctx.lineWidth = 1.3;
			ctx.beginPath();
			let st = false;
			s.data.forEach((v, i) => {
				if (v == null) return;
				const x = X(i);
				const y = Y(v);
				st ? ctx.lineTo(x, y) : ((ctx.moveTo(x, y), (st = true)));
			});
			ctx.stroke();
			// last dot
			for (let i = s.data.length - 1; i >= 0; i--) {
				if (s.data[i] != null) {
					ctx.fillStyle = s.color;
					ctx.beginPath();
					ctx.arc(X(i), Y(s.data[i]!), 1.8, 0, 7);
					ctx.fill();
					break;
				}
			}
		});
		// x labels (first + last)
		ctx.fillStyle = '#6b7280';
		ctx.font = '7.5px "JetBrains Mono", monospace';
		ctx.textBaseline = 'alphabetic';
		ctx.textAlign = 'left';
		if (periods[0]) ctx.fillText(periods[0], padL, H - 2);
		ctx.textAlign = 'right';
		if (periods[n - 1]) ctx.fillText(periods[n - 1], padL + plotW, H - 2);
	});
	const lastVal = (d: Num[]): Num => {
		for (let i = d.length - 1; i >= 0; i--) if (d[i] != null) return d[i];
		return null;
	};
</script>

<div class="mlWrap" bind:this={wrap}>
	<canvas bind:this={canvas}></canvas>
	<div class="mlLegend">
		{#each series as s (s.label)}
			<span class="mlItem"><span class="mlDot" style={`background:${s.color}`}></span>{s.label} <b class="mono">{lastVal(s.data) == null ? '—' : fmtNum(lastVal(s.data), 1) + (s.unit || '')}</b></span>
		{/each}
	</div>
</div>
