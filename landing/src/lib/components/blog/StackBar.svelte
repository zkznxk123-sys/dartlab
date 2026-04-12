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

	let { data = [], title = '', unit = '억원', height = 300 }: Props = $props();

	const W = 700;
	const PAD = { top: 40, right: 20, bottom: 50, left: 80 };
	const plotW = W - PAD.left - PAD.right;
	const plotH = height - PAD.top - PAD.bottom;

	const maxTotal = $derived(Math.max(...data.map((d) => d.segments.reduce((s, seg) => s + Math.max(seg.value, 0), 0))));
	const gap = $derived(plotW / data.length);
	const barW = $derived(Math.min(gap * 0.6, 70));

	function y(v: number): number {
		return PAD.top + (1 - v / maxTotal) * plotH;
	}

	function fmt(v: number): string {
		if (Math.abs(v) >= 1e4) return (v / 1e4).toFixed(1) + '조';
		return v.toLocaleString('ko-KR');
	}

	// legend: unique labels
	const legendItems = $derived(
		data[0]?.segments.map((s) => ({ label: s.label, color: s.color })) ?? []
	);

	let hoverIdx = $state<number | null>(null);
</script>

<div class="chart-wrap">
	{#if title}
		<div class="chart-title">{title}</div>
	{/if}
	<svg viewBox="0 0 {W} {height}" xmlns="http://www.w3.org/2000/svg">
		<!-- grid -->
		{#each Array.from({ length: 5 }, (_, i) => (maxTotal * i) / 4) as tick}
			<line
				x1={PAD.left}
				y1={y(tick)}
				x2={W - PAD.right}
				y2={y(tick)}
				stroke="#1e293b"
				stroke-width="0.5"
			/>
			<text x={PAD.left - 8} y={y(tick) + 4} text-anchor="end" fill="#64748b" font-size="11"
				>{fmt(tick)}</text
			>
		{/each}

		<!-- stacked bars -->
		{#each data as item, i}
			{@const bx = PAD.left + i * gap + (gap - barW) / 2}
			{#each item.segments as seg, si}
				{@const prevSum = item.segments.slice(0, si).reduce((s, p) => s + Math.max(p.value, 0), 0)}
				{@const segH = (Math.max(seg.value, 0) / maxTotal) * plotH}
				<rect
					x={bx}
					y={y(prevSum + Math.max(seg.value, 0))}
					width={barW}
					height={Math.max(segH, 0)}
					fill={seg.color}
					opacity={hoverIdx === i ? 1 : 0.85}
					rx="2"
					onmouseenter={() => (hoverIdx = i)}
					onmouseleave={() => (hoverIdx = null)}
				/>
			{/each}
			<text
				x={bx + barW / 2}
				y={height - 10}
				text-anchor="middle"
				fill="#94a3b8"
				font-size="11">{item.year}</text
			>
			<!-- total on top -->
			{#if hoverIdx === i}
				{@const total = item.segments.reduce((s, seg) => s + Math.max(seg.value, 0), 0)}
				<text
					x={bx + barW / 2}
					y={y(total) - 8}
					text-anchor="middle"
					fill="#f1f5f9"
					font-size="12"
					font-weight="bold">{fmt(total)}</text
				>
			{/if}
		{/each}

		<!-- legend -->
		{#each legendItems as item, i}
			<rect
				x={PAD.left + i * 110}
				y={height - 28}
				width="12"
				height="12"
				rx="2"
				fill={item.color}
			/>
			<text x={PAD.left + i * 110 + 16} y={height - 18} fill="#94a3b8" font-size="11"
				>{item.label}</text
			>
		{/each}

		<text x={PAD.left} y={PAD.top - 12} fill="#64748b" font-size="10">({unit})</text>
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
		max-width: 700px;
		height: auto;
		font-family: -apple-system, 'Segoe UI', sans-serif;
	}
</style>
