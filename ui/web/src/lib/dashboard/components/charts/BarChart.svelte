<script>
	import { slotColor } from "../colorSlot.js";

	let { spec } = $props();

	const padding = { top: 18, right: 56, bottom: 28, left: 56 };
	let svgEl = $state(null);
	let width = $state(640);
	let height = $state(280);

	const categories = $derived(spec?.categories || []);
	const stacked = $derived(!!spec?.options?.stacked);
	const allSeries = $derived(spec?.series || []);
	const barSeries = $derived(allSeries.filter((s) => (s.type || "bar") === "bar"));
	const lineSeries = $derived(allSeries.filter((s) => s.type === "line"));

	function maxAbs(values) {
		const nums = values.filter((v) => typeof v === "number" && !Number.isNaN(v));
		return nums.length ? Math.max(...nums.map(Math.abs)) : 1;
	}

	const leftExtent = $derived.by(() => {
		const allVals = barSeries.flatMap((s) => s.data || []).concat(lineSeries.filter((s) => s.yAxis !== "right").flatMap((s) => s.data || []));
		const nums = allVals.filter((v) => typeof v === "number" && !Number.isNaN(v));
		if (!nums.length) return [0, 1];
		const mn = Math.min(0, ...nums);
		const mx = Math.max(0, ...nums);
		const span = (mx - mn) || 1;
		return [mn - span * 0.05, mx + span * 0.08];
	});
	const rightExtent = $derived.by(() => {
		const nums = lineSeries.filter((s) => s.yAxis === "right").flatMap((s) => s.data || []).filter((v) => typeof v === "number" && !Number.isNaN(v));
		if (!nums.length) return [0, 1];
		const mn = Math.min(...nums);
		const mx = Math.max(...nums);
		const span = (mx - mn) || 1;
		return [mn - span * 0.08, mx + span * 0.08];
	});

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

	function xBand(i, n) {
		const innerW = width - padding.left - padding.right;
		const bw = innerW / Math.max(1, n);
		return { x: padding.left + bw * i, w: bw };
	}
	function yPos(v, extent) {
		const [mn, mx] = extent;
		const innerH = height - padding.top - padding.bottom;
		if (mx === mn) return padding.top + innerH / 2;
		return padding.top + (1 - (v - mn) / (mx - mn)) * innerH;
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
		if (abs >= 1e12) return (v / 1e12).toFixed(1) + "조";
		if (abs >= 1e8) return (v / 1e8).toFixed(0) + "억";
		if (abs >= 100) return v.toFixed(0);
		if (abs >= 10) return v.toFixed(1);
		return v.toFixed(2);
	}

	function pathFor(data, extent) {
		const pts = [];
		for (let i = 0; i < data.length; i++) {
			const v = data[i];
			if (v == null || Number.isNaN(v)) continue;
			const { x, w } = xBand(i, data.length);
			pts.push(`${pts.length === 0 ? "M" : "L"}${x + w / 2} ${yPos(v, extent)}`);
		}
		return pts.join(" ");
	}
</script>

<div class="w-full h-full flex flex-col gap-2">
	<svg bind:this={svgEl} viewBox="0 0 {width} {height}" class="w-full flex-1" preserveAspectRatio="none">
		<line x1={padding.left} x2={width - padding.right} y1={yPos(0, leftExtent)} y2={yPos(0, leftExtent)} stroke="hsl(var(--border))" />
		{#each ticks(leftExtent) as t}
			<line x1={padding.left} x2={width - padding.right} y1={yPos(t, leftExtent)} y2={yPos(t, leftExtent)} stroke="hsl(var(--border))" stroke-dasharray="2 4" />
			<text x={padding.left - 6} y={yPos(t, leftExtent) + 3} text-anchor="end" class="text-[10px] fill-[hsl(var(--muted-foreground))]">{fmt(t)}</text>
		{/each}
		{#if lineSeries.some((s) => s.yAxis === "right")}
			{#each ticks(rightExtent) as t}
				<text x={width - padding.right + 6} y={yPos(t, rightExtent) + 3} text-anchor="start" class="text-[10px] fill-[hsl(var(--muted-foreground))]">{fmt(t)}</text>
			{/each}
		{/if}
		{#each categories as c, i}
			{@const { x, w } = xBand(i, categories.length)}
			<text x={x + w / 2} y={height - padding.bottom + 16} text-anchor="middle" class="text-[10px] fill-[hsl(var(--muted-foreground))]">{c}</text>
		{/each}
		<!-- bars -->
		{#each categories as _, i}
			{@const { x, w } = xBand(i, categories.length)}
			{#if stacked}
				{@const stack = barSeries.map((s) => s.data?.[i]).filter((v) => v != null)}
				{@const total = stack.reduce((a, b) => a + b, 0)}
				{@const bw = Math.max(2, w * 0.55)}
				{@const cx = x + (w - bw) / 2}
				{#each barSeries as s, si}
					{@const v = s.data?.[i]}
					{#if v != null && !Number.isNaN(v)}
						{@const acc = barSeries.slice(0, si).reduce((acc, ss) => acc + (ss.data?.[i] || 0), 0)}
						{@const y0 = yPos(acc, leftExtent)}
						{@const y1 = yPos(acc + v, leftExtent)}
						<rect x={cx} y={Math.min(y0, y1)} width={bw} height={Math.abs(y1 - y0)} fill={slotColor(s.colorSlot)} />
					{/if}
				{/each}
			{:else}
				{@const bSeriesCount = barSeries.length || 1}
				{@const bw = Math.max(2, (w * 0.78) / bSeriesCount)}
				{#each barSeries as s, si}
					{@const v = s.data?.[i]}
					{#if v != null && !Number.isNaN(v)}
						{@const bx = x + w * 0.11 + bw * si}
						{@const y0 = yPos(0, leftExtent)}
						{@const y1 = yPos(v, leftExtent)}
						<rect x={bx} y={Math.min(y0, y1)} width={bw} height={Math.max(1, Math.abs(y1 - y0))} fill={slotColor(s.colorSlot)} />
					{/if}
				{/each}
			{/if}
		{/each}
		<!-- line overlays -->
		{#each lineSeries as s}
			{@const ex = s.yAxis === "right" ? rightExtent : leftExtent}
			<path d={pathFor(s.data || [], ex)} fill="none" stroke={slotColor(s.colorSlot)} stroke-width="1.6" />
			{#each (s.data || []) as v, i}
				{#if v != null && !Number.isNaN(v)}
					{@const { x, w } = xBand(i, categories.length)}
					<circle cx={x + w / 2} cy={yPos(v, ex)} r="2.4" fill={slotColor(s.colorSlot)} />
				{/if}
			{/each}
		{/each}
	</svg>
	<div class="flex flex-wrap items-center gap-x-3 gap-y-1 text-[10px] text-muted-foreground px-2">
		{#each allSeries as s}
			<span class="inline-flex items-center gap-1">
				<span class="inline-block w-2.5 h-2.5 rounded-sm" style="background: {slotColor(s.colorSlot)}"></span>
				{s.label}
			</span>
		{/each}
	</div>
</div>
