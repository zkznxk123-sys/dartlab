<!--
	Analysis > 자금조달 — fundingSources, netDebtEbitda, impliedBorrowingRate, distressIndicators.
-->
<script>
	import { isFiniteNum } from "$lib/dashboard/chart/util.js";
	import LineTrend from "$lib/dashboard/chart/LineTrend.svelte";

	let { payload = null, loading = false } = $props();

	const fs = $derived(payload?.fundingSources || null);
	const latest = $derived(fs?.latest || {});
	const hist = $derived(fs?.history || []);
	const diagnosis = $derived(fs?.diagnosis || "");
	const netDebtEbitda = $derived(fs?.netDebtEbitda);
	const impliedRate = $derived(fs?.impliedBorrowingRate);
	const distress = $derived(payload?.distressIndicators || null);
	const liquidityM = $derived(payload?.liquidity?.metrics || []);
</script>

{#if loading}
	<div class="flex flex-col gap-3">{#each Array(3) as _}<div class="editorial-skeleton h-28"></div>{/each}</div>
{:else if !payload}
	<div class="ed-card" style="border-style: dashed;"><div class="ed-eyebrow">No data</div></div>
{:else}
	<div class="flex flex-col gap-3">
		<!-- KPI -->
		<div class="grid grid-cols-2 md:grid-cols-4 gap-2">
			<div class="ed-card"><div class="ed-eyebrow">Net Debt / EBITDA</div><div class="ed-num text-[24px] mt-1" style="color: {isFiniteNum(netDebtEbitda) && netDebtEbitda > 3 ? 'var(--ed-down)' : 'var(--ed-text)'};">{isFiniteNum(netDebtEbitda) ? netDebtEbitda.toFixed(2) : "—"}<span class="text-[10px]" style="color: var(--ed-text-3);">x</span></div></div>
			<div class="ed-card"><div class="ed-eyebrow">Implied Borrow Rate</div><div class="ed-num text-[24px] mt-1" style="color: var(--ed-text);">{isFiniteNum(impliedRate) ? impliedRate.toFixed(2) + "%" : "—"}</div></div>
			<div class="ed-card"><div class="ed-eyebrow">Retained %</div><div class="ed-num text-[24px] mt-1" style="color: var(--ed-text);">{isFiniteNum(latest.retainedPct) ? latest.retainedPct.toFixed(1) + "%" : "—"}</div></div>
			<div class="ed-card"><div class="ed-eyebrow">Fin Debt %</div><div class="ed-num text-[24px] mt-1" style="color: {isFiniteNum(latest.finDebtPct) && latest.finDebtPct > 50 ? 'var(--ed-down)' : 'var(--ed-text)'};">{isFiniteNum(latest.finDebtPct) ? latest.finDebtPct.toFixed(1) + "%" : "—"}</div></div>
		</div>

		{#if diagnosis}
			<div class="ed-card"><div class="text-[12px]" style="color: var(--ed-text-2);">{diagnosis}</div></div>
		{/if}

		{#if hist.length > 0}
			<div class="ed-card">
				<div class="ed-eyebrow mb-2">자금조달 구성 · 추이 (%)</div>
				<LineTrend history={hist} series={[
					{ key: "retainedPct", label: "유보", color: "var(--ed-up)" },
					{ key: "paidInPct", label: "납입자본", color: "var(--ed-brand)" },
					{ key: "finDebtPct", label: "금융부채", color: "var(--ed-down)" },
					{ key: "opFundingPct", label: "영업조달", color: "var(--ed-text-2)" },
					{ key: "otherLiabPct", label: "기타부채", color: "var(--ed-text-3)" },
				]} xKey="period" height={240} yIsPercent={true} />
			</div>
		{/if}

		{#if liquidityM.length > 0}
			<div class="ed-card">
				<div class="ed-eyebrow mb-2">유동성 지표 ({liquidityM.length})</div>
				<div class="grid grid-cols-2 md:grid-cols-4 gap-2">
					{#each liquidityM as m}
						<div class="rounded border p-2" style="border-color: var(--ed-line);">
							<div class="text-[10px] uppercase tracking-wide truncate" style="color: var(--ed-text-3);">{m.name ?? "—"}</div>
							<div class="ed-num text-[14px] mt-1" style="color: var(--ed-text);">{isFiniteNum(m.value) ? m.value.toFixed(2) : (m.value ?? "—")}</div>
						</div>
					{/each}
				</div>
			</div>
		{/if}

		{#if distress && Array.isArray(distress.flags) && distress.flags.length > 0}
			<div class="ed-card" style="border-color: var(--ed-down);">
				<div class="ed-eyebrow mb-2" style="color: var(--ed-down);">Distress Indicators</div>
				<ul class="flex flex-col gap-1.5 text-[12px]">{#each distress.flags as f}<li style="color: var(--ed-text-2);">{typeof f === 'string' ? f : (f.message || JSON.stringify(f))}</li>{/each}</ul>
			</div>
		{/if}
	</div>
{/if}
