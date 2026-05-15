<!--
	StackedBarTrend — 시계열 stacked bar (segments / CCC dso-dio-dpo / 등).
	props:
	  rows: [{ [xKey], [seriesKey1]: number, [seriesKey2]: number, ... }]
	  xKey: "period"
	  series: [{ key, label, color }]
-->
<script>
	import { isFiniteNum, fmtKrw, fmtPct, linearScale } from "./util.js";

	let {
		rows = [],
		xKey = "period",
		series = [],
		height = 240,
		unit = "",
		format = null,
	} = $props();

	const W = 800;
	const PAD = { top: 18, right: 24, bottom: 28, left: 60 };

	const fmt = $derived(format || (unit === "%" ? fmtPct : fmtKrw));
	const sortedRows = $derived([...rows].reverse());
	const labels = $derived(sortedRows.map((r) => String(r?.[xKey] ?? "")));
	const N = $derived(sortedRows.length);

	const rowTotals = $derived(
		sortedRows.map((r) => {
			let sum = 0;
			for (const s of series) {
				const v = r?.[s.key];
				if (isFiniteNum(v) && v > 0) sum += v;
			}
			return sum;
		})
	);
	const yMax = $derived(Math.max(1, ...rowTotals) * 1.1);
	const yScale = $derived(linearScale([0, yMax], [height - PAD.bottom, PAD.top]));

	const innerW = $derived(W - PAD.left - PAD.right);
	const stepW = $derived(innerW / Math.max(1, N));
	const barW = $derived(stepW * 0.68);
	function xLeft(i) {
		return PAD.left + stepW * i + (stepW - barW) / 2;
	}

	const yTicks = $derived.by(() => {
		const step = yMax / 4;
		return [0, 1, 2, 3, 4].map((i) => step * i);
	});

	const xTickIndices = $derived.by(() => {
		if (N <= 8) return sortedRows.map((_, i) => i);
		const step = Math.ceil(N / 8);
		const arr = [];
		for (let i = 0; i < N; i += step) arr.push(i);
		if (arr[arr.length - 1] !== N - 1) arr.push(N - 1);
		return arr;
	});
</script>

<div class="w-full">
	<svg viewBox="0 0 {W} {height}" preserveAspectRatio="xMidYMid meet" class="w-full block">
		{#each yTicks as t}
			{@const y = yScale(t)}
			<line x1={PAD.left} x2={W - PAD.right} y1={y} y2={y} stroke="var(--ed-line)" stroke-width="0.5" />
			<text x={PAD.left - 6} y={y + 3.5} text-anchor="end" font-size="9.5" fill="var(--ed-text-3)" font-family="var(--font-num)">
				{fmt(t)}
			</text>
		{/each}

		{#each sortedRows as r, i}
			{@const x = xLeft(i)}
			{@const stacks = (() => {
				let acc = 0;
				return series.map((s) => {
					const v = r?.[s.key];
					const valid = isFiniteNum(v) && v > 0;
					const seg = valid ? { start: acc, end: acc + v, ...s } : null;
					if (valid) acc += v;
					return seg;
				}).filter(Boolean);
			})()}
			{#each stacks as seg}
				{@const yTop = yScale(seg.end)}
				{@const yBot = yScale(seg.start)}
				<rect x={x} y={yTop} width={barW} height={Math.max(0.5, yBot - yTop)} fill={seg.color} opacity="0.86" />
			{/each}
		{/each}

		{#each xTickIndices as i}
			<text x={xLeft(i) + barW / 2} y={height - 10} text-anchor="middle" font-size="9.5" fill="var(--ed-text-3)" font-family="var(--font-num)">
				{labels[i]}
			</text>
		{/each}
	</svg>

	<div class="flex flex-wrap items-center gap-x-4 gap-y-1 mt-1 text-[10.5px]" style="color: var(--ed-text-2);">
		{#each series as s}
			<div class="flex items-center gap-1.5">
				<span class="inline-block w-2.5 h-2.5 rounded-sm" style="background: {s.color};"></span>
				<span>{s.label || s.key}</span>
			</div>
		{/each}
	</div>
</div>
