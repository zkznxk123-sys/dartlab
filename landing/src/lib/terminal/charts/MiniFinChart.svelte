<script lang="ts">
	// 밀집 재무 미니차트 — small multiple. 막대+선·이중축·signed·stacked·refLine.
	// 호버 시 크로스헤어 + 기간·각 시리즈 값 툴팁 (뭔 상태인지). 정보밀도 우선.
	import type { FinCard, Num } from '../data/terminalFinance';

	interface Props {
		card: FinCard;
		periods: string[];
	}
	let { card, periods }: Props = $props();

	const W = 300;
	const H = 100;
	const PADT = 5;
	const PADB = 12;
	const plotH = H - PADT - PADB;

	const fin = (v: Num): v is number => typeof v === 'number' && Number.isFinite(v);
	const n = $derived(periods.length);

	const leftSeries = $derived(card.series.filter((s) => s.axis !== 'r'));
	const rightSeries = $derived(card.series.filter((s) => s.axis === 'r'));
	const barSeries = $derived(leftSeries.filter((s) => s.type === 'bar'));
	const leftLineSeries = $derived(leftSeries.filter((s) => s.type === 'line'));

	function extent(vals: number[], incl0: boolean): [number, number] {
		const arr = incl0 ? [...vals, 0] : vals;
		if (!arr.length) return [0, 1];
		let lo = Math.min(...arr);
		let hi = Math.max(...arr);
		if (lo === hi) { hi = lo + Math.abs(lo || 1); lo = Math.min(lo, 0); }
		const pad = (hi - lo) * 0.08;
		return [lo - (lo < 0 ? pad : 0), hi + pad];
	}

	const leftExt = $derived.by<[number, number]>(() => {
		const vals: number[] = [];
		if (card.stacked) {
			for (let i = 0; i < n; i++) {
				let s = 0;
				for (const b of barSeries) { const v = b.data[i]; if (fin(v)) s += v; }
				vals.push(s);
			}
		} else {
			for (const b of barSeries) for (const v of b.data) if (fin(v)) vals.push(v);
		}
		for (const l of leftLineSeries) for (const v of l.data) if (fin(v)) vals.push(v);
		return extent(vals, true);
	});
	const rightExt = $derived.by<[number, number]>(() => {
		const vals: number[] = [];
		for (const s of rightSeries) for (const v of s.data) if (fin(v)) vals.push(v);
		return extent(vals, true);
	});

	const x = (i: number) => (n <= 1 ? W / 2 : 4 + (i / (n - 1)) * (W - 8));
	const yOf = (v: number, [lo, hi]: [number, number]) => PADT + plotH - ((v - lo) / (hi - lo || 1)) * plotH;
	const yL = (v: number) => yOf(v, leftExt);
	const yR = (v: number) => yOf(v, rightExt);

	const slotW = $derived(n > 0 ? (W - 8) / n : W);
	const groupW = $derived(slotW * 0.76);
	const barW = $derived(card.stacked || barSeries.length <= 1 ? groupW : groupW / barSeries.length);

	function linePath(data: Num[], yfn: (v: number) => number): string {
		let d = '';
		let pen = false;
		data.forEach((v, i) => {
			if (!fin(v)) { pen = false; return; }
			d += `${pen ? 'L' : 'M'}${x(i).toFixed(1)},${yfn(v).toFixed(1)} `;
			pen = true;
		});
		return d.trim();
	}

	const primary = $derived(card.series[0]);
	const latest = $derived.by(() => {
		const d = primary?.data ?? [];
		for (let i = d.length - 1; i >= 0; i--) if (fin(d[i])) return { v: d[i] as number, i };
		return null;
	});
	const fmtVal = (v: number) => {
		const a = Math.abs(v);
		if (card.unit === '조' || card.unit === '배') return v.toFixed(2);
		if (a >= 100) return v.toFixed(0);
		return v.toFixed(1);
	};
	const zeroY = $derived(leftExt[0] < 0 && leftExt[1] > 0 ? yL(0) : null);

	// ── 호버 ──
	let svgEl = $state<SVGSVGElement | null>(null);
	let hoverI = $state(-1);
	function onMove(e: MouseEvent) {
		if (!svgEl || n === 0) return;
		const r = svgEl.getBoundingClientRect();
		const frac = (e.clientX - r.left) / r.width;
		hoverI = Math.max(0, Math.min(n - 1, Math.round(frac * (n - 1))));
	}
	function onLeave() { hoverI = -1; }
	const fmtTip = (v: number) => { const a = Math.abs(v); return a >= 100 ? v.toFixed(0) : a >= 10 ? v.toFixed(1) : v.toFixed(2); };
	const headVal = $derived(hoverI >= 0 && primary && fin(primary.data[hoverI]) ? (primary.data[hoverI] as number) : latest?.v ?? null);
</script>

<div class="mfc">
	<div class="mfcHead">
		<span class="mfcTitle">{card.title}</span>
		<span class="mfcDots">
			{#each card.series as s (s.name)}<i style={`background:${s.color}`} title={s.name}></i>{/each}
		</span>
		{#if headVal != null}
			<b class="mfcVal mono">{fmtVal(headVal)}<span class="mfcUnit">{card.unit}</span></b>
		{/if}
	</div>
	<div class="mfcPlot">
		<svg bind:this={svgEl} viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none" role="img" aria-label={card.title}
			onmousemove={onMove} onmouseleave={onLeave}>
			{#each card.refLines ?? [] as rl (rl)}
				{#if rl >= leftExt[0] && rl <= leftExt[1]}
					<line x1="0" x2={W} y1={yL(rl)} y2={yL(rl)} stroke="#475569" stroke-width="0.6" stroke-dasharray="3 3" />
				{/if}
			{/each}
			{#if zeroY != null}<line x1="0" x2={W} y1={zeroY} y2={zeroY} stroke="#3a4660" stroke-width="0.7" />{/if}
			{#if hoverI >= 0}<line x1={x(hoverI)} x2={x(hoverI)} y1={PADT - 3} y2={H - PADB + 2} stroke="#94a3b8" stroke-width="0.8" stroke-dasharray="2 2" />{/if}
			{#each periods as _p, i (i)}
				{#if card.stacked}
					{#each barSeries as b, bi (b.name)}
						{@const stackBelow = barSeries.slice(0, bi).reduce((a, s) => a + (fin(s.data[i]) ? (s.data[i] as number) : 0), 0)}
						{@const v = b.data[i]}
						{#if fin(v) && v > 0}
							{@const y0 = yL(stackBelow)}
							{@const y1 = yL(stackBelow + v)}
							<rect x={x(i) - barW / 2} y={Math.min(y0, y1)} width={barW} height={Math.max(0.5, Math.abs(y1 - y0))} fill={b.color} fill-opacity={hoverI < 0 || hoverI === i ? 0.9 : 0.42} />
						{/if}
					{/each}
				{:else}
					{#each barSeries as b, bi (b.name)}
						{@const v = b.data[i]}
						{#if fin(v)}
							{@const base = zeroY != null ? zeroY : yL(leftExt[0])}
							{@const yv = yL(v)}
							{@const gx = x(i) - groupW / 2 + bi * barW + barW / 2}
							<rect x={gx - barW / 2} y={Math.min(base, yv)} width={Math.max(0.6, barW - 0.6)} height={Math.max(0.5, Math.abs(yv - base))} fill={b.color} fill-opacity={hoverI < 0 || hoverI === i ? 0.88 : 0.4} />
						{/if}
					{/each}
				{/if}
			{/each}
			{#each leftLineSeries as l (l.name)}
				<path d={linePath(l.data, yL)} fill="none" stroke={l.color} stroke-width="1.5" />
			{/each}
			{#each rightSeries as r (r.name)}
				<path d={linePath(r.data, yR)} fill="none" stroke={r.color} stroke-width="1.5" />
			{/each}
			{#if hoverI >= 0}
				{#each card.series as s (s.name)}
					{@const v = s.data[hoverI]}
					{#if fin(v)}<circle cx={x(hoverI)} cy={(s.axis === 'r' ? yR : yL)(v)} r="2.2" fill={s.color} stroke="#0b1220" stroke-width="0.6" />{/if}
				{/each}
			{/if}
		</svg>
		{#if hoverI >= 0}
			<div class="mfcTip">
				<span class="mfcTipP mono">{periods[hoverI]}</span>
				{#each card.series as s (s.name)}
					{@const v = s.data[hoverI]}
					<span class="mfcTipS"><i style={`background:${s.color}`}></i>{fin(v) ? fmtTip(v as number) : '—'}</span>
				{/each}
			</div>
		{/if}
	</div>
	<div class="mfcAxis mono"><span>{periods[0] ?? ''}</span><span>{periods[periods.length - 1] ?? ''}</span></div>
</div>
