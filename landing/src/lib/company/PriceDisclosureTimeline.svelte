<script lang="ts">
	import { ExternalLink, LineChart, Loader2 } from 'lucide-svelte';
	import type { RegularFiling } from '$lib/data/companyFilingsRuntime';
	import { loadCompanyPriceTimeline, type CompanyPriceTimeline } from '$lib/data/companyPriceTimelineRuntime';
	import { alignFilingsToPrices, summarizeTimeline, type PricePoint } from './priceTimelineModel';
	import { fmtKrw, fmtPrice } from '$lib/format/krw';
	import { fmtPct } from '$lib/format/pct';

	let {
		code,
		corpName = '',
		filings = []
	}: {
		code: string;
		corpName?: string;
		filings?: RegularFiling[];
	} = $props();

	type RangeKey = '1Y' | '3Y' | 'ALL';
	const RANGES: Array<{ key: RangeKey; label: string; points: number | null }> = [
		{ key: '1Y', label: '1년', points: 252 },
		{ key: '3Y', label: '3년', points: 756 },
		{ key: 'ALL', label: '전체', points: null }
	];

	let range = $state<RangeKey>('1Y');
	let timeline = $state<CompanyPriceTimeline | null>(null);
	let loading = $state(true);
	let errorMsg = $state<string | null>(null);

	$effect(() => {
		const c = code;
		loading = true;
		errorMsg = null;
		timeline = null;
		void loadCompanyPriceTimeline(c, fetch)
			.then((next) => {
				if (code === c) timeline = next;
			})
			.catch((error) => {
				if (code === c) errorMsg = error instanceof Error ? error.message : String(error);
			})
			.finally(() => {
				if (code === c) loading = false;
			});
	});

	const visiblePoints = $derived.by(() => {
		const points = timeline?.points ?? [];
		const spec = RANGES.find((item) => item.key === range);
		return spec?.points ? points.slice(-spec.points) : points;
	});
	const markers = $derived.by(() => alignFilingsToPrices(visiblePoints, filings).slice(-24).reverse());
	const stats = $derived(summarizeTimeline(visiblePoints));
	const chart = $derived(buildChart(visiblePoints));
	const displayName = $derived(corpName || timeline?.points[0]?.name || code);
	const sourceLabel = $derived(timeline?.source ?? `krx/prices/company/${code}.parquet`);

	function buildChart(points: PricePoint[]) {
		const closeValues = points.map((point) => point.close).filter(isFiniteNumber);
		const volumeValues = points.map((point) => point.volume).filter(isFiniteNumber);
		const min = closeValues.length ? Math.min(...closeValues) : 0;
		const max = closeValues.length ? Math.max(...closeValues) : 0;
		const volumeMax = volumeValues.length ? Math.max(...volumeValues) : 0;
		return {
			min,
			max,
			volumeMax,
			pricePath: pricePath(points, min, max),
			areaPath: areaPath(points, min, max),
			bars: volumeBars(points, volumeMax)
		};
	}

	function pricePath(points: PricePoint[], min: number, max: number): string {
		const coords = points
			.map((point, index) => (point.close == null ? null : `${x(index, points.length).toFixed(1)},${y(point.close, min, max).toFixed(1)}`))
			.filter((value): value is string => value != null);
		return coords.map((coord, index) => `${index === 0 ? 'M' : 'L'}${coord}`).join(' ');
	}

	function areaPath(points: PricePoint[], min: number, max: number): string {
		const coords = points
			.map((point, index) =>
				point.close == null
					? null
					: { x: x(index, points.length), y: y(point.close, min, max) }
			)
			.filter((value): value is { x: number; y: number } => value != null);
		if (coords.length < 2) return '';
		const line = coords.map((coord, index) => `${index === 0 ? 'M' : 'L'}${coord.x.toFixed(1)},${coord.y.toFixed(1)}`).join(' ');
		const first = coords[0];
		const last = coords.at(-1) ?? first;
		return `${line} L${last.x.toFixed(1)},276 L${first.x.toFixed(1)},276 Z`;
	}

	function volumeBars(points: PricePoint[], volumeMax: number) {
		const barWidth = Math.max(1.2, 880 / Math.max(points.length, 1) - 1);
		return points.map((point, index) => {
			const ratio = volumeMax && point.volume != null ? point.volume / volumeMax : 0;
			const height = Math.max(0, ratio * 46);
			return {
				x: x(index, points.length) - barWidth / 2,
				y: 328 - height,
				width: barWidth,
				height
			};
		});
	}

	function x(index: number, length: number): number {
		if (length <= 1) return 60;
		return 60 + (index / (length - 1)) * 880;
	}

	function y(value: number, min: number, max: number): number {
		if (max <= min) return 150;
		return 276 - ((value - min) / (max - min)) * 206;
	}

	function markerX(index: number): number {
		return x(index, visiblePoints.length);
	}

	function markerY(point: PricePoint | null): number {
		return point?.close == null ? 70 : y(point.close, chart.min, chart.max);
	}

	function fmtDate(value: string): string {
		const d = value.replace(/[^0-9]/g, '').slice(0, 8);
		if (d.length !== 8) return value || '-';
		return `${d.slice(0, 4)}.${d.slice(4, 6)}.${d.slice(6, 8)}`;
	}

	function fmtNum(value: number | null): string {
		if (value == null || !Number.isFinite(value)) return '-';
		return new Intl.NumberFormat('ko-KR', { maximumFractionDigits: 0 }).format(value);
	}

	function isFiniteNumber(value: number | null): value is number {
		return typeof value === 'number' && Number.isFinite(value);
	}
</script>

<section class="timeline-pane" aria-label="주가와 공시 타임라인">
	<header class="tp-head">
		<div class="title">
			<LineChart size={17} />
			<div>
				<strong>{displayName}</strong>
				<span>{sourceLabel}</span>
			</div>
		</div>
		<div class="range" aria-label="기간 선택">
			{#each RANGES as item (item.key)}
				<button type="button" class:active={range === item.key} onclick={() => (range = item.key)}>
					{item.label}
				</button>
			{/each}
		</div>
	</header>

	{#if loading}
		<div class="state"><span class="spin"><Loader2 size={24} /></span><p>주가 시계열을 여는 중</p></div>
	{:else if errorMsg}
		<div class="state">
			<p>회사별 주가 artifact를 아직 읽지 못했습니다.</p>
			<small>{errorMsg}</small>
		</div>
	{:else if !visiblePoints.length}
		<div class="state"><p>이 회사의 주가 시계열 데이터가 없습니다.</p></div>
	{:else}
		<div class="stats">
			<div class="stat">
				<span>종가</span>
				<strong>{fmtPrice(stats.latest?.close ?? null)}</strong>
				<em>{stats.latest ? fmtDate(stats.latest.date) : '-'}</em>
			</div>
			<div class="stat">
				<span>기간 수익률</span>
				<strong class:up={(stats.returnPct ?? 0) >= 0} class:down={(stats.returnPct ?? 0) < 0}>{fmtPct(stats.returnPct, { withSign: true })}</strong>
				<em>{stats.first ? fmtDate(stats.first.date) : '-'}</em>
			</div>
			<div class="stat">
				<span>고가 / 저가</span>
				<strong>{fmtPrice(stats.high)} / {fmtPrice(stats.low)}</strong>
				<em>{range}</em>
			</div>
			<div class="stat">
				<span>시가총액</span>
				<strong>{fmtKrw(stats.latest?.marketCap ?? null)}</strong>
				<em>최근 거래일</em>
			</div>
			<div class="stat">
				<span>평균 거래량</span>
				<strong>{fmtNum(stats.avgVolume)}</strong>
				<em>{visiblePoints.length} 거래일</em>
			</div>
		</div>

		<div class="chart-wrap">
			<svg viewBox="0 0 1000 360" role="img" aria-label="가격, 거래량, 공시 마커 차트">
				<defs>
					<linearGradient id={`price-fill-${code}`} x1="0" x2="0" y1="0" y2="1">
						<stop offset="0%" stop-color="#38bdf8" stop-opacity="0.28" />
						<stop offset="100%" stop-color="#38bdf8" stop-opacity="0.02" />
					</linearGradient>
				</defs>
				<line x1="60" y1="70" x2="940" y2="70" class="grid" />
				<line x1="60" y1="173" x2="940" y2="173" class="grid" />
				<line x1="60" y1="276" x2="940" y2="276" class="grid" />
				<text x="18" y="75" class="axis">{fmtPrice(chart.max)}</text>
				<text x="18" y="280" class="axis">{fmtPrice(chart.min)}</text>

				{#each chart.bars as bar, index (`${visiblePoints[index]?.date}-bar`)}
					<rect class="vol" x={bar.x} y={bar.y} width={bar.width} height={bar.height} />
				{/each}
				{#if chart.areaPath}
					<path d={chart.areaPath} fill={`url(#price-fill-${code})`} />
				{/if}
				<path class="price-line" d={chart.pricePath} />

				{#each markers as marker (marker.filing.rceptNo)}
					<g class="marker" transform={`translate(${markerX(marker.index).toFixed(1)},0)`}>
						<line x1="0" y1="62" x2="0" y2="334" />
						<circle cy={markerY(marker.point)} r="5" />
						<title>{marker.filing.reportType} · {fmtDate(marker.filing.rceptDate)}</title>
					</g>
				{/each}

				<text x="60" y="352" class="axis">{fmtDate(visiblePoints[0]?.date ?? '')}</text>
				<text x="940" y="352" class="axis right">{fmtDate(visiblePoints.at(-1)?.date ?? '')}</text>
			</svg>
		</div>

		<div class="marker-list">
			<div class="marker-head">
				<span>정기공시 마커</span>
				<small>{markers.length}건</small>
			</div>
			{#if markers.length}
				<div class="events">
					{#each markers as marker (marker.filing.rceptNo)}
						<a class="event" href={marker.filing.url} target="_blank" rel="noreferrer">
							<span class="event-date">{fmtDate(marker.filing.rceptDate)}</span>
							<strong>{marker.filing.reportType}</strong>
							<em>{marker.point ? fmtPrice(marker.point.close) : '-'}</em>
							<ExternalLink size={12} />
						</a>
					{/each}
				</div>
			{:else}
				<div class="empty">선택 기간 안의 정기공시가 없습니다.</div>
			{/if}
		</div>
	{/if}
</section>

<style>
	.timeline-pane {
		min-height: 100%;
		display: flex;
		flex-direction: column;
		gap: 10px;
		color: #f1f5f9;
	}
	.tp-head {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 12px;
		padding: 9px 11px;
		border: 1px solid #1e2433;
		border-radius: 8px;
		background: #080d17;
	}
	.title {
		display: flex;
		align-items: center;
		gap: 8px;
		min-width: 0;
		color: #38bdf8;
	}
	.title div {
		min-width: 0;
		display: flex;
		flex-direction: column;
		gap: 2px;
	}
	.title strong {
		color: #f8fafc;
		font-size: 13px;
	}
	.title span {
		color: #64748b;
		font-size: 10px;
		font-family: monospace;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	.range {
		flex-shrink: 0;
		display: inline-flex;
		gap: 3px;
		padding: 3px;
		border: 1px solid #1e2433;
		border-radius: 7px;
		background: #050811;
	}
	.range button {
		height: 26px;
		padding: 0 9px;
		border: 0;
		border-radius: 5px;
		background: transparent;
		color: #94a3b8;
		font: inherit;
		font-size: 11px;
		cursor: pointer;
	}
	.range button.active {
		background: rgba(56, 189, 248, 0.14);
		color: #67e8f9;
	}
	.stats {
		display: grid;
		grid-template-columns: repeat(5, minmax(0, 1fr));
		gap: 8px;
	}
	.stat {
		min-width: 0;
		padding: 9px 10px;
		border: 1px solid #1e2433;
		border-radius: 8px;
		background: rgba(8, 13, 23, 0.86);
	}
	.stat span,
	.stat em {
		display: block;
		color: #64748b;
		font-size: 10px;
		font-style: normal;
		white-space: nowrap;
	}
	.stat strong {
		display: block;
		margin: 3px 0 2px;
		color: #f8fafc;
		font-size: 15px;
		font-weight: 800;
		font-variant-numeric: tabular-nums;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	.stat strong.up {
		color: #34d399;
	}
	.stat strong.down {
		color: #f87171;
	}
	.chart-wrap {
		border: 1px solid #1e2433;
		border-radius: 8px;
		background: #050811;
		overflow: hidden;
	}
	svg {
		display: block;
		width: 100%;
		aspect-ratio: 1000 / 360;
	}
	.grid {
		stroke: #1e293b;
		stroke-width: 1;
	}
	.axis {
		fill: #64748b;
		font-size: 10px;
		font-family: monospace;
	}
	.axis.right {
		text-anchor: end;
	}
	.vol {
		fill: rgba(148, 163, 184, 0.18);
	}
	.price-line {
		fill: none;
		stroke: #38bdf8;
		stroke-width: 2.2;
		stroke-linecap: round;
		stroke-linejoin: round;
	}
	.marker line {
		stroke: rgba(251, 146, 60, 0.45);
		stroke-width: 1;
		stroke-dasharray: 3 4;
	}
	.marker circle {
		fill: #fb923c;
		stroke: #050811;
		stroke-width: 2;
	}
	.marker-list {
		min-height: 0;
		border: 1px solid #1e2433;
		border-radius: 8px;
		background: rgba(8, 13, 23, 0.7);
		overflow: hidden;
	}
	.marker-head {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 8px 10px;
		border-bottom: 1px solid #1e2433;
	}
	.marker-head span {
		font-size: 12px;
		font-weight: 800;
	}
	.marker-head small {
		color: #64748b;
		font-size: 10px;
	}
	.events {
		display: grid;
		grid-template-columns: repeat(2, minmax(0, 1fr));
	}
	.event {
		display: grid;
		grid-template-columns: 74px 1fr 88px 14px;
		gap: 8px;
		align-items: center;
		padding: 7px 10px;
		border-right: 1px solid #1e2433;
		border-bottom: 1px solid #1e2433;
		color: #cbd5e1;
		text-decoration: none;
	}
	.event:hover {
		background: rgba(56, 189, 248, 0.07);
		color: #f8fafc;
	}
	.event-date,
	.event em {
		color: #64748b;
		font-size: 10px;
		font-style: normal;
		font-family: monospace;
	}
	.event strong {
		min-width: 0;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
		font-size: 12px;
	}
	.event em {
		text-align: right;
	}
	.state {
		flex: 1 1 auto;
		min-height: 360px;
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		gap: 10px;
		border: 1px solid #1e2433;
		border-radius: 8px;
		color: #94a3b8;
		text-align: center;
	}
	.state p {
		margin: 0;
		font-size: 13px;
	}
	.state small {
		max-width: 520px;
		color: #64748b;
		font-size: 11px;
		line-height: 1.5;
	}
	.empty {
		padding: 16px;
		color: #64748b;
		font-size: 11px;
		text-align: center;
	}
	.spin {
		animation: spin 0.9s linear infinite;
	}
	@keyframes spin {
		to {
			transform: rotate(360deg);
		}
	}
	@media (max-width: 980px) {
		.stats {
			grid-template-columns: repeat(2, minmax(0, 1fr));
		}
		.events {
			grid-template-columns: 1fr;
		}
	}
	@media (max-width: 640px) {
		.tp-head {
			align-items: flex-start;
			flex-direction: column;
		}
		.stats {
			grid-template-columns: 1fr;
		}
		.event {
			grid-template-columns: 72px 1fr 14px;
		}
		.event em {
			display: none;
		}
	}
</style>
