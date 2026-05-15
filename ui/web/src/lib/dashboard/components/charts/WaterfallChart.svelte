<script>
	import { slotColor } from "../colorSlot.js";

	let { spec } = $props();

	const padding = { top: 18, right: 24, bottom: 30, left: 56 };
	let svgEl = $state(null);
	let width = $state(640);
	let height = $state(280);

	const series = $derived(spec?.series || []);

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

	const bars = $derived.by(() => {
		let acc = 0;
		const out = [];
		for (const s of series) {
			const m = s.measure || "relative";
			const v = typeof s.value === "number" ? s.value : 0;
			let y0, y1, top, bot;
			if (m === "absolute" || m === "total") {
				y0 = 0;
				y1 = v;
				top = v;
				bot = 0;
				acc = v;
			} else {
				y0 = acc;
				y1 = acc + v;
				top = Math.max(y0, y1);
				bot = Math.min(y0, y1);
				acc = y1;
			}
			out.push({ label: s.label, color: slotColor(s.colorSlot), top, bot, measure: m, value: v });
		}
		return out;
	});

	const extent = $derived.by(() => {
		const tops = bars.map((b) => b.top);
		const bots = bars.map((b) => b.bot);
		const mn = Math.min(0, ...bots);
		const mx = Math.max(0, ...tops);
		const span = (mx - mn) || 1;
		return [mn - span * 0.05, mx + span * 0.08];
	});

	function xBand(i, n) {
		const innerW = width - padding.left - padding.right;
		const bw = innerW / Math.max(1, n);
		return { x: padding.left + bw * i, w: bw };
	}
	function yPos(v) {
		const [mn, mx] = extent;
		const innerH = height - padding.top - padding.bottom;
		if (mx === mn) return padding.top + innerH / 2;
		return padding.top + (1 - (v - mn) / (mx - mn)) * innerH;
	}
	function ticks(count = 4) {
		const [mn, mx] = extent;
		const out = [];
		for (let i = 0; i <= count; i++) out.push(mn + ((mx - mn) * i) / count);
		return out;
	}
	function fmt(v) {
		const abs = Math.abs(v);
		if (abs >= 1e12) return (v / 1e12).toFixed(1) + "조";
		if (abs >= 1e8) return (v / 1e8).toFixed(0) + "억";
		if (abs >= 100) return v.toFixed(0);
		return v.toFixed(2);
	}
</script>

<div class="w-full h-full flex flex-col gap-2">
	<svg bind:this={svgEl} viewBox="0 0 {width} {height}" class="w-full flex-1" preserveAspectRatio="none">
		<line x1={padding.left} x2={width - padding.right} y1={yPos(0)} y2={yPos(0)} stroke="hsl(var(--border))" />
		{#each ticks() as t}
			<line x1={padding.left} x2={width - padding.right} y1={yPos(t)} y2={yPos(t)} stroke="hsl(var(--border))" stroke-dasharray="2 4" />
			<text x={padding.left - 6} y={yPos(t) + 3} text-anchor="end" class="text-[10px] fill-[hsl(var(--muted-foreground))]">{fmt(t)}</text>
		{/each}
		{#each bars as b, i}
			{@const { x, w } = xBand(i, bars.length)}
			{@const bw = Math.max(2, w * 0.6)}
			{@const bx = x + (w - bw) / 2}
			{@const y0 = yPos(b.top)}
			{@const y1 = yPos(b.bot)}
			<rect x={bx} y={Math.min(y0, y1)} width={bw} height={Math.max(1, Math.abs(y1 - y0))} fill={b.color} opacity={b.measure === "relative" ? 0.85 : 1} />
			<text x={bx + bw / 2} y={Math.min(y0, y1) - 4} text-anchor="middle" class="text-[9px] fill-[hsl(var(--foreground))] tabular-nums">{fmt(b.value)}</text>
			<text x={bx + bw / 2} y={height - padding.bottom + 16} text-anchor="middle" class="text-[10px] fill-[hsl(var(--muted-foreground))]">{b.label}</text>
		{/each}
	</svg>
</div>
