<!--
	Donut — 구성비 시각화. 라벨 외부 leader line. Editorial 톤.
	props:
	  slices: Array<{ label, value, color? }>
	  height: 240
	  centerLabel? / centerValue? — 중앙 큰 텍스트
-->
<script>
	import { isFiniteNum } from "./util.js";

	let {
		slices = [],
		height = 240,
		centerLabel = "",
		centerValue = "",
	} = $props();

	const W = 360;
	const cx = W / 2;
	const cy = height / 2;
	const radiusOuter = Math.min(W, height) / 2 - 24;
	const radiusInner = radiusOuter * 0.62;

	const palette = [
		"var(--ed-brand)",
		"var(--ed-up)",
		"var(--ed-warn)",
		"#7a98c4",
		"#a37ac4",
		"var(--ed-text-2)",
		"#5a7a8c",
		"#c47a7a",
	];

	const validSlices = $derived(
		slices.filter((s) => isFiniteNum(s.value) && s.value > 0)
	);
	const total = $derived(validSlices.reduce((a, s) => a + s.value, 0) || 1);

	function arcPath(startAngle, endAngle) {
		// angles in radians, 0 = top, clockwise
		const sx1 = cx + radiusOuter * Math.sin(startAngle);
		const sy1 = cy - radiusOuter * Math.cos(startAngle);
		const ex1 = cx + radiusOuter * Math.sin(endAngle);
		const ey1 = cy - radiusOuter * Math.cos(endAngle);
		const sx2 = cx + radiusInner * Math.sin(endAngle);
		const sy2 = cy - radiusInner * Math.cos(endAngle);
		const ex2 = cx + radiusInner * Math.sin(startAngle);
		const ey2 = cy - radiusInner * Math.cos(startAngle);
		const largeArc = endAngle - startAngle > Math.PI ? 1 : 0;
		return `M${sx1.toFixed(2)} ${sy1.toFixed(2)} A${radiusOuter} ${radiusOuter} 0 ${largeArc} 1 ${ex1.toFixed(2)} ${ey1.toFixed(2)} L${sx2.toFixed(2)} ${sy2.toFixed(2)} A${radiusInner} ${radiusInner} 0 ${largeArc} 0 ${ex2.toFixed(2)} ${ey2.toFixed(2)} Z`;
	}

	const arcs = $derived.by(() => {
		let acc = 0;
		return validSlices.map((s, i) => {
			const start = (acc / total) * Math.PI * 2;
			acc += s.value;
			const end = (acc / total) * Math.PI * 2;
			const mid = (start + end) / 2;
			return {
				...s,
				start,
				end,
				mid,
				pct: (s.value / total) * 100,
				color: s.color || palette[i % palette.length],
				labelX: cx + (radiusOuter + 8) * Math.sin(mid),
				labelY: cy - (radiusOuter + 8) * Math.cos(mid),
				anchor: Math.sin(mid) > 0 ? "start" : "end",
			};
		});
	});
</script>

<div class="w-full flex items-center gap-4">
	<svg viewBox="0 0 {W} {height}" class="shrink-0" style="max-width: 260px;">
		{#each arcs as a}
			<path d={arcPath(a.start, a.end)} fill={a.color} opacity="0.92" />
		{/each}
		{#if centerLabel || centerValue}
			<text x={cx} y={cy - 4} text-anchor="middle" font-size="9.5" fill="var(--ed-text-3)" font-family="var(--font-body)" letter-spacing="0.14em">
				{centerLabel.toUpperCase()}
			</text>
			<text x={cx} y={cy + 14} text-anchor="middle" font-size="17" fill="var(--ed-text)" font-family="var(--font-num)" font-weight="500">
				{centerValue}
			</text>
		{/if}
	</svg>

	<ul class="flex-1 min-w-0 flex flex-col gap-1.5">
		{#each arcs as a}
			<li class="flex items-center gap-2 text-[11.5px]" style="color: var(--ed-text-2);">
				<span class="inline-block w-2.5 h-2.5 rounded-sm shrink-0" style="background: {a.color};"></span>
				<span class="truncate flex-1" title={a.label}>{a.label}</span>
				<span class="ed-num shrink-0" style="color: var(--ed-text);">{a.pct.toFixed(1)}%</span>
			</li>
		{/each}
		{#if arcs.length === 0}
			<li class="text-[11.5px]" style="color: var(--ed-text-3);">데이터 없음</li>
		{/if}
	</ul>
</div>
