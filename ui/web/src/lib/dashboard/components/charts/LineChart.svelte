<script>
	import { slotColor } from "../colorSlot.js";

	let { spec } = $props();

	const padding = { top: 18, right: 56, bottom: 28, left: 56 };
	let svgEl = $state(null);
	let width = $state(640);
	let height = $state(280);

	const series = $derived(spec?.series || []);
	const categories = $derived(spec?.categories || []);

	function autoExtent(values) {
		const nums = values.filter((v) => typeof v === "number" && !Number.isNaN(v));
		if (!nums.length) return [0, 1];
		const mn = Math.min(...nums);
		const mx = Math.max(...nums);
		if (mn === mx) return [mn - 1, mx + 1];
		const span = mx - mn;
		return [mn - span * 0.08, mx + span * 0.08];
	}

	const leftSeries = $derived(series.filter((s) => s.yAxis !== "right"));
	const rightSeries = $derived(series.filter((s) => s.yAxis === "right"));
	const leftExtent = $derived(autoExtent(leftSeries.flatMap((s) => s.data || [])));
	const rightExtent = $derived(autoExtent(rightSeries.flatMap((s) => s.data || [])));

	$effect(() => {
		if (!svgEl) return;
		const ro = new ResizeObserver((entries) => {
			for (const e of entries) {
				width = Math.max(200, e.contentRect.width);
				height = Math.max(160, e.contentRect.height);
			}
		});
		ro.observe(svgEl);
		return () => ro.disconnect();
	});

	function xPos(i, n) {
		const innerW = width - padding.left - padding.right;
		if (n <= 1) return padding.left + innerW / 2;
		return padding.left + (i / (n - 1)) * innerW;
	}
	function yPos(v, extent) {
		const [mn, mx] = extent;
		const innerH = height - padding.top - padding.bottom;
		if (mx === mn) return padding.top + innerH / 2;
		return padding.top + (1 - (v - mn) / (mx - mn)) * innerH;
	}
	function pathFor(data, extent) {
		const pts = [];
		for (let i = 0; i < data.length; i++) {
			const v = data[i];
			if (v == null || Number.isNaN(v)) continue;
			pts.push(`${pts.length === 0 ? "M" : "L"}${xPos(i, data.length)} ${yPos(v, extent)}`);
		}
		return pts.join(" ");
	}

	function ticks(extent, count = 4) {
		const [mn, mx] = extent;
		const out = [];
		for (let i = 0; i <= count; i++) out.push(mn + ((mx - mn) * i) / count);
		return out;
	}

	function fmt(v) {
		if (v == null || Number.isNaN(v)) return "-";
		const abs = Math.abs(v);
		if (abs >= 100) return v.toFixed(0);
		if (abs >= 10) return v.toFixed(1);
		return v.toFixed(2);
	}
</script>

<div class="w-full h-full flex flex-col gap-2">
	<svg bind:this={svgEl} viewBox="0 0 {width} {height}" class="w-full flex-1" preserveAspectRatio="none">
		<!-- left axis ticks -->
		{#each ticks(leftExtent) as t}
			<line x1={padding.left} x2={width - padding.right} y1={yPos(t, leftExtent)} y2={yPos(t, leftExtent)} stroke="hsl(var(--border))" stroke-dasharray="2 4" />
			<text x={padding.left - 6} y={yPos(t, leftExtent) + 3} text-anchor="end" class="text-[10px] fill-[hsl(var(--muted-foreground))]">{fmt(t)}</text>
		{/each}
		<!-- right axis ticks -->
		{#if rightSeries.length}
			{#each ticks(rightExtent) as t}
				<text x={width - padding.right + 6} y={yPos(t, rightExtent) + 3} text-anchor="start" class="text-[10px] fill-[hsl(var(--muted-foreground))]">{fmt(t)}</text>
			{/each}
		{/if}
		<!-- x axis labels -->
		{#each categories as c, i}
			<text x={xPos(i, categories.length)} y={height - padding.bottom + 16} text-anchor="middle" class="text-[10px] fill-[hsl(var(--muted-foreground))]">{c}</text>
		{/each}
		<!-- series -->
		{#each series as s}
			{@const ex = s.yAxis === "right" ? rightExtent : leftExtent}
			<path d={pathFor(s.data || [], ex)} fill="none" stroke={slotColor(s.colorSlot)} stroke-width="1.6" />
			{#each (s.data || []) as v, i}
				{#if v != null && !Number.isNaN(v)}
					<circle cx={xPos(i, (s.data || []).length)} cy={yPos(v, ex)} r="2.4" fill={slotColor(s.colorSlot)} />
				{/if}
			{/each}
		{/each}
	</svg>
	<div class="flex flex-wrap items-center gap-x-3 gap-y-1 text-[10px] text-muted-foreground px-2">
		{#each series as s}
			<span class="inline-flex items-center gap-1">
				<span class="inline-block w-2.5 h-0.5 rounded-sm" style="background: {slotColor(s.colorSlot)}"></span>
				{s.label}
			</span>
		{/each}
	</div>
</div>
