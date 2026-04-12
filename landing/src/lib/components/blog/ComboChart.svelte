<script lang="ts">
	interface DataPoint {
		year: string;
		[key: string]: string | number | null;
	}

	interface Props {
		data: DataPoint[];
		title?: string;
		unit?: string;
		lineKeys?: string[];
		barKeys?: string[];
		lineColors?: string[];
		barColors?: string[];
		height?: number;
	}

	let {
		data = [],
		title = '',
		unit = '억원',
		lineKeys = [],
		barKeys = [],
		lineColors = ['#22c55e'],
		barColors = ['#3b82f6', '#f59e0b', '#ef4444'],
		height = 320
	}: Props = $props();

	const W = 700;
	const PAD = { top: 40, right: 20, bottom: 55, left: 75 };
	const plotW = W - PAD.left - PAD.right;
	const plotH = height - PAD.top - PAD.bottom;

	// 전체 값에서 min/max
	const allKeys = $derived([...lineKeys, ...barKeys]);
	const allVals = $derived(
		data.flatMap((d) => allKeys.map((k) => d[k] as number).filter((v) => v != null))
	);
	const rawMin = $derived(Math.min(...allVals, 0));
	const rawMax = $derived(Math.max(...allVals, 0));
	const pad = $derived((rawMax - rawMin) * 0.12 || 1);
	const yMin = $derived(rawMin < 0 ? rawMin - pad : 0);
	const yMax = $derived(rawMax + pad);

	function xCenter(i: number): number {
		const gap = plotW / data.length;
		return PAD.left + i * gap + gap / 2;
	}
	function y(v: number): number {
		return PAD.top + (1 - (v - yMin) / (yMax - yMin)) * plotH;
	}

	const zeroY = $derived(yMin <= 0 && yMax >= 0 ? y(0) : null);
	const barGroupW = $derived(Math.min((plotW / data.length) * 0.7, 80));
	const singleBarW = $derived(barKeys.length > 0 ? barGroupW / barKeys.length : 0);

	function fmt(v: number): string {
		if (Math.abs(v) >= 1e4) return (v / 1e4).toFixed(1) + '조';
		if (Math.abs(v) >= 1) return v.toLocaleString('ko-KR');
		return v.toFixed(1);
	}

	const yTicks = $derived(
		Array.from({ length: 5 }, (_, i) => yMin + ((yMax - yMin) * i) / 4)
	);

	let hoverIdx = $state<number | null>(null);
</script>

<div class="chart-wrap">
	{#if title}
		<div class="chart-title">{title}</div>
	{/if}
	<svg viewBox="0 0 {W} {height}" xmlns="http://www.w3.org/2000/svg">
		<!-- grid -->
		{#each yTicks as tick}
			<line x1={PAD.left} y1={y(tick)} x2={W - PAD.right} y2={y(tick)} stroke="#1e293b" stroke-width="0.5" />
			<text x={PAD.left - 8} y={y(tick) + 4} text-anchor="end" fill="#64748b" font-size="11">{fmt(tick)}</text>
		{/each}

		<!-- zero line -->
		{#if zeroY != null}
			<line x1={PAD.left} y1={zeroY} x2={W - PAD.right} y2={zeroY} stroke="#475569" stroke-width="1" stroke-dasharray="4,3" />
		{/if}

		<!-- bars -->
		{#each data as d, i}
			{#each barKeys as bk, bi}
				{@const val = d[bk] as number | null}
				{#if val != null}
					{@const bx = xCenter(i) - barGroupW / 2 + bi * singleBarW}
					{@const byTop = val >= 0 ? y(val) : (zeroY ?? y(0))}
					{@const bh = Math.abs(y(val) - (zeroY ?? y(0)))}
					<rect
						x={bx} y={byTop} width={singleBarW - 2} height={Math.max(bh, 1)}
						rx="2" fill={barColors[bi % barColors.length]}
						opacity={hoverIdx === i ? 1 : 0.75}
					/>
				{/if}
			{/each}
		{/each}

		<!-- lines -->
		{#each lineKeys as lk, li}
			{@const pts = data.map((d, i) => {
				const val = d[lk] as number | null;
				return val != null ? `${xCenter(i)},${y(val)}` : null;
			}).filter(Boolean)}
			<polyline
				points={pts.join(' ')}
				fill="none" stroke={lineColors[li % lineColors.length]}
				stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"
			/>
			{#each data as d, i}
				{#if d[lk] != null}
					<circle cx={xCenter(i)} cy={y(d[lk] as number)} r={hoverIdx === i ? 5 : 3.5}
						fill={lineColors[li % lineColors.length]} />
				{/if}
			{/each}
		{/each}

		<!-- x labels -->
		{#each data as d, i}
			<text x={xCenter(i)} y={height - 12} text-anchor="middle" fill="#94a3b8" font-size="12">{d.year}</text>
		{/each}

		<!-- hover zones -->
		{#each data as _, i}
			{@const gap = plotW / data.length}
			<rect x={PAD.left + i * gap} y={PAD.top} width={gap} height={plotH}
				fill="transparent"
				onmouseenter={() => (hoverIdx = i)} onmouseleave={() => (hoverIdx = null)} />
		{/each}

		<!-- tooltip -->
		{#if hoverIdx != null}
			{@const d = data[hoverIdx]}
			{@const allK = [...lineKeys, ...barKeys]}
			{@const tw = 140}
			{@const th = allK.length * 18 + 24}
			{@const tx = Math.min(Math.max(xCenter(hoverIdx) - tw / 2, PAD.left), W - PAD.right - tw)}
			<rect x={tx} y={PAD.top - 5} width={tw} height={th} rx="6"
				fill="#0f172a" fill-opacity="0.95" stroke="#334155" />
			<text x={tx + tw / 2} y={PAD.top + 12} text-anchor="middle"
				fill="#f1f5f9" font-size="11" font-weight="bold">{d.year}</text>
			{#each allK as k, ki}
				{@const isLine = lineKeys.includes(k)}
				{@const color = isLine ? lineColors[lineKeys.indexOf(k)] : barColors[barKeys.indexOf(k)]}
				<text x={tx + tw / 2} y={PAD.top + 12 + (ki + 1) * 18} text-anchor="middle"
					fill={color} font-size="11">
					{k}: {d[k] != null ? fmt(d[k] as number) : '—'}
				</text>
			{/each}
		{/if}

		<!-- legend -->
		{#each lineKeys as k, i}
			{@const lx = PAD.left + i * 100}
			<line x1={lx} y1={height - 32} x2={lx + 14} y2={height - 32}
				stroke={lineColors[i]} stroke-width="2.5" />
			<text x={lx + 18} y={height - 28} fill="#94a3b8" font-size="11">{k}</text>
		{/each}
		{#each barKeys as k, i}
			{@const lx = PAD.left + lineKeys.length * 100 + i * 100}
			<rect x={lx} y={height - 38} width="12" height="12" rx="2"
				fill={barColors[i % barColors.length]} />
			<text x={lx + 16} y={height - 28} fill="#94a3b8" font-size="11">{k}</text>
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
