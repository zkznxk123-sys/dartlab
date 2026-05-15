<!--
	Profitability — Analysis 수익성 axis specialized 시각.
	응답: { marginTrend: { history: [{ period, operatingMargin, netMargin, grossMargin, drivers: [...] }] } }
-->
<script>
	import LineTrend from "$lib/dashboard/chart/LineTrend.svelte";
	import DriverBar from "$lib/dashboard/chart/DriverBar.svelte";
	import KpiTile from "$lib/dashboard/chart/KpiTile.svelte";
	import { fmtPct, fmtKrw, isFiniteNum } from "$lib/dashboard/chart/util.js";

	let { payload = null, loading = false } = $props();

	const trend = $derived(payload?.marginTrend || null);
	const history = $derived(trend?.history || []);
	const latest = $derived(history[0] || null);
	const prev = $derived(history[1] || null);

	function delta(curr, prevVal) {
		if (!isFiniteNum(curr) || !isFiniteNum(prevVal)) return null;
		return curr - prevVal;
	}
</script>

{#if loading}
	<div class="ed-card">
		<div class="ed-eyebrow mb-2">Loading</div>
		<div class="editorial-skeleton h-32 w-full"></div>
	</div>
{:else if !trend}
	<div class="ed-card" style="border-style: dashed;">
		<div class="ed-eyebrow mb-1">No data</div>
		<div class="text-[12px]" style="color: var(--ed-text-2);">marginTrend 데이터 없음</div>
	</div>
{:else}
	<!-- KPI strip 3 칸 (latest period 기준 + Δ vs prev) -->
	<div class="grid grid-cols-3 gap-3 mb-4">
		<KpiTile
			label="매출총이익률 GPM"
			value={latest?.grossMargin}
			delta={delta(latest?.grossMargin, prev?.grossMargin)}
			unit="%"
		/>
		<KpiTile
			label="영업이익률 OPM"
			value={latest?.operatingMargin}
			delta={delta(latest?.operatingMargin, prev?.operatingMargin)}
			unit="%"
		/>
		<KpiTile
			label="순이익률 NPM"
			value={latest?.netMargin}
			delta={delta(latest?.netMargin, prev?.netMargin)}
			unit="%"
		/>
	</div>

	<!-- Margin trend line chart -->
	<div class="ed-card mb-4">
		<div class="flex items-baseline justify-between mb-2">
			<div class="ed-eyebrow">Margin Trend</div>
			<div class="text-[10.5px]" style="color: var(--ed-text-3);">
				{history.length} 기간 · GPM · OPM · NPM
			</div>
		</div>
		<LineTrend
			rows={history}
			xKey="period"
			series={[
				{ key: "grossMargin", label: "GPM", color: "var(--ed-text)" },
				{ key: "operatingMargin", label: "OPM", color: "var(--ed-brand)" },
				{ key: "netMargin", label: "NPM", color: "var(--ed-up)" },
			]}
			height={260}
			unit="%"
		/>
	</div>

	<!-- Driver breakdown (latest period 의 drivers) -->
	{#if latest?.drivers && latest.drivers.length > 0}
		<div class="ed-card mb-4">
			<div class="flex items-baseline justify-between mb-3">
				<div class="ed-eyebrow">{latest.period} 마진 변동 driver 분해</div>
				{#if isFiniteNum(latest?.driversExplained)}
					<div class="text-[10.5px] ed-num" style="color: var(--ed-text-3);">
						설명력 {latest.driversExplained.toFixed(1)}%
					</div>
				{/if}
			</div>
			<DriverBar drivers={latest.drivers} />
		</div>
	{/if}

	<!-- Revenue/OP/NI absolute trend -->
	<div class="ed-card mb-4">
		<div class="ed-eyebrow mb-2">Revenue · Operating Income · Net Income</div>
		<LineTrend
			rows={history}
			xKey="period"
			series={[
				{ key: "revenue", label: "Revenue", color: "var(--ed-text)" },
				{ key: "operatingIncome", label: "OP", color: "var(--ed-brand)" },
				{ key: "netIncome", label: "NI", color: "var(--ed-up)" },
			]}
			height={220}
		/>
	</div>

	<!-- Detail table (history full) -->
	<details class="ed-card">
		<summary class="cursor-pointer select-none ed-eyebrow">상세 표 — {history.length} 기간 full history</summary>
		<div class="mt-3 overflow-x-auto max-h-96">
			<table class="w-full text-[11px]" style="font-family: var(--font-num);">
				<thead style="position: sticky; top: 0; background: var(--ed-surface); z-index: 1;">
					<tr style="border-bottom: 1px solid var(--ed-line);">
						<th class="text-left p-1.5" style="color: var(--ed-text-3); font-weight: 600;">Period</th>
						<th class="text-right p-1.5" style="color: var(--ed-text-3); font-weight: 600;">Revenue</th>
						<th class="text-right p-1.5" style="color: var(--ed-text-3); font-weight: 600;">YoY</th>
						<th class="text-right p-1.5" style="color: var(--ed-text-3); font-weight: 600;">OP</th>
						<th class="text-right p-1.5" style="color: var(--ed-text-3); font-weight: 600;">OPM</th>
						<th class="text-right p-1.5" style="color: var(--ed-text-3); font-weight: 600;">NI</th>
						<th class="text-right p-1.5" style="color: var(--ed-text-3); font-weight: 600;">NPM</th>
						<th class="text-right p-1.5" style="color: var(--ed-text-3); font-weight: 600;">GPM</th>
					</tr>
				</thead>
				<tbody>
					{#each history as r}
						<tr style="border-bottom: 1px solid var(--ed-line);">
							<td class="p-1.5" style="color: var(--ed-text); font-weight: 500;">{r.period ?? ""}</td>
							<td class="p-1.5 text-right" style="color: var(--ed-text);">{fmtKrw(r.revenue)}</td>
							<td class="p-1.5 text-right" style="color: {isFiniteNum(r.revenueYoy) && r.revenueYoy > 0 ? 'var(--ed-up)' : isFiniteNum(r.revenueYoy) && r.revenueYoy < 0 ? 'var(--ed-down)' : 'var(--ed-text-3)'};">{fmtPct(r.revenueYoy)}</td>
							<td class="p-1.5 text-right" style="color: var(--ed-text);">{fmtKrw(r.operatingIncome)}</td>
							<td class="p-1.5 text-right" style="color: var(--ed-text-2);">{fmtPct(r.operatingMargin)}</td>
							<td class="p-1.5 text-right" style="color: var(--ed-text);">{fmtKrw(r.netIncome)}</td>
							<td class="p-1.5 text-right" style="color: var(--ed-text-2);">{fmtPct(r.netMargin)}</td>
							<td class="p-1.5 text-right" style="color: var(--ed-text-2);">{fmtPct(r.grossMargin)}</td>
						</tr>
					{/each}
				</tbody>
			</table>
		</div>
	</details>
{/if}
