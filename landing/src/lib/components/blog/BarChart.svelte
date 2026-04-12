<script lang="ts">
	interface DataPoint {
		label: string;
		value: number;
		color?: string;
	}

	interface Props {
		data: DataPoint[];
		title?: string;
		unit?: string;
		height?: number;
		horizontal?: boolean;
	}

	let {
		data = [],
		title = '',
		unit = '억원',
		height = 300,
		horizontal = false
	}: Props = $props();

	const W = 700;
	const PAD = { top: 40, right: 20, bottom: 50, left: 90 };
	const plotW = W - PAD.left - PAD.right;
	const plotH = height - PAD.top - PAD.bottom;

	const vals = $derived(data.map((d) => d.value));
	const rawMax = $derived(Math.max(...vals, 0));
	const rawMin = $derived(Math.min(...vals, 0));
	const padding = $derived((rawMax - rawMin) * 0.1 || 1);
	const yMax = $derived(rawMax + padding);
	const yMin = $derived(rawMin < 0 ? rawMin - padding : 0);

	function y(v: number): number {
		return PAD.top + (1 - (v - yMin) / (yMax - yMin)) * plotH;
	}

	const zeroY = $derived(y(0));
	const barW = $derived(Math.min(plotW / data.length * 0.6, 60));
	const gap = $derived(plotW / data.length);

	function barColor(d: DataPoint): string {
		if (d.color) return d.color;
		return d.value >= 0 ? '#22c55e' : '#ef4444';
	}

	function fmt(v: number): string {
		if (Math.abs(v) >= 1e4) return (v / 1e4).toFixed(1) + '조';
		return v.toLocaleString('ko-KR');
	}

	let hoverIdx = $state<number | null>(null);
</script>

<div class="chart-wrap">
	{#if title}
		<div class="chart-title">{title}</div>
	{/if}
	<svg viewBox="0 0 {W} {height}" xmlns="http://www.w3.org/2000/svg">
		<!-- zero line -->
		<line
			x1={PAD.left}
			y1={zeroY}
			x2={W - PAD.right}
			y2={zeroY}
			stroke="#475569"
			stroke-width="1"
		/>

		<!-- bars -->
		{#each data as d, i}
			{@const bx = PAD.left + i * gap + (gap - barW) / 2}
			{@const byTop = d.value >= 0 ? y(d.value) : zeroY}
			{@const bh = Math.abs(y(d.value) - zeroY)}
			<rect
				x={bx}
				y={byTop}
				width={barW}
				height={Math.max(bh, 1)}
				rx="3"
				fill={barColor(d)}
				opacity={hoverIdx === i ? 1 : 0.85}
				onmouseenter={() => (hoverIdx = i)}
				onmouseleave={() => (hoverIdx = null)}
			/>
			<!-- label -->
			<text
				x={bx + barW / 2}
				y={height - 10}
				text-anchor="middle"
				fill="#94a3b8"
				font-size="11">{d.label}</text
			>
			<!-- value on top -->
			{#if hoverIdx === i}
				<text
					x={bx + barW / 2}
					y={byTop - 8}
					text-anchor="middle"
					fill={barColor(d)}
					font-size="12"
					font-weight="bold">{fmt(d.value)}</text
				>
			{/if}
		{/each}

		<!-- y axis ticks -->
		{#each Array.from({ length: 5 }, (_, i) => yMin + ((yMax - yMin) * i) / 4) as tick}
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
