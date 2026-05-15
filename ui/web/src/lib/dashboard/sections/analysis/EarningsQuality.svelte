<!--
	Analysis > 이익품질 — accrual / persistence / Beneish M-score / anomalies.
-->
<script>
	import { isFiniteNum, fmtPct } from "$lib/dashboard/chart/util.js";
	import LineTrend from "$lib/dashboard/chart/LineTrend.svelte";

	let { payload = null, loading = false } = $props();

	const accrualHist = $derived(payload?.accrualAnalysis?.history || []);
	const persistHist = $derived(payload?.earningsPersistence?.history || []);
	const earningsVol = $derived(payload?.earningsPersistence?.earningsVolatility);
	const beneishHist = $derived(payload?.beneishMScore?.history || []);
	const beneishThreshold = $derived(payload?.beneishMScore?.threshold ?? -1.78);
	const qualityAnomalies = $derived(payload?.qualityAnomalies || null);
	const anomalyScore = $derived(qualityAnomalies?.score);
	const flags = $derived(Array.isArray(payload?.earningsQualityFlags?.flags) ? payload.earningsQualityFlags.flags : []);
	const sloanQuintile = $derived(qualityAnomalies?.sloan?.quintile || "—");
	const beneishLatest = $derived(beneishHist.length > 0 ? beneishHist[beneishHist.length - 1]?.mScore : null);
</script>

{#if loading}
	<div class="flex flex-col gap-3">{#each Array(3) as _}<div class="editorial-skeleton h-32"></div>{/each}</div>
{:else if !payload}
	<div class="ed-card" style="border-style: dashed;"><div class="ed-eyebrow">No data</div></div>
{:else}
	<div class="flex flex-col gap-3">
		<!-- KPI -->
		<div class="grid grid-cols-2 md:grid-cols-4 gap-2">
			<div class="ed-card"><div class="ed-eyebrow">Anomaly Score</div><div class="ed-num text-[26px] mt-1" style="color: {isFiniteNum(anomalyScore) && anomalyScore >= 80 ? 'var(--ed-up)' : isFiniteNum(anomalyScore) && anomalyScore < 50 ? 'var(--ed-down)' : 'var(--ed-text)'};">{isFiniteNum(anomalyScore) ? anomalyScore.toFixed(0) : "—"}</div><div class="text-[9.5px]" style="color: var(--ed-text-3);">100 = no anomaly</div></div>
			<div class="ed-card"><div class="ed-eyebrow">Beneish M</div><div class="ed-num text-[26px] mt-1" style="color: {isFiniteNum(beneishLatest) && beneishLatest > beneishThreshold ? 'var(--ed-down)' : 'var(--ed-text)'};">{isFiniteNum(beneishLatest) ? beneishLatest.toFixed(2) : "—"}</div><div class="text-[9.5px]" style="color: var(--ed-text-3);">> {beneishThreshold} 위험</div></div>
			<div class="ed-card"><div class="ed-eyebrow">Sloan Q</div><div class="text-[20px] font-bold mt-1" style="color: var(--ed-text); font-family: var(--font-display);">{sloanQuintile}</div><div class="text-[9.5px]" style="color: var(--ed-text-3);">accrual quintile</div></div>
			<div class="ed-card"><div class="ed-eyebrow">Earnings Vol</div><div class="ed-num text-[26px] mt-1" style="color: var(--ed-text);">{isFiniteNum(earningsVol) ? earningsVol.toFixed(3) : "—"}</div><div class="text-[9.5px]" style="color: var(--ed-text-3);">σ of OP income</div></div>
		</div>

		<!-- Accrual ratio trend -->
		{#if accrualHist.length > 0}
			<div class="ed-card">
				<div class="ed-eyebrow mb-2">Sloan Accrual Ratio · 추이</div>
				<LineTrend history={accrualHist} series={[
					{ key: "sloanAccrualRatio", label: "Sloan Accrual", color: "var(--ed-brand)" },
					{ key: "accrualToRevenue", label: "Accrual / Revenue", color: "var(--ed-text-3)" },
				]} xKey="period" height={200} yIsPercent={false} />
			</div>
		{/if}

		<!-- Beneish M trend -->
		{#if beneishHist.length > 0}
			<div class="ed-card">
				<div class="ed-eyebrow mb-2">Beneish M-Score · 추이 (threshold {beneishThreshold})</div>
				<LineTrend history={beneishHist} series={[
					{ key: "mScore", label: "M-Score", color: "var(--ed-down)" },
				]} xKey="period" height={200} yIsPercent={false} />
			</div>
		{/if}

		<!-- Earnings persistence -->
		{#if persistHist.length > 0}
			<div class="ed-card">
				<div class="ed-eyebrow mb-2">Earnings Persistence · 영업 vs 비영업</div>
				<LineTrend history={persistHist} series={[
					{ key: "operatingIncome", label: "영업이익", color: "var(--ed-brand)" },
					{ key: "nonOperatingIncome", label: "비영업", color: "var(--ed-text-3)" },
					{ key: "preTaxIncome", label: "세전", color: "var(--ed-text-2)" },
				]} xKey="period" height={200} yIsPercent={false} />
			</div>
		{/if}

		{#if flags.length > 0}
			<div class="ed-card" style="border-color: var(--ed-down);">
				<div class="ed-eyebrow mb-2" style="color: var(--ed-down);">Earnings Quality Flags ({flags.length})</div>
				<ul class="flex flex-col gap-1.5 text-[12px]">{#each flags as f}<li style="color: var(--ed-text-2);">{typeof f === 'string' ? f : (f.message || JSON.stringify(f))}</li>{/each}</ul>
			</div>
		{/if}
	</div>
{/if}
