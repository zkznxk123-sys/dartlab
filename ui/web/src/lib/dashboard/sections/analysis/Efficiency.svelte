<!--
	Efficiency — Analysis 효율성 axis specialized.
	응답: { turnoverTrend: { history: [{ period, revenue, totalAssets, receivables, inventory, payables, totalAssetTurnover, receivablesTurnover, inventoryTurnover, dso, dio, dpo, ccc }] } }
-->
<script>
	import LineTrend from "$lib/dashboard/chart/LineTrend.svelte";
	import KpiTile from "$lib/dashboard/chart/KpiTile.svelte";
	import { fmtPct, fmtKrw, isFiniteNum } from "$lib/dashboard/chart/util.js";

	let { payload = null, loading = false } = $props();

	const trend = $derived(payload?.turnoverTrend || null);
	const history = $derived(trend?.history || []);
	const latest = $derived(history[0] || null);
	const prev = $derived(history[1] || null);

	function delta(c, p) {
		if (!isFiniteNum(c) || !isFiniteNum(p)) return null;
		return c - p;
	}

	function fmtDays(v) {
		if (!isFiniteNum(v)) return "—";
		return v.toFixed(0) + "일";
	}
	function fmtRatio(v) {
		if (!isFiniteNum(v)) return "—";
		return v.toFixed(2) + "x";
	}
</script>

{#if loading}
	<div class="ed-card"><div class="ed-eyebrow mb-2">Loading</div><div class="editorial-skeleton h-32 w-full"></div></div>
{:else if !trend}
	<div class="ed-card" style="border-style: dashed;"><div class="ed-eyebrow mb-1">No data</div><div class="text-[12px]" style="color: var(--ed-text-2);">turnoverTrend 데이터 없음</div></div>
{:else}
	<div class="grid grid-cols-4 gap-3 mb-4">
		<KpiTile label="CCC 현금주기" value={latest?.ccc} delta={delta(latest?.ccc, prev?.ccc)} unit="일" valueFormat={fmtDays} />
		<KpiTile label="DSO 매출회수" value={latest?.dso} delta={delta(latest?.dso, prev?.dso)} unit="일" valueFormat={fmtDays} />
		<KpiTile label="DIO 재고소진" value={latest?.dio} delta={delta(latest?.dio, prev?.dio)} unit="일" valueFormat={fmtDays} />
		<KpiTile label="총자산회전율" value={latest?.totalAssetTurnover} delta={delta(latest?.totalAssetTurnover, prev?.totalAssetTurnover)} unit="x" valueFormat={fmtRatio} />
	</div>

	<div class="ed-card mb-4">
		<div class="ed-eyebrow mb-2">CCC 구성 추이 (DSO · DIO · DPO · CCC)</div>
		<LineTrend rows={history} xKey="period"
			series={[
				{ key: "dso", label: "DSO (회수)", color: "var(--ed-text-2)" },
				{ key: "dio", label: "DIO (재고)", color: "var(--ed-warn)" },
				{ key: "dpo", label: "DPO (결제유예)", color: "var(--ed-up)" },
				{ key: "ccc", label: "CCC (순주기)", color: "var(--ed-brand)" },
			]} height={260} format={fmtDays} />
	</div>

	<div class="ed-card mb-4">
		<div class="ed-eyebrow mb-2">회전율 추이</div>
		<LineTrend rows={history} xKey="period"
			series={[
				{ key: "totalAssetTurnover", label: "총자산", color: "var(--ed-text)" },
				{ key: "receivablesTurnover", label: "매출채권", color: "var(--ed-up)" },
				{ key: "inventoryTurnover", label: "재고", color: "var(--ed-brand)" },
			]} height={220} format={fmtRatio} />
	</div>

	<details class="ed-card">
		<summary class="cursor-pointer select-none ed-eyebrow">상세 표 — {history.length} 기간 full</summary>
		<div class="mt-3 overflow-x-auto max-h-96">
			<table class="w-full text-[11px]" style="font-family: var(--font-num);">
				<thead style="position: sticky; top: 0; background: var(--ed-surface);"><tr style="border-bottom: 1px solid var(--ed-line);">
					<th class="text-left p-1.5" style="color: var(--ed-text-3); font-weight: 600;">Period</th>
					<th class="text-right p-1.5" style="color: var(--ed-text-3); font-weight: 600;">CCC</th>
					<th class="text-right p-1.5" style="color: var(--ed-text-3); font-weight: 600;">DSO</th>
					<th class="text-right p-1.5" style="color: var(--ed-text-3); font-weight: 600;">DIO</th>
					<th class="text-right p-1.5" style="color: var(--ed-text-3); font-weight: 600;">DPO</th>
					<th class="text-right p-1.5" style="color: var(--ed-text-3); font-weight: 600;">자산회전</th>
					<th class="text-right p-1.5" style="color: var(--ed-text-3); font-weight: 600;">매출채권회전</th>
					<th class="text-right p-1.5" style="color: var(--ed-text-3); font-weight: 600;">재고회전</th>
				</tr></thead>
				<tbody>
					{#each history as r}
						<tr style="border-bottom: 1px solid var(--ed-line);">
							<td class="p-1.5" style="color: var(--ed-text); font-weight: 500;">{r.period ?? ""}</td>
							<td class="p-1.5 text-right" style="color: {isFiniteNum(r.ccc) && r.ccc <= 90 ? 'var(--ed-up)' : 'var(--ed-down)'};">{fmtDays(r.ccc)}</td>
							<td class="p-1.5 text-right" style="color: var(--ed-text-2);">{fmtDays(r.dso)}</td>
							<td class="p-1.5 text-right" style="color: var(--ed-text-2);">{fmtDays(r.dio)}</td>
							<td class="p-1.5 text-right" style="color: var(--ed-text-2);">{fmtDays(r.dpo)}</td>
							<td class="p-1.5 text-right" style="color: var(--ed-text);">{fmtRatio(r.totalAssetTurnover)}</td>
							<td class="p-1.5 text-right" style="color: var(--ed-text-2);">{fmtRatio(r.receivablesTurnover)}</td>
							<td class="p-1.5 text-right" style="color: var(--ed-text-2);">{fmtRatio(r.inventoryTurnover)}</td>
						</tr>
					{/each}
				</tbody>
			</table>
		</div>
	</details>
{/if}
