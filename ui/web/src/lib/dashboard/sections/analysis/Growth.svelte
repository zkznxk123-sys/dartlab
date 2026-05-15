<!--
	Growth — Analysis 성장성 axis specialized.
	응답: { growthTrend: { history: [{ period, revenue, revenueYoy, operatingIncome, operatingIncomeYoy, netIncome, netIncomeYoy, totalAssets, totalAssetsYoy }] } }
-->
<script>
	import LineTrend from "$lib/dashboard/chart/LineTrend.svelte";
	import BarTrend from "$lib/dashboard/chart/BarTrend.svelte";
	import KpiTile from "$lib/dashboard/chart/KpiTile.svelte";
	import { fmtPct, fmtKrw, isFiniteNum } from "$lib/dashboard/chart/util.js";

	let { payload = null, loading = false } = $props();

	const trend = $derived(payload?.growthTrend || null);
	const history = $derived(trend?.history || []);
	const latest = $derived(history[0] || null);
	const prev = $derived(history[1] || null);

	function delta(c, p) {
		if (!isFiniteNum(c) || !isFiniteNum(p)) return null;
		return c - p;
	}
</script>

{#if loading}
	<div class="ed-card"><div class="ed-eyebrow mb-2">Loading</div><div class="editorial-skeleton h-32 w-full"></div></div>
{:else if !trend}
	<div class="ed-card" style="border-style: dashed;"><div class="ed-eyebrow mb-1">No data</div><div class="text-[12px]" style="color: var(--ed-text-2);">growthTrend 데이터 없음</div></div>
{:else}
	<div class="grid grid-cols-4 gap-3 mb-4">
		<KpiTile label="매출 YoY" value={latest?.revenueYoy} delta={delta(latest?.revenueYoy, prev?.revenueYoy)} unit="%" />
		<KpiTile label="영업이익 YoY" value={latest?.operatingIncomeYoy} delta={delta(latest?.operatingIncomeYoy, prev?.operatingIncomeYoy)} unit="%" />
		<KpiTile label="순이익 YoY" value={latest?.netIncomeYoy} delta={delta(latest?.netIncomeYoy, prev?.netIncomeYoy)} unit="%" />
		<KpiTile label="자산 YoY" value={latest?.totalAssetsYoy} delta={delta(latest?.totalAssetsYoy, prev?.totalAssetsYoy)} unit="%" />
	</div>

	<div class="ed-card mb-4">
		<div class="ed-eyebrow mb-2">YoY Growth Trend</div>
		<LineTrend rows={history} xKey="period"
			series={[
				{ key: "revenueYoy", label: "매출", color: "var(--ed-text)" },
				{ key: "operatingIncomeYoy", label: "영업이익", color: "var(--ed-brand)" },
				{ key: "netIncomeYoy", label: "순이익", color: "var(--ed-up)" },
				{ key: "totalAssetsYoy", label: "자산", color: "var(--ed-text-2)" },
			]} height={260} unit="%" />
	</div>

	<div class="ed-card mb-4">
		<div class="ed-eyebrow mb-2">매출 YoY 막대</div>
		<BarTrend rows={history} xKey="period" yKey="revenueYoy" height={200} unit="%" />
	</div>

	<details class="ed-card">
		<summary class="cursor-pointer select-none ed-eyebrow">상세 표 — {history.length} 기간 full</summary>
		<div class="mt-3 overflow-x-auto max-h-96">
			<table class="w-full text-[11px]" style="font-family: var(--font-num);">
				<thead style="position: sticky; top: 0; background: var(--ed-surface);"><tr style="border-bottom: 1px solid var(--ed-line);">
					<th class="text-left p-1.5" style="color: var(--ed-text-3); font-weight: 600;">Period</th>
					<th class="text-right p-1.5" style="color: var(--ed-text-3); font-weight: 600;">Revenue</th>
					<th class="text-right p-1.5" style="color: var(--ed-text-3); font-weight: 600;">Rev YoY</th>
					<th class="text-right p-1.5" style="color: var(--ed-text-3); font-weight: 600;">OP</th>
					<th class="text-right p-1.5" style="color: var(--ed-text-3); font-weight: 600;">OP YoY</th>
					<th class="text-right p-1.5" style="color: var(--ed-text-3); font-weight: 600;">NI</th>
					<th class="text-right p-1.5" style="color: var(--ed-text-3); font-weight: 600;">NI YoY</th>
				</tr></thead>
				<tbody>
					{#each history as r}
						<tr style="border-bottom: 1px solid var(--ed-line);">
							<td class="p-1.5" style="color: var(--ed-text); font-weight: 500;">{r.period ?? ""}</td>
							<td class="p-1.5 text-right" style="color: var(--ed-text);">{fmtKrw(r.revenue)}</td>
							<td class="p-1.5 text-right" style="color: {isFiniteNum(r.revenueYoy) && r.revenueYoy >= 0 ? 'var(--ed-up)' : 'var(--ed-down)'};">{fmtPct(r.revenueYoy)}</td>
							<td class="p-1.5 text-right" style="color: var(--ed-text);">{fmtKrw(r.operatingIncome)}</td>
							<td class="p-1.5 text-right" style="color: {isFiniteNum(r.operatingIncomeYoy) && r.operatingIncomeYoy >= 0 ? 'var(--ed-up)' : 'var(--ed-down)'};">{fmtPct(r.operatingIncomeYoy)}</td>
							<td class="p-1.5 text-right" style="color: var(--ed-text);">{fmtKrw(r.netIncome)}</td>
							<td class="p-1.5 text-right" style="color: {isFiniteNum(r.netIncomeYoy) && r.netIncomeYoy >= 0 ? 'var(--ed-up)' : 'var(--ed-down)'};">{fmtPct(r.netIncomeYoy)}</td>
						</tr>
					{/each}
				</tbody>
			</table>
		</div>
	</details>
{/if}
