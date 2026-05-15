<!--
	LineTrend — 시계열 라인 차트 (Editorial 톤).
	N series, 같은 X축 (period). null gap 처리. 마지막 점 dot + label.
	props:
	  rows: Array<{ [xKey]: string, [...numeric] }>
	  xKey: "period"
	  series: Array<{ key, label, color, format? }>
	  height: 220
	  unit: "" | "%" | "억" 등 (Y축 표시)
-->
<script>
	import { isFiniteNum, fmtKrw, fmtPct, linearScale } from "./util.js";

	let {
		rows = [],
		xKey = "period",
		series = [],
		height = 220,
		unit = "",
		format = null,
	} = $props();

	const W = 800;
	const PAD = { top: 18, right: 60, bottom: 28, left: 56 };

	const fmt = $derived(format || (unit === "%" ? fmtPct : fmtKrw));
	const sortedRows = $derived([...rows].reverse()); // dartlab response: 최신→과거. 차트: 과거→최신.
	const labels = $derived(sortedRows.map((r) => String(r?.[xKey] ?? "")));
	const N = $derived(sortedRows.length);

	const yDomain = $derived.by(() => {
		const vals = [];
		for (const r of sortedRows) {
			for (const s of series) {
				const v = r?.[s.key];
				if (isFiniteNum(v)) vals.push(v);
			}
		}
		if (vals.length === 0) return [0, 1];
		const min = Math.min(...vals, 0);
		const max = Math.max(...vals, 0);
		const range = max - min || 1;
		return [min - range * 0.06, max + range * 0.08];
	});

	const xScale = $derived(linearScale([0, Math.max(1, N - 1)], [PAD.left, W - PAD.right]));
	const yScale = $derived(linearScale(yDomain, [height - PAD.bottom, PAD.top]));

	function pathFor(seriesKey) {
		let d = "";
		let pen = false;
		sortedRows.forEach((r, i) => {
			const v = r?.[seriesKey];
			if (!isFiniteNum(v)) {
				pen = false;
				return;
			}
			const x = xScale(i);
			const y = yScale(v);
			d += pen ? ` L${x.toFixed(1)} ${y.toFixed(1)}` : `M${x.toFixed(1)} ${y.toFixed(1)}`;
			pen = true;
		});
		return d;
	}

	function lastFinite(seriesKey) {
		for (let i = sortedRows.length - 1; i >= 0; i--) {
			const v = sortedRows[i]?.[seriesKey];
			if (isFiniteNum(v)) return { i, v };
		}
		return null;
	}

	// Y축 ticks — 4 ~ 5개. nice round.
	const yTicks = $derived.by(() => {
		const [lo, hi] = yDomain;
		const step = (hi - lo) / 4;
		return [0, 1, 2, 3, 4].map((i) => lo + step * i);
	});

	// X축 ticks — 5개 까지만 (period 라벨이 많을 때 thin out).
	const xTickIndices = $derived.by(() => {
		if (N <= 6) return sortedRows.map((_, i) => i);
		const step = Math.ceil(N / 6);
		const arr = [];
		for (let i = 0; i < N; i += step) arr.push(i);
		if (arr[arr.length - 1] !== N - 1) arr.push(N - 1);
		return arr;
	});
</script>

<div class="w-full">
	<svg viewBox="0 0 {W} {height}" preserveAspectRatio="xMidYMid meet" class="w-full block">
		<!-- Y gridlines + ticks -->
		{#each yTicks as t, ti}
			{@const y = yScale(t)}
			<line x1={PAD.left} x2={W - PAD.right} y1={y} y2={y} stroke="var(--ed-line)" stroke-width="0.5" />
			<text x={PAD.left - 6} y={y + 3.5} text-anchor="end" font-size="9.5" fill="var(--ed-text-3)" font-family="var(--font-num)">
				{fmt(t)}
			</text>
		{/each}

		<!-- Zero line (when domain crosses 0) -->
		{#if yDomain[0] < 0 && yDomain[1] > 0}
			{@const y0 = yScale(0)}
			<line x1={PAD.left} x2={W - PAD.right} y1={y0} y2={y0} stroke="var(--ed-text-3)" stroke-width="0.5" stroke-dasharray="2 2" opacity="0.5" />
		{/if}

		<!-- X ticks -->
		{#each xTickIndices as i}
			<text x={xScale(i)} y={height - 10} text-anchor="middle" font-size="9.5" fill="var(--ed-text-3)" font-family="var(--font-num)">
				{labels[i]}
			</text>
		{/each}

		<!-- Series -->
		{#each series as s, si}
			{@const d = pathFor(s.key)}
			<path d={d} fill="none" stroke={s.color} stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round" />
			{#each sortedRows as r, ri}
				{#if isFiniteNum(r?.[s.key])}
					<circle cx={xScale(ri)} cy={yScale(r[s.key])} r="1.6" fill={s.color} />
				{/if}
			{/each}
			{@const last = lastFinite(s.key)}
			{#if last}
				<circle cx={xScale(last.i)} cy={yScale(last.v)} r="2.6" fill={s.color} />
				<text x={xScale(last.i) + 5} y={yScale(last.v) + 3} font-size="9.5" fill={s.color} font-family="var(--font-num)" font-weight="500">
					{fmt(last.v)}
				</text>
			{/if}
		{/each}
	</svg>

	<!-- Legend -->
	<div class="flex flex-wrap items-center gap-x-4 gap-y-1 mt-1 text-[10.5px]" style="color: var(--ed-text-2);">
		{#each series as s}
			<div class="flex items-center gap-1.5">
				<span class="inline-block w-2.5 h-[2px]" style="background: {s.color};"></span>
				<span>{s.label || s.key}</span>
			</div>
		{/each}
	</div>
</div>
