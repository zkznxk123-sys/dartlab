<!--
	Analysis > 재무정합성 — IS/CF divergence, IS/BS divergence, anomalyScore, effectiveTaxRate, deferredTax.
-->
<script>
	import { isFiniteNum } from "$lib/dashboard/chart/util.js";
	import LineTrend from "$lib/dashboard/chart/LineTrend.svelte";

	let { payload = null, loading = false } = $props();

	const cfDivHist = $derived(payload?.isCfDivergence?.history || []);
	const bsDivHist = $derived(payload?.isBsDivergence?.history || []);
	const anomalyHist = $derived(payload?.anomalyScore?.history || []);
	const taxHist = $derived(payload?.effectiveTaxRate?.history || []);
	const deferredHist = $derived(payload?.deferredTax?.history || []);
	const articulation = $derived(payload?.articulationCheck || null);

	const lastAnomaly = $derived(anomalyHist[anomalyHist.length - 1] || {});
	const lastTax = $derived(taxHist[taxHist.length - 1] || {});
	const lastCfDiv = $derived(cfDivHist[cfDivHist.length - 1] || {});
</script>

{#if loading}
	<div class="flex flex-col gap-3">{#each Array(3) as _}<div class="editorial-skeleton h-32"></div>{/each}</div>
{:else if !payload}
	<div class="ed-card" style="border-style: dashed;"><div class="ed-eyebrow">No data</div></div>
{:else}
	<div class="flex flex-col gap-3">
		<div class="grid grid-cols-2 md:grid-cols-4 gap-2">
			<div class="ed-card"><div class="ed-eyebrow">Anomaly Score</div><div class="ed-num text-[24px] mt-1" style="color: {isFiniteNum(lastAnomaly.score) && lastAnomaly.score >= 80 ? 'var(--ed-up)' : isFiniteNum(lastAnomaly.score) && lastAnomaly.score < 50 ? 'var(--ed-down)' : 'var(--ed-text)'};">{isFiniteNum(lastAnomaly.score) ? lastAnomaly.score.toFixed(0) : "—"}</div></div>
			<div class="ed-card"><div class="ed-eyebrow">IS-CF Divergence</div><div class="ed-num text-[22px] mt-1" style="color: {isFiniteNum(lastCfDiv.divergence) && Math.abs(lastCfDiv.divergence) > 50 ? 'var(--ed-down)' : 'var(--ed-text)'};">{isFiniteNum(lastCfDiv.divergence) ? lastCfDiv.divergence.toFixed(1) + "%" : "—"}</div></div>
			<div class="ed-card"><div class="ed-eyebrow">Effective Tax</div><div class="ed-num text-[22px] mt-1" style="color: var(--ed-text);">{isFiniteNum(lastTax.effectiveTaxRate) ? (lastTax.effectiveTaxRate * 100).toFixed(1) + "%" : "—"}</div></div>
			<div class="ed-card"><div class="ed-eyebrow">Tax Gap (vs statutory)</div><div class="ed-num text-[22px] mt-1" style="color: {isFiniteNum(lastTax.taxGap) && Math.abs(lastTax.taxGap) > 0.1 ? 'var(--ed-down)' : 'var(--ed-text)'};">{isFiniteNum(lastTax.taxGap) ? (lastTax.taxGap * 100).toFixed(1) + "%" : "—"}</div></div>
		</div>

		{#if cfDivHist.length > 0}
			<div class="ed-card">
				<div class="ed-eyebrow mb-2">IS-CF Divergence · netIncome vs OCF</div>
				<LineTrend history={cfDivHist} series={[
					{ key: "netIncome", label: "Net Income", color: "var(--ed-brand)" },
					{ key: "ocf", label: "OCF", color: "var(--ed-up)" },
				]} xKey="period" height={220} yIsPercent={false} />
			</div>
		{/if}

		{#if bsDivHist.length > 0}
			<div class="ed-card">
				<div class="ed-eyebrow mb-2">IS-BS Divergence · 매출 vs 매출채권 / 재고 성장</div>
				<LineTrend history={bsDivHist} series={[
					{ key: "revenueGrowth", label: "매출 성장", color: "var(--ed-brand)", scale: 100 },
					{ key: "receivableGrowth", label: "채권 성장", color: "var(--ed-text-2)", scale: 100 },
					{ key: "inventoryGrowth", label: "재고 성장", color: "var(--ed-down)", scale: 100 },
				]} xKey="period" height={220} yIsPercent={true} />
			</div>
		{/if}

		{#if anomalyHist.length > 0}
			<div class="ed-card">
				<div class="ed-eyebrow mb-2">Anomaly Score · 추이</div>
				<LineTrend history={anomalyHist} series={[
					{ key: "score", label: "Score", color: "var(--ed-brand)" },
				]} xKey="period" height={200} yIsPercent={false} />
			</div>
		{/if}

		{#if taxHist.length > 0}
			<div class="ed-card">
				<div class="ed-eyebrow mb-2">Effective Tax Rate · 추이</div>
				<LineTrend history={taxHist} series={[
					{ key: "effectiveTaxRate", label: "실효세율", color: "var(--ed-brand)", scale: 100 },
					{ key: "statutoryRate", label: "법정세율", color: "var(--ed-text-3)", scale: 100 },
				]} xKey="period" height={200} yIsPercent={true} />
			</div>
		{/if}

		{#if articulation && typeof articulation === "object" && Object.keys(articulation).length > 0}
			<details class="ed-card">
				<summary class="cursor-pointer select-none ed-eyebrow" style="color: var(--ed-text-3);">Articulation check ({Object.keys(articulation).length})</summary>
				<pre class="text-[11px] mt-3 overflow-x-auto" style="color: var(--ed-text-2);">{JSON.stringify(articulation, null, 2)}</pre>
			</details>
		{/if}
	</div>
{/if}
