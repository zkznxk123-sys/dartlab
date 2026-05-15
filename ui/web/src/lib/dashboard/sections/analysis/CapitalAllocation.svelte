<!--
	Analysis > 자본배분 — dividendPolicy / shareholderReturn / reinvestment / fcfUsage.
-->
<script>
	import { isFiniteNum } from "$lib/dashboard/chart/util.js";
	import LineTrend from "$lib/dashboard/chart/LineTrend.svelte";

	let { payload = null, loading = false } = $props();

	const divHist = $derived(payload?.dividendPolicy?.history || []);
	const consecutive = $derived(payload?.dividendPolicy?.consecutiveYears);
	const retHist = $derived(payload?.shareholderReturn?.history || []);
	const reinvHist = $derived(payload?.reinvestment?.history || []);
	const fcfHist = $derived(payload?.fcfUsage?.history || []);
	const docs = $derived(payload?.dividendDocs || {});
	const treasury = $derived(payload?.treasuryStockStatus || null);
	const flags = $derived(Array.isArray(payload?.capitalAllocationFlags) ? payload.capitalAllocationFlags : []);

	const lastDiv = $derived(divHist[divHist.length - 1] || {});
	const lastReinv = $derived(reinvHist[reinvHist.length - 1] || {});
</script>

{#if loading}
	<div class="flex flex-col gap-3">{#each Array(3) as _}<div class="editorial-skeleton h-32"></div>{/each}</div>
{:else if !payload}
	<div class="ed-card" style="border-style: dashed;"><div class="ed-eyebrow">No data</div></div>
{:else}
	<div class="flex flex-col gap-3">
		<div class="grid grid-cols-2 md:grid-cols-4 gap-2">
			<div class="ed-card"><div class="ed-eyebrow">Payout Ratio</div><div class="ed-num text-[22px] mt-1" style="color: var(--ed-text);">{isFiniteNum(docs.payoutRatio) ? docs.payoutRatio.toFixed(1) + "%" : isFiniteNum(lastDiv.payoutRatio) ? lastDiv.payoutRatio.toFixed(1) + "%" : "—"}</div></div>
			<div class="ed-card"><div class="ed-eyebrow">DPS</div><div class="ed-num text-[22px] mt-1" style="color: var(--ed-text);">{isFiniteNum(docs.dps) ? docs.dps.toLocaleString() : "—"}</div></div>
			<div class="ed-card"><div class="ed-eyebrow">Div Yield</div><div class="ed-num text-[22px] mt-1" style="color: var(--ed-text);">{isFiniteNum(docs.dividendYield) ? docs.dividendYield.toFixed(2) + "%" : "—"}</div></div>
			<div class="ed-card"><div class="ed-eyebrow">Consecutive</div><div class="ed-num text-[22px] mt-1" style="color: {consecutive >= 5 ? 'var(--ed-up)' : 'var(--ed-text)'};">{consecutive ?? "—"}<span class="text-[10px]" style="color: var(--ed-text-3);">y</span></div></div>
		</div>

		{#if divHist.length > 0}
			<div class="ed-card">
				<div class="ed-eyebrow mb-2">배당정책 · 추이</div>
				<LineTrend history={divHist} series={[
					{ key: "payoutRatio", label: "Payout %", color: "var(--ed-brand)" },
					{ key: "dividendGrowth", label: "DPS 성장 %", color: "var(--ed-up)" },
				]} xKey="period" height={200} yIsPercent={true} />
			</div>
		{/if}

		{#if retHist.length > 0}
			<div class="ed-card">
				<div class="ed-eyebrow mb-2">주주환원 / FCF</div>
				<LineTrend history={retHist} series={[
					{ key: "returnToFcf", label: "환원 / FCF", color: "var(--ed-brand)" },
				]} xKey="period" height={200} yIsPercent={false} />
			</div>
		{/if}

		{#if reinvHist.length > 0}
			<div class="ed-card">
				<div class="ed-eyebrow mb-2">재투자 · capex/revenue · retention</div>
				<LineTrend history={reinvHist} series={[
					{ key: "capexToRevenue", label: "Capex / Rev", color: "var(--ed-brand)", scale: 100 },
					{ key: "retentionRate", label: "Retention", color: "var(--ed-text-2)", scale: 100 },
				]} xKey="period" height={200} yIsPercent={true} />
			</div>
		{/if}

		{#if fcfHist.length > 0}
			<div class="ed-card">
				<div class="ed-eyebrow mb-2">FCF 사용처 · dividend / debt repay / residual</div>
				<LineTrend history={fcfHist} series={[
					{ key: "dividendsPaid", label: "배당지급", color: "var(--ed-brand)" },
					{ key: "debtRepaid", label: "부채상환", color: "var(--ed-text-2)" },
					{ key: "residual", label: "잔여", color: "var(--ed-text-3)" },
				]} xKey="period" height={220} yIsPercent={false} />
			</div>
		{/if}

		{#if flags.length > 0}
			<div class="ed-card"><div class="ed-eyebrow mb-2">Flags ({flags.length})</div>
				<ul class="flex flex-col gap-1.5 text-[12px]">{#each flags as f}<li style="color: var(--ed-text-2);">{typeof f === 'string' ? f : (f.message || JSON.stringify(f))}</li>{/each}</ul>
			</div>
		{/if}
	</div>
{/if}
