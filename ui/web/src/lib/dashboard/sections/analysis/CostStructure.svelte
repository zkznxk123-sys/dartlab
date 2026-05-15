<!--
	Analysis > 비용구조 — costBreakdown, operatingLeverage (DOL), breakevenEstimate (BEP).
-->
<script>
	import { isFiniteNum } from "$lib/dashboard/chart/util.js";
	import LineTrend from "$lib/dashboard/chart/LineTrend.svelte";

	let { payload = null, loading = false } = $props();

	const costHist = $derived(payload?.costBreakdown?.history || []);
	const dolHist = $derived(payload?.operatingLeverage?.history || []);
	const bepHist = $derived(payload?.breakevenEstimate?.history || []);
	const flags = $derived(Array.isArray(payload?.costStructureFlags) ? payload.costStructureFlags : []);

	const lastCost = $derived(costHist[costHist.length - 1] || {});
	const lastDol = $derived(dolHist[dolHist.length - 1] || {});
	const lastBep = $derived(bepHist[bepHist.length - 1] || {});
</script>

{#if loading}
	<div class="flex flex-col gap-3">{#each Array(3) as _}<div class="editorial-skeleton h-32"></div>{/each}</div>
{:else if !payload}
	<div class="ed-card" style="border-style: dashed;"><div class="ed-eyebrow">No data</div></div>
{:else}
	<div class="flex flex-col gap-3">
		<div class="grid grid-cols-2 md:grid-cols-4 gap-2">
			<div class="ed-card"><div class="ed-eyebrow">COGS / Rev</div><div class="ed-num text-[22px] mt-1" style="color: var(--ed-text);">{isFiniteNum(lastCost.costOfSalesRatio) ? (lastCost.costOfSalesRatio * 100).toFixed(1) + "%" : "—"}</div></div>
			<div class="ed-card"><div class="ed-eyebrow">SG&A / Rev</div><div class="ed-num text-[22px] mt-1" style="color: var(--ed-text);">{isFiniteNum(lastCost.sgaRatio) ? (lastCost.sgaRatio * 100).toFixed(1) + "%" : "—"}</div></div>
			<div class="ed-card"><div class="ed-eyebrow">DOL</div><div class="ed-num text-[22px] mt-1" style="color: {isFiniteNum(lastDol.dol) && Math.abs(lastDol.dol) > 3 ? 'var(--ed-down)' : 'var(--ed-text)'};">{isFiniteNum(lastDol.dol) ? lastDol.dol.toFixed(2) : "—"}</div></div>
			<div class="ed-card"><div class="ed-eyebrow">Margin of Safety</div><div class="ed-num text-[22px] mt-1" style="color: {isFiniteNum(lastBep.marginOfSafety) && lastBep.marginOfSafety < 0.1 ? 'var(--ed-down)' : 'var(--ed-text)'};">{isFiniteNum(lastBep.marginOfSafety) ? (lastBep.marginOfSafety * 100).toFixed(1) + "%" : "—"}</div></div>
		</div>

		{#if costHist.length > 0}
			<div class="ed-card">
				<div class="ed-eyebrow mb-2">COGS / SG&A 비중 · 추이</div>
				<LineTrend history={costHist} series={[
					{ key: "costOfSalesRatio", label: "COGS / Rev", color: "var(--ed-brand)", scale: 100 },
					{ key: "sgaRatio", label: "SG&A / Rev", color: "var(--ed-text-2)", scale: 100 },
				]} xKey="period" height={200} yIsPercent={true} />
			</div>
		{/if}

		{#if dolHist.length > 0}
			<div class="ed-card">
				<div class="ed-eyebrow mb-2">Degree of Operating Leverage · 추이</div>
				<LineTrend history={dolHist} series={[
					{ key: "dol", label: "DOL", color: "var(--ed-down)" },
				]} xKey="period" height={200} yIsPercent={false} />
			</div>
		{/if}

		{#if bepHist.length > 0}
			<div class="ed-card">
				<div class="ed-eyebrow mb-2">Breakeven Estimate · BEP vs Revenue</div>
				<LineTrend history={bepHist} series={[
					{ key: "revenue", label: "매출", color: "var(--ed-brand)" },
					{ key: "bepRevenue", label: "BEP 매출", color: "var(--ed-down)" },
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
