<script lang="ts">
	interface YearData {
		year: string;
		sales?: number | null;
		operating_profit?: number | null;
		net_profit?: number | null;
		total_assets?: number | null;
	}

	let { data }: { data: YearData[] } = $props();

	let sorted = $derived([...data].sort((a, b) => a.year.localeCompare(b.year)));

	let maxRev = $derived(Math.max(...sorted.map((d) => d.sales || 0), 1));
	let maxOI = $derived(Math.max(...sorted.map((d) => d.operating_profit || 0), 1));

	const chartHeight = 180;
	const barWidth = 42;

	function formatTrillion(v: number | null | undefined): string {
		if (!v || v === 0) return '-';
		if (Math.abs(v) >= 1e12) return `${(v / 1e12).toFixed(1)}조`;
		return `${Math.round(v / 1e8).toLocaleString()}억`;
	}

	function opm(d: YearData): string {
		if (!d.sales || !d.operating_profit) return '-';
		return `${((d.operating_profit / d.sales) * 100).toFixed(1)}%`;
	}
</script>

{#if sorted.length > 0}
	<div class="fin-trend">
		<header>
			<h3>5년 재무 추이</h3>
			<div class="legend">
				<span class="legend-item"><span class="swatch rev"></span>매출</span>
				<span class="legend-item"><span class="swatch oi"></span>영업이익</span>
				<span class="legend-item"><span class="swatch margin"></span>OPM</span>
			</div>
		</header>

		<div class="chart">
			{#each sorted as d (d.year)}
				<div class="year-col">
					<div class="bars">
						<div
							class="bar rev"
							style="height: {((d.sales || 0) / maxRev) * chartHeight}px"
							title="매출 {formatTrillion(d.sales)}"
						></div>
						<div
							class="bar oi"
							style="height: {((d.operating_profit || 0) / maxOI) * (chartHeight * 0.5)}px"
							title="영업이익 {formatTrillion(d.operating_profit)}"
						></div>
					</div>
					<div class="values">
						<div class="rev-val">{formatTrillion(d.sales)}</div>
						<div class="oi-val">{formatTrillion(d.operating_profit)}</div>
						<div class="margin-val">{opm(d)}</div>
					</div>
					<div class="year-label">{d.year}</div>
				</div>
			{/each}
		</div>
	</div>
{/if}

<style>
	.fin-trend {
		background: #0f1219;
		border: 1px solid #1e2433;
		border-radius: 10px;
		padding: 20px;
	}
	header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 16px;
	}
	h3 {
		margin: 0;
		font-size: 14px;
		color: #f1f5f9;
	}
	.legend {
		display: flex;
		gap: 12px;
	}
	.legend-item {
		display: flex;
		align-items: center;
		gap: 4px;
		font-size: 11px;
		color: #94a3b8;
	}
	.swatch {
		width: 10px;
		height: 10px;
		border-radius: 2px;
	}
	.swatch.rev {
		background: #60a5fa;
	}
	.swatch.oi {
		background: #fb923c;
	}
	.swatch.margin {
		background: #34d399;
	}

	.chart {
		display: flex;
		align-items: flex-end;
		justify-content: space-around;
		gap: 4px;
		padding-top: 16px;
	}
	.year-col {
		display: flex;
		flex-direction: column;
		align-items: center;
		min-width: 70px;
	}
	.bars {
		display: flex;
		align-items: flex-end;
		gap: 2px;
		height: 180px;
	}
	.bar {
		width: 18px;
		border-radius: 2px 2px 0 0;
		transition: opacity 0.2s;
	}
	.bar:hover {
		opacity: 0.8;
	}
	.bar.rev {
		background: #60a5fa;
	}
	.bar.oi {
		background: #fb923c;
	}
	.values {
		text-align: center;
		margin-top: 6px;
		font-size: 10px;
		line-height: 1.5;
	}
	.rev-val {
		color: #60a5fa;
		font-weight: 600;
	}
	.oi-val {
		color: #fb923c;
	}
	.margin-val {
		color: #34d399;
		font-weight: 600;
	}
	.year-label {
		margin-top: 4px;
		font-size: 11px;
		color: #94a3b8;
	}
</style>
