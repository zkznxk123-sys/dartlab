<!--
	QuantMarketContext — { marketBeta, marketAlpha, correlation, rSquared, ... 25 keys }
-->
<script>
	import { isFiniteNum } from "$lib/dashboard/chart/util.js";

	let { payload = null, loading = false } = $props();

	const HERO = ["marketBeta", "marketAlpha", "correlation", "rSquared"];
	const META = ["stockCode", "market", "lookback", "lookbackDays", "dateRef", "lastClose"];

	function fmtRaw(v, digits = 3) {
		if (v == null) return "—";
		if (typeof v === "number") {
			if (!Number.isFinite(v)) return "—";
			if (Math.abs(v) >= 1e6) return v.toExponential(2);
			if (Number.isInteger(v) && Math.abs(v) < 1e4) return v.toString();
			return v.toFixed(digits);
		}
		return String(v);
	}

	const otherEntries = $derived(
		payload
			? Object.entries(payload).filter(([k]) => !HERO.includes(k) && !META.includes(k))
			: []
	);
</script>

{#if loading}
	<div class="flex flex-col gap-3">
		<div class="editorial-skeleton h-28"></div>
		<div class="editorial-skeleton h-40"></div>
	</div>
{:else if !payload}
	<div class="ed-card" style="border-style: dashed;"><div class="ed-eyebrow">No data</div></div>
{:else}
	<div class="flex flex-col gap-3">
		<!-- Hero CAPM -->
		<div class="ed-card">
			<div class="flex items-baseline justify-between mb-3">
				<div class="ed-eyebrow">Market Context · CAPM</div>
				<div class="text-[10px]" style="color: var(--ed-text-3);">
					{payload.market || "—"} · lookback {payload.lookback ?? payload.lookbackDays ?? "—"} · {payload.dateRef || "—"}
				</div>
			</div>
			<div class="grid grid-cols-2 md:grid-cols-4 gap-3">
				{#each HERO as k}
					<div class="rounded border p-3" style="border-color: var(--ed-line); background: var(--ed-surface-2);">
						<div class="text-[10px] uppercase tracking-wide" style="color: var(--ed-text-3);">{k.replace(/([A-Z])/g, " $1").trim()}</div>
						<div class="ed-num text-[22px] mt-1" style="color: var(--ed-text); font-family: var(--font-display);">{fmtRaw(payload[k])}</div>
					</div>
				{/each}
			</div>
		</div>

		<!-- All other CAPM 부수 지표 -->
		{#if otherEntries.length > 0}
			<div class="ed-card">
				<div class="ed-eyebrow mb-3">부수 지표 ({otherEntries.length})</div>
				<div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-2">
					{#each otherEntries as [k, v]}
						<div class="rounded border p-2" style="border-color: var(--ed-line);">
							<div class="text-[10px] uppercase tracking-wide truncate" style="color: var(--ed-text-3);" title={k}>{k}</div>
							<div class="ed-num text-[12px] mt-1 truncate" style="color: var(--ed-text);" title={typeof v === 'number' ? String(v) : ''}>{fmtRaw(v)}</div>
						</div>
					{/each}
				</div>
			</div>
		{/if}
	</div>
{/if}
