<script lang="ts">
	interface StackItem {
		year: string;
		segments: { label: string; value: number; color: string }[];
	}

	interface Props {
		data: StackItem[];
		title?: string;
		unit?: string;
		height?: number;
	}

	let { data = [], title = '', unit = '억원', height = 320 }: Props = $props();

	const W = 720;
	const PAD = { top: 30, right: 20, bottom: 60, left: 70 };
	const plotW = W - PAD.left - PAD.right;
	const plotH = height - PAD.top - PAD.bottom;

	const maxTotal = $derived(
		Math.max(...data.map((d) => d.segments.reduce((s, seg) => s + Math.max(seg.value, 0), 0)))
	);
	const gap = $derived(plotW / data.length);
	const barW = $derived(Math.min(gap * 0.6, 70));

	function yScale(v: number): number {
		return PAD.top + (1 - v / maxTotal) * plotH;
	}

	function fmt(v: number): string {
		if (Math.abs(v) >= 1e4) return (v / 1e4).toFixed(1) + '조';
		if (Math.abs(v) >= 1) return v.toLocaleString('ko-KR');
		return v.toFixed(1);
	}

	const legendItems = $derived(
		data[0]?.segments.map((s) => ({ label: s.label, color: s.color })) ?? []
	);
	const legendW = $derived(legendItems.length * 100);
	const legendStartX = $derived((W - legendW) / 2);

	const yTicks = $derived(
		Array.from({ length: 5 }, (_, i) => (maxTotal * i) / 4)
	);

	let hoverIdx = $state<number | null>(null);
</script>

<div class="chart-wrap">
	{#if title}
		<div class="chart-title">{title}</div>
	{/if}
	<svg viewBox="0 0 {W} {height}" xmlns="http://www.w3.org/2000/svg">
		<!-- grid + Y labels -->
		{#each yTicks as tick}
			<line x1={PAD.left} y1={yScale(tick)} x2={W - PAD.right} y2={yScale(tick)}
				stroke="#1e293b" stroke-width="0.5" />
			<text x={PAD.left - 8} y={yScale(tick) + 4} text-anchor="end" fill="#64748b" font-size="10">
				{fmt(tick)}
			</text>
		{/each}

		<!-- Y축 라벨 -->
		<text x={12} y={PAD.top + plotH / 2} text-anchor="middle" fill="#64748b" font-size="10"
			transform="rotate(-90, 12, {PAD.top + plotH / 2})">{unit}</text>

		<!-- stacked bars -->
		{#each data as item, i}
			{@const bx = PAD.left + i * gap + (gap - barW) / 2}
			{#each item.segments as seg, si}
				{@const prevSum = item.segments.slice(0, si).reduce((s, p) => s + Math.max(p.value, 0), 0)}
				{@const segH = (Math.max(seg.value, 0) / maxTotal) * plotH}
				<rect
					x={bx} y={yScale(prevSum + Math.max(seg.value, 0))}
					width={barW} height={Math.max(segH, 0)}
					fill={seg.color} opacity={hoverIdx === i ? 1 : 0.8} rx="2"
					onmouseenter={() => (hoverIdx = i)}
					onmouseleave={() => (hoverIdx = null)}
				/>
			{/each}

			<!-- year label -->
			<text x={bx + barW / 2} y={PAD.top + plotH + 20} text-anchor="middle"
				fill="#94a3b8" font-size="12">{item.year}</text>

			<!-- total on top -->
			{#if hoverIdx === i}
				{@const total = item.segments.reduce((s, seg) => s + Math.max(seg.value, 0), 0)}
				<rect x={bx - 10} y={yScale(total) - 22} width={barW + 20} height={20} rx="4"
					fill="#0f172a" fill-opacity="0.95" stroke="#334155" />
				<text x={bx + barW / 2} y={yScale(total) - 8} text-anchor="middle"
					fill="#f1f5f9" font-size="11" font-weight="bold">
					합계 {fmt(total)}
				</text>
			{/if}
		{/each}

		<!-- 부채비율 표시 (부채/자본이면) -->
		{#each data as item, i}
			{#if hoverIdx === i}
				{@const bx = PAD.left + i * gap + (gap - barW) / 2}
				{@const debtSeg = item.segments.find((s) => s.label === '부채')}
				{@const eqSeg = item.segments.find((s) => s.label === '자본')}
				{#if debtSeg && eqSeg && eqSeg.value > 0}
					<text x={bx + barW / 2} y={PAD.top + plotH + 36} text-anchor="middle"
						fill="#f59e0b" font-size="10">
						부채비율 {(debtSeg.value / eqSeg.value * 100).toFixed(0)}%
					</text>
				{/if}
			{/if}
		{/each}

		<!-- legend (X축 아래) -->
		{#each legendItems as item, i}
			<rect x={legendStartX + i * 100} y={height - 18} width="12" height="10" rx="2"
				fill={item.color} />
			<text x={legendStartX + i * 100 + 16} y={height - 9} fill="#94a3b8" font-size="11">
				{item.label}
			</text>
		{/each}
	</svg>
</div>

<style>
	.chart-wrap {
		margin: 1.5rem 0;
		padding: 1rem;
		background: #0a0e1a;
		border: 1px solid #1e293b;
		border-radius: 12px;
		overflow-x: auto;
	}
	.chart-title {
		color: #f1f5f9;
		font-size: 0.95rem;
		font-weight: 600;
		margin-bottom: 0.5rem;
		padding-left: 0.5rem;
	}
	svg {
		width: 100%;
		max-width: 720px;
		height: auto;
		font-family: -apple-system, 'Segoe UI', sans-serif;
	}
</style>
