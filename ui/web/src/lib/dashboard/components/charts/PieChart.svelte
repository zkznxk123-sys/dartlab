<script>
	import { slotColor } from "../colorSlot.js";

	let { spec } = $props();

	const series = $derived(spec?.series || []);
	const dual = $derived(!!spec?.options?.dual);

	function arcPath(cx, cy, r, a0, a1) {
		const x0 = cx + r * Math.cos(a0);
		const y0 = cy + r * Math.sin(a0);
		const x1 = cx + r * Math.cos(a1);
		const y1 = cy + r * Math.sin(a1);
		const large = a1 - a0 > Math.PI ? 1 : 0;
		return `M ${cx} ${cy} L ${x0} ${y0} A ${r} ${r} 0 ${large} 1 ${x1} ${y1} Z`;
	}

	function buildSlices(s) {
		const data = (s.data || []).map((v) => (typeof v === "number" ? Math.max(0, v) : 0));
		const total = data.reduce((a, b) => a + b, 0);
		if (total <= 0) return [];
		let acc = -Math.PI / 2;
		const slots = s.colorSlots || [];
		return data.map((v, i) => {
			const angle = (v / total) * Math.PI * 2;
			const path = arcPath(110, 110, 100, acc, acc + angle);
			acc += angle;
			return { path, label: s.labels?.[i] || "", value: v, ratio: v / total, color: slotColor(slots[i] || "primary") };
		});
	}

	function fmt(v) {
		const abs = Math.abs(v);
		if (abs >= 1e12) return (v / 1e12).toFixed(1) + "조";
		if (abs >= 1e8) return (v / 1e8).toFixed(0) + "억";
		return v.toString();
	}
</script>

<div class="w-full h-full grid {dual ? 'grid-cols-2 gap-4' : 'grid-cols-1'}">
	{#each series as s}
		{@const slices = buildSlices(s)}
		<div class="flex flex-col items-center gap-2">
			<div class="text-xs font-medium text-muted-foreground">{s.label}</div>
			<svg viewBox="0 0 220 220" class="w-full max-w-[220px]">
				{#each slices as sl}
					<path d={sl.path} fill={sl.color} stroke="hsl(var(--card))" stroke-width="1.5" />
				{/each}
			</svg>
			<div class="grid grid-cols-2 gap-x-3 gap-y-0.5 text-[10px] w-full">
				{#each slices as sl}
					<span class="inline-flex items-center gap-1 text-foreground">
						<span class="inline-block w-2 h-2 rounded-sm" style="background: {sl.color}"></span>
						<span class="truncate">{sl.label}</span>
					</span>
					<span class="text-right text-muted-foreground tabular-nums">{(sl.ratio * 100).toFixed(1)}%</span>
				{/each}
			</div>
		</div>
	{/each}
</div>
