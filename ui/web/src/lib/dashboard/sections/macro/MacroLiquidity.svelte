<!--
	Macro > Liquidity — regime / score / signals / NFCI / FCI.
-->
<script>
	import { isFiniteNum } from "$lib/dashboard/chart/util.js";

	let { payload = null, loading = false } = $props();

	const regime = $derived(payload?.regime || "—");
	const regimeLabel = $derived(payload?.regimeLabel || payload?.regime || "—");
	const score = $derived(payload?.score);
	const signals = $derived(payload?.signals || {});
	const nfci = $derived(payload?.nfci);
	const fci = $derived(payload?.fci);
	const market = $derived(payload?.market || "—");

	const regimeColor = $derived(
		regime === "tight" || regime === "stress" ? "var(--ed-down)"
		: regime === "loose" || regime === "easy" ? "var(--ed-up)"
		: "var(--ed-text-2)"
	);
</script>

{#if loading}
	<div class="flex flex-col gap-3">{#each Array(2) as _}<div class="editorial-skeleton h-28"></div>{/each}</div>
{:else if !payload}
	<div class="ed-card" style="border-style: dashed;"><div class="ed-eyebrow">No data</div></div>
{:else}
	<div class="flex flex-col gap-3">
		<div class="ed-card">
			<div class="flex items-baseline justify-between mb-3">
				<div class="ed-eyebrow">Liquidity Regime · {market}</div>
			</div>
			<div class="flex items-baseline gap-10 flex-wrap">
				<div>
					<div class="text-[10px] uppercase tracking-wide" style="color: var(--ed-text-3);">Regime</div>
					<div class="text-[32px] font-bold leading-none mt-1" style="color: {regimeColor}; font-family: var(--font-display);">{regimeLabel}</div>
				</div>
				<div>
					<div class="text-[10px] uppercase tracking-wide" style="color: var(--ed-text-3);">Score</div>
					<div class="ed-num text-[28px] leading-none mt-1" style="color: var(--ed-text); font-family: var(--font-display);">{isFiniteNum(score) ? score.toFixed(2) : "—"}</div>
				</div>
				<div>
					<div class="text-[10px] uppercase tracking-wide" style="color: var(--ed-text-3);">NFCI</div>
					<div class="ed-num text-[20px] leading-none mt-1" style="color: var(--ed-text);">{isFiniteNum(nfci) ? nfci.toFixed(3) : "—"}</div>
				</div>
				<div>
					<div class="text-[10px] uppercase tracking-wide" style="color: var(--ed-text-3);">FCI</div>
					<div class="ed-num text-[20px] leading-none mt-1" style="color: var(--ed-text);">{isFiniteNum(fci) ? fci.toFixed(3) : "—"}</div>
				</div>
			</div>
		</div>

		{#if signals && typeof signals === "object" && Object.keys(signals).length > 0}
			<div class="ed-card">
				<div class="ed-eyebrow mb-3">유동성 시그널 ({Object.keys(signals).length})</div>
				<div class="grid grid-cols-2 md:grid-cols-4 gap-2">
					{#each Object.entries(signals) as [k, v]}
						<div class="rounded border p-2" style="border-color: var(--ed-line);">
							<div class="text-[10px] uppercase tracking-wide truncate" style="color: var(--ed-text-3);" title={k}>{k}</div>
							<div class="ed-num text-[12px] mt-1 truncate" style="color: var(--ed-text);">
								{typeof v === "number" ? (Number.isInteger(v) ? v : v.toFixed(3)) : (typeof v === "string" ? v : "—")}
							</div>
						</div>
					{/each}
				</div>
			</div>
		{/if}
	</div>
{/if}
