<!--
	BarTrend — 시계열 막대 차트 (Editorial 톤).
	단일 series. positive/negative 색 분리.
-->
<script>
	import { isFiniteNum, fmtKrw, fmtPct, linearScale } from "./util.js";

	let {
		rows = [],
		xKey = "period",
		yKey = "value",
		label = "",
		height = 200,
		unit = "",
		format = null,
		colorPos = "var(--ed-text-2)",
		colorNeg = "var(--ed-down)",
	} = $props();

	const W = 800;
	const PAD = { top: 16, right: 24, bottom: 28, left: 56 };

	const fmt = $derived(format || (unit === "%" ? fmtPct : fmtKrw));
	const sortedRows = $derived([...rows].reverse());
	const labels = $derived(sortedRows.map((r) => String(r?.[xKey] ?? "")));
	const N = $derived(sortedRows.length);

	const yDomain = $derived.by(() => {
		const vals = sortedRows.map((r) => r?.[yKey]).filter(isFiniteNum);
		if (vals.length === 0) return [0, 1];
		const min = Math.min(...vals, 0);
		const max = Math.max(...vals, 0);
		const range = max - min || 1;
		return [min - range * 0.06, max + range * 0.1];
	});

	const xScale = $derived.by(() => {
		const innerW = W - PAD.left - PAD.right;
		const step = innerW / Math.max(1, N);
		return (i) => PAD.left + step * i + step * 0.15;
	});
	const barWidth = $derived.by(() => {
		const innerW = W - PAD.left - PAD.right;
		return (innerW / Math.max(1, N)) * 0.7;
	});
	const yScale = $derived(linearScale(yDomain, [height - PAD.bottom, PAD.top]));
	const y0 = $derived(yScale(0));

	const yTicks = $derived.by(() => {
		const [lo, hi] = yDomain;
		const step = (hi - lo) / 4;
		return [0, 1, 2, 3, 4].map((i) => lo + step * i);
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

		{#if yDomain[0] < 0 && yDomain[1] > 0}
			<line x1={PAD.left} x2={W - PAD.right} y1={y0} y2={y0} stroke="var(--ed-text-3)" stroke-width="0.5" />
		{/if}

		{#each sortedRows as r, i}
			{@const v = r?.[yKey]}
			{#if isFiniteNum(v)}
				{@const y = yScale(v)}
				{@const top = Math.min(y, y0)}
				{@const h = Math.abs(y - y0)}
				<rect x={xScale(i)} y={top} width={barWidth} height={h} fill={v >= 0 ? colorPos : colorNeg} opacity="0.85" />
			{/if}
		{/each}

		{#each xTickIndices as i}
			<text x={xScale(i) + barWidth / 2} y={height - 10} text-anchor="middle" font-size="9.5" fill="var(--ed-text-3)" font-family="var(--font-num)">
				{labels[i]}
			</text>
		{/each}
	</svg>
	{#if label}
		<div class="text-[10.5px] mt-1" style="color: var(--ed-text-2);">{label}</div>
	{/if}
</div>
