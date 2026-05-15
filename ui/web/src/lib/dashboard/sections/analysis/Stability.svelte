<!--
	Stability — Analysis 안정성 axis specialized.
	응답: { leverageTrend: { history: [{ period, totalDebt, equity, totalAssets, cash, totalBorrowing, netDebt, debtRatio, equityRatio, netDebtRatio, totalDebtYoy, equityYoy }] } }
-->
<script>
	import LineTrend from "$lib/dashboard/chart/LineTrend.svelte";
	import StackedBarTrend from "$lib/dashboard/chart/StackedBarTrend.svelte";
	import KpiTile from "$lib/dashboard/chart/KpiTile.svelte";
	import { fmtPct, fmtKrw, isFiniteNum } from "$lib/dashboard/chart/util.js";

	let { payload = null, loading = false } = $props();

	const trend = $derived(payload?.leverageTrend || null);
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
	<div class="ed-card" style="border-style: dashed;"><div class="ed-eyebrow mb-1">No data</div><div class="text-[12px]" style="color: var(--ed-text-2);">leverageTrend 데이터 없음</div></div>
{:else}
	<div class="grid grid-cols-4 gap-3 mb-4">
		<KpiTile label="부채비율 D/E" value={latest?.debtRatio} delta={delta(latest?.debtRatio, prev?.debtRatio)} unit="%" />
		<KpiTile label="자기자본비율" value={latest?.equityRatio} delta={delta(latest?.equityRatio, prev?.equityRatio)} unit="%" />
		<KpiTile label="순부채비율" value={latest?.netDebtRatio} delta={delta(latest?.netDebtRatio, prev?.netDebtRatio)} unit="%" />
		<KpiTile label="순부채 NetDebt" value={latest?.netDebt} delta={delta(latest?.netDebt, prev?.netDebt)} unit="KRW" />
	</div>

	<div class="ed-card mb-4">
		<div class="ed-eyebrow mb-2">Leverage Ratio Trend</div>
		<LineTrend rows={history} xKey="period"
			series={[
				{ key: "debtRatio", label: "부채비율 D/E", color: "var(--ed-down)" },
				{ key: "equityRatio", label: "자기자본비율", color: "var(--ed-up)" },
				{ key: "netDebtRatio", label: "순부채비율", color: "var(--ed-brand)" },
			]} height={260} unit="%" />
	</div>

	<div class="ed-card mb-4">
		<div class="ed-eyebrow mb-2">자본 구성 stacked (Equity vs Total Debt)</div>
		<StackedBarTrend rows={history} xKey="period"
			series={[
				{ key: "equity", label: "Equity", color: "var(--ed-up)" },
				{ key: "totalDebt", label: "Total Debt", color: "var(--ed-down)" },
			]} height={240} unit="KRW" />
	</div>

	<details class="ed-card">
		<summary class="cursor-pointer select-none ed-eyebrow">상세 표 — {history.length} 기간 full</summary>
		<div class="mt-3 overflow-x-auto max-h-96">
			<table class="w-full text-[11px]" style="font-family: var(--font-num);">
				<thead style="position: sticky; top: 0; background: var(--ed-surface);"><tr style="border-bottom: 1px solid var(--ed-line);">
					<th class="text-left p-1.5" style="color: var(--ed-text-3); font-weight: 600;">Period</th>
					<th class="text-right p-1.5" style="color: var(--ed-text-3); font-weight: 600;">Total Debt</th>
					<th class="text-right p-1.5" style="color: var(--ed-text-3); font-weight: 600;">Equity</th>
					<th class="text-right p-1.5" style="color: var(--ed-text-3); font-weight: 600;">Cash</th>
					<th class="text-right p-1.5" style="color: var(--ed-text-3); font-weight: 600;">Net Debt</th>
					<th class="text-right p-1.5" style="color: var(--ed-text-3); font-weight: 600;">D/E</th>
					<th class="text-right p-1.5" style="color: var(--ed-text-3); font-weight: 600;">Equity %</th>
				</tr></thead>
				<tbody>
					{#each history as r}
						<tr style="border-bottom: 1px solid var(--ed-line);">
							<td class="p-1.5" style="color: var(--ed-text); font-weight: 500;">{r.period ?? ""}</td>
							<td class="p-1.5 text-right" style="color: var(--ed-down);">{fmtKrw(r.totalDebt)}</td>
							<td class="p-1.5 text-right" style="color: var(--ed-up);">{fmtKrw(r.equity)}</td>
							<td class="p-1.5 text-right" style="color: var(--ed-text);">{fmtKrw(r.cash)}</td>
							<td class="p-1.5 text-right" style="color: {isFiniteNum(r.netDebt) && r.netDebt < 0 ? 'var(--ed-up)' : 'var(--ed-down)'};">{fmtKrw(r.netDebt)}</td>
							<td class="p-1.5 text-right" style="color: var(--ed-text-2);">{fmtPct(r.debtRatio)}</td>
							<td class="p-1.5 text-right" style="color: var(--ed-text-2);">{fmtPct(r.equityRatio)}</td>
						</tr>
					{/each}
				</tbody>
			</table>
		</div>
	</details>
{/if}
