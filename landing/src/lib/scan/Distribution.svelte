<script lang="ts">
	/**
	 * 분포 패널 — 현재 정렬 컬럼의 30 bin 히스토그램.
	 *
	 *  - bin click → 그 구간 회사를 그리드에서 highlight (양방향)
	 *  - 산업 필터 시 산업 평균 line 추가 표시
	 *  - 통계량 (mean / median / p10 / p90) 표시
	 *  - 로그 스케일 toggle (MetricDef.distribution 기본값 자동)
	 */
	import { binNumeric, findBinIndex } from './binning';
	import type { DistributionData } from './binning';
	import { METRICS_BY_KEY } from './metrics';
	import type { ScanNode } from './types';
	import { fmtKrw } from '$lib/format/krw';
	import { fmtPct, fmtMul } from '$lib/format/pct';

	interface Props {
		nodes: ScanNode[];
		filteredNodes: ScanNode[];
		metricKey: string;
		highlightBin: { x0: number; x1: number } | null;
		onBinHover: (bin: { x0: number; x1: number } | null) => void;
	}

	let { nodes, filteredNodes, metricKey, highlightBin, onBinHover }: Props = $props();

	let metric = $derived(METRICS_BY_KEY[metricKey]);
	let scale = $state<'linear' | 'log'>('linear');

	// metric 바뀌면 권장 스케일 따라가기
	$effect(() => {
		scale = metric?.distribution || 'linear';
	});

	let dist = $derived.by<DistributionData>(() => {
		if (!metric || metric.type !== 'number') {
			return {
				bins: [],
				min: 0,
				max: 0,
				count: 0,
				scale: 'linear',
				mean: 0,
				median: 0,
				p10: 0,
				p90: 0
			};
		}
		return binNumeric(
			nodes.map((n) => (n as Record<string, unknown>)[metricKey] as number | null | undefined),
			scale
		);
	});

	// 현재 필터된 회사들의 평균 (bin 위에 line 으로)
	let filteredMean = $derived.by(() => {
		if (!metric || metric.type !== 'number' || filteredNodes.length === 0) return null;
		const valid: number[] = [];
		for (const n of filteredNodes) {
			const v = (n as Record<string, unknown>)[metricKey];
			if (typeof v === 'number' && Number.isFinite(v)) {
				if (scale === 'log' && v <= 0) continue;
				valid.push(v);
			}
		}
		if (valid.length === 0) return null;
		return valid.reduce((s, v) => s + v, 0) / valid.length;
	});

	let filteredMeanBin = $derived(filteredMean !== null ? findBinIndex(dist, filteredMean) : -1);

	const W = 280;
	const H = 140;
	const PAD_T = 8;
	const PAD_B = 18;

	let maxCount = $derived(dist.bins.length === 0 ? 0 : Math.max(...dist.bins.map((b) => b.count)));
	let barWidth = $derived(dist.bins.length === 0 ? 0 : (W - 16) / dist.bins.length - 1);

	function fmtVal(v: number): string {
		if (!metric) return String(v);
		if (metric.unit === '원') return fmtKrw(v);
		if (metric.unit === '%' || metric.unit === '%p') return fmtPct(v);
		if (metric.unit === '배') return fmtMul(v, 1);
		if (metric.unit === '명') return Math.round(v).toLocaleString('ko-KR') + '명';
		if (metric.unit === '위') return Math.round(v) + '위';
		if (metric.unit === '건') return Math.round(v) + '건';
		return v.toFixed(1);
	}

	function isBinHighlighted(b: { x0: number; x1: number }): boolean {
		if (!highlightBin) return false;
		return b.x0 === highlightBin.x0 && b.x1 === highlightBin.x1;
	}

	function handleBinEnter(b: { x0: number; x1: number }) {
		onBinHover({ x0: b.x0, x1: b.x1 });
	}
	function handleBinLeave() {
		onBinHover(null);
	}
</script>

<div class="dist">
	<div class="dist-head">
		<div class="dist-title">
			<span class="d-mlbl">분포</span>
			<span class="d-mname">{metric?.label ?? metricKey}</span>
			{#if metric?.unit}<span class="d-munit">({metric.unit})</span>{/if}
		</div>
		{#if metric?.type === 'number'}
			<button
				type="button"
				class="scale-toggle"
				class:active={scale === 'log'}
				onclick={() => (scale = scale === 'log' ? 'linear' : 'log')}
				title="로그 스케일 toggle"
			>
				log
			</button>
		{/if}
	</div>

	{#if metric?.type !== 'number'}
		<div class="dist-empty">숫자 메트릭만 분포 표시 ({metric?.label ?? metricKey} 은 텍스트/등급)</div>
	{:else if dist.count === 0}
		<div class="dist-empty">데이터 없음</div>
	{:else}
		<svg viewBox="0 0 {W} {H}" class="dist-svg" role="img" aria-label="히스토그램">
			<!-- bars -->
			{#each dist.bins as b, i (i)}
				{@const h = maxCount === 0 ? 0 : ((H - PAD_T - PAD_B) * b.count) / maxCount}
				{@const x = 8 + i * (barWidth + 1)}
				{@const y = H - PAD_B - h}
				<rect
					{x}
					{y}
					width={barWidth}
					height={h}
					class="bar"
					class:highlighted={isBinHighlighted(b)}
					onmouseenter={() => handleBinEnter(b)}
					onmouseleave={handleBinLeave}
					role="presentation"
				></rect>
				<!-- 투명 hit area (얇은 bar 도 hover 잘 잡힘) -->
				<rect
					{x}
					y={PAD_T}
					width={barWidth + 1}
					height={H - PAD_T - PAD_B}
					class="hit"
					onmouseenter={() => handleBinEnter(b)}
					onmouseleave={handleBinLeave}
				></rect>
			{/each}
			<!-- 필터된 평균 line -->
			{#if filteredMeanBin >= 0 && filteredNodes.length < nodes.length}
				{@const lx = 8 + filteredMeanBin * (barWidth + 1) + barWidth / 2}
				<line x1={lx} x2={lx} y1={PAD_T} y2={H - PAD_B} class="mean-line" />
				<text x={lx} y={PAD_T + 4} class="mean-label" text-anchor="middle">필터 평균</text>
			{/if}
			<!-- baseline -->
			<line x1="0" x2={W} y1={H - PAD_B} y2={H - PAD_B} class="axis" />
		</svg>

		<div class="stats">
			<div class="stat">
				<span class="s-lbl">전체 평균</span>
				<span class="s-val">{fmtVal(dist.mean)}</span>
			</div>
			<div class="stat">
				<span class="s-lbl">중앙값</span>
				<span class="s-val">{fmtVal(dist.median)}</span>
			</div>
			<div class="stat">
				<span class="s-lbl">p10</span>
				<span class="s-val">{fmtVal(dist.p10)}</span>
			</div>
			<div class="stat">
				<span class="s-lbl">p90</span>
				<span class="s-val">{fmtVal(dist.p90)}</span>
			</div>
			{#if filteredMean !== null && filteredNodes.length < nodes.length}
				<div class="stat highlight">
					<span class="s-lbl">필터 평균</span>
					<span class="s-val">{fmtVal(filteredMean)}</span>
				</div>
				<div class="stat highlight">
					<span class="s-lbl">필터 사</span>
					<span class="s-val">{filteredNodes.length.toLocaleString('ko-KR')}</span>
				</div>
			{/if}
		</div>

		<div class="range">
			<span>{fmtVal(dist.min)}</span>
			<span>{fmtVal(dist.max)}</span>
		</div>
	{/if}
</div>

<style>
	.dist {
		display: flex;
		flex-direction: column;
		gap: 8px;
		padding: 12px;
		background: #050811;
		border: 1px solid #1e2433;
		border-radius: 6px;
		font-size: 11px;
		height: 100%;
		overflow: hidden;
	}
	.dist-head {
		display: flex;
		justify-content: space-between;
		align-items: center;
	}
	.dist-title {
		display: flex;
		align-items: baseline;
		gap: 6px;
	}
	.d-mlbl {
		font-size: 10px;
		color: #64748b;
		text-transform: uppercase;
		letter-spacing: 0.05em;
	}
	.d-mname {
		font-weight: 600;
		color: #f1f5f9;
		font-size: 12px;
	}
	.d-munit {
		font-size: 10px;
		color: #64748b;
	}
	.scale-toggle {
		font-size: 10px;
		padding: 2px 8px;
		background: #0a0e18;
		border: 1px solid #1e2433;
		border-radius: 3px;
		color: #94a3b8;
		font-family: monospace;
		cursor: pointer;
	}
	.scale-toggle.active {
		background: rgba(251, 146, 60, 0.1);
		border-color: rgba(251, 146, 60, 0.4);
		color: #fb923c;
	}

	.dist-empty {
		flex: 1;
		display: flex;
		align-items: center;
		justify-content: center;
		color: #475569;
		font-size: 11px;
		text-align: center;
		padding: 20px 8px;
	}

	.dist-svg {
		width: 100%;
		height: auto;
	}
	.bar {
		fill: #475569;
		transition: fill 0.1s;
	}
	.bar.highlighted {
		fill: #fb923c;
	}
	.hit {
		fill: transparent;
		cursor: crosshair;
	}
	.hit:hover + .bar,
	.hit:hover {
		cursor: crosshair;
	}
	.mean-line {
		stroke: #fb923c;
		stroke-width: 1.5;
		stroke-dasharray: 2 2;
	}
	.mean-label {
		fill: #fb923c;
		font-size: 8px;
		font-family: monospace;
	}
	.axis {
		stroke: #1e2433;
		stroke-width: 1;
	}

	.stats {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 4px 12px;
	}
	.stat {
		display: flex;
		justify-content: space-between;
		font-family: monospace;
		font-size: 10px;
	}
	.s-lbl {
		color: #64748b;
	}
	.s-val {
		color: #cbd5e1;
		font-weight: 500;
	}
	.stat.highlight .s-val {
		color: #fb923c;
	}

	.range {
		display: flex;
		justify-content: space-between;
		font-family: monospace;
		font-size: 9px;
		color: #475569;
		padding: 0 8px;
	}
</style>
