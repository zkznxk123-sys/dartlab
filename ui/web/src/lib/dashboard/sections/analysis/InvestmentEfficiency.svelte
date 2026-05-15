<!--
	Analysis > 투자효율 — roicTimeline + turningPoints, investmentIntensity, evaTimeline (NOPAT-WACC).
-->
<script>
	import { isFiniteNum } from "$lib/dashboard/chart/util.js";
	import LineTrend from "$lib/dashboard/chart/LineTrend.svelte";

	let { payload = null, loading = false } = $props();

	const roicHist = $derived(payload?.roicTimeline?.history || []);
	const turningPoints = $derived(Array.isArray(payload?.roicTimeline?.turningPoints) ? payload.roicTimeline.turningPoints : []);
	const intensityHist = $derived(payload?.investmentIntensity?.history || []);
	const evaHist = $derived(payload?.evaTimeline?.history || []);
	const flags = $derived(Array.isArray(payload?.investmentFlags) ? payload.investmentFlags : []);

	const lastRoic = $derived(roicHist[roicHist.length - 1] || {});
	const lastEva = $derived(evaHist[evaHist.length - 1] || {});

	const roicCurrent = $derived.by(() => {
		if (!lastRoic.nopat || !lastRoic.equity) return null;
		return (lastRoic.nopat / lastRoic.equity) * 100;
	});

	const evaPositive = $derived(isFiniteNum(lastEva.eva) && lastEva.eva > 0);
</script>

{#if loading}
	<div class="flex flex-col gap-3">{#each Array(3) as _}<div class="editorial-skeleton h-32"></div>{/each}</div>
{:else if !payload}
	<div class="ed-card" style="border-style: dashed;"><div class="ed-eyebrow">No data</div></div>
{:else}
	<div class="flex flex-col gap-3">
		<div class="grid grid-cols-2 md:grid-cols-4 gap-2">
			<div class="ed-card"><div class="ed-eyebrow">ROIC (approx)</div><div class="ed-num text-[22px] mt-1" style="color: {isFiniteNum(roicCurrent) && roicCurrent > 10 ? 'var(--ed-up)' : 'var(--ed-text)'};">{isFiniteNum(roicCurrent) ? roicCurrent.toFixed(1) + "%" : "—"}</div></div>
			<div class="ed-card"><div class="ed-eyebrow">NOPAT</div><div class="ed-num text-[18px] mt-1" style="color: var(--ed-text);">{isFiniteNum(lastRoic.nopat) ? (lastRoic.nopat / 1e8).toFixed(0) + "억" : "—"}</div></div>
			<div class="ed-card"><div class="ed-eyebrow">WACC</div><div class="ed-num text-[22px] mt-1" style="color: var(--ed-text);">{isFiniteNum(lastEva.waccEstimate) ? (lastEva.waccEstimate * 100).toFixed(2) + "%" : "—"}</div></div>
			<div class="ed-card"><div class="ed-eyebrow">EVA</div><div class="ed-num text-[18px] mt-1" style="color: {evaPositive ? 'var(--ed-up)' : 'var(--ed-down)'};">{isFiniteNum(lastEva.eva) ? (lastEva.eva / 1e8).toFixed(0) + "억" : "—"}</div></div>
		</div>

		{#if roicHist.length > 0}
			<div class="ed-card">
				<div class="ed-eyebrow mb-2">ROIC 시계열 · NOPAT vs Equity</div>
				<LineTrend history={roicHist} series={[
					{ key: "nopat", label: "NOPAT", color: "var(--ed-brand)" },
					{ key: "operatingIncome", label: "영업이익", color: "var(--ed-text-2)" },
				]} xKey="period" height={220} yIsPercent={false} />
			</div>
		{/if}

		{#if turningPoints.length > 0}
			<div class="ed-card">
				<div class="ed-eyebrow mb-2">전환점 ({turningPoints.length})</div>
				<ul class="flex flex-col gap-1.5">
					{#each turningPoints as tp}
						<li class="grid grid-cols-[80px_1fr_60px] items-center gap-2 px-2.5 py-1.5 rounded border text-[12px]"
							style="border-color: var(--ed-line); background: var(--ed-surface-2);">
							<span class="ed-num" style="color: var(--ed-text-3);">{tp.period || "—"}</span>
							<span style="color: var(--ed-text);">{tp.direction || "—"} · {tp.magnitude || "—"}</span>
							<span class="ed-num text-right" style="color: {tp.direction === 'up' ? 'var(--ed-up)' : tp.direction === 'down' ? 'var(--ed-down)' : 'var(--ed-text-2)'};">
								{isFiniteNum(tp.deltaPct) ? (tp.deltaPct > 0 ? "+" : "") + tp.deltaPct.toFixed(1) + "%" : "—"}
							</span>
						</li>
					{/each}
				</ul>
			</div>
		{/if}

		{#if evaHist.length > 0}
			<div class="ed-card">
				<div class="ed-eyebrow mb-2">EVA Timeline · NOPAT return vs WACC</div>
				<LineTrend history={evaHist} series={[
					{ key: "nopatReturn", label: "NOPAT Return", color: "var(--ed-up)", scale: 100 },
					{ key: "waccEstimate", label: "WACC", color: "var(--ed-down)", scale: 100 },
				]} xKey="period" height={220} yIsPercent={true} />
			</div>
		{/if}

		{#if intensityHist.length > 0}
			<div class="ed-card">
				<div class="ed-eyebrow mb-2">투자 강도 · capex / 자산</div>
				<LineTrend history={intensityHist} series={[
					{ key: "capex", label: "Capex", color: "var(--ed-brand)" },
				]} xKey="period" height={200} yIsPercent={false} />
			</div>
		{/if}

		{#if flags.length > 0}
			<div class="ed-card"><div class="ed-eyebrow mb-2">Flags ({flags.length})</div>
				<ul class="flex flex-col gap-1.5 text-[12px]">{#each flags as f}<li style="color: var(--ed-text-2);">{typeof f === 'string' ? f : (f.message || JSON.stringify(f))}</li>{/each}</ul>
			</div>
		{/if}
	</div>
{/if}
