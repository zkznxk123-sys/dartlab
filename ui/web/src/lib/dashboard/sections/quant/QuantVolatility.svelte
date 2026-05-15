<!--
	QuantVolatility — Realized vol 5/20/60/120d + HAR-RV + 추가 지표 KPI grid.
-->
<script>
	import { isFiniteNum } from "$lib/dashboard/chart/util.js";

	let { payload = null, loading = false } = $props();

	const PRIMARY = ["realizedVol_5d", "realizedVol_20d", "realizedVol_60d", "realizedVol_120d"];
	const HAR_KEYS = ["harRV", "harRV_predicted", "harDaily", "harWeekly", "harMonthly"];
	const META_KEYS = ["stockCode", "market", "dataPoints"];

	function fmtVol(v) {
		if (!isFiniteNum(v)) return "—";
		// realized vol 은 annualized fraction (0.35 = 35%)
		if (Math.abs(v) <= 5) return (v * 100).toFixed(2) + "%";
		return v.toFixed(2);
	}

	function fmtRaw(v) {
		if (v == null) return "—";
		if (typeof v === "number") {
			if (!Number.isFinite(v)) return "—";
			if (Math.abs(v) >= 1e6) return v.toExponential(2);
			if (Math.abs(v) <= 5) return (v * 100).toFixed(2) + "%";
			return v.toFixed(3);
		}
		return String(v);
	}

	const otherEntries = $derived(
		payload
			? Object.entries(payload).filter(([k]) => !PRIMARY.includes(k) && !HAR_KEYS.includes(k) && !META_KEYS.includes(k))
			: []
	);
</script>

{#if loading}
	<div class="flex flex-col gap-3">
		<div class="grid grid-cols-4 gap-2">{#each Array(4) as _}<div class="editorial-skeleton h-20"></div>{/each}</div>
		<div class="editorial-skeleton h-40"></div>
	</div>
{:else if !payload}
	<div class="ed-card" style="border-style: dashed;"><div class="ed-eyebrow">No data</div></div>
{:else}
	<div class="flex flex-col gap-3">
		<!-- Hero KPI: 4 horizon RV -->
		<div class="ed-card">
			<div class="flex items-baseline justify-between mb-3">
				<div class="ed-eyebrow">Realized Volatility · annualized</div>
				<div class="text-[10px]" style="color: var(--ed-text-3);">
					{payload.market || "—"} · {payload.dataPoints ?? "—"} obs
				</div>
			</div>
			<div class="grid grid-cols-2 md:grid-cols-4 gap-3">
				{#each PRIMARY as k}
					<div class="rounded border p-3" style="border-color: var(--ed-line); background: var(--ed-surface-2);">
						<div class="text-[10px] uppercase tracking-wide" style="color: var(--ed-text-3);">{k.replace("realizedVol_", "RV ").toUpperCase()}</div>
						<div class="ed-num text-[24px] mt-1" style="color: var(--ed-text); font-family: var(--font-display);">{fmtVol(payload[k])}</div>
					</div>
				{/each}
			</div>
		</div>

		<!-- HAR-RV 분해 -->
		{#if HAR_KEYS.some((k) => payload[k] !== undefined)}
			<div class="ed-card">
				<div class="ed-eyebrow mb-3">HAR-RV 분해</div>
				<div class="grid grid-cols-2 md:grid-cols-5 gap-2">
					{#each HAR_KEYS as k}
						{#if payload[k] !== undefined}
							<div class="rounded border p-2.5" style="border-color: var(--ed-line); background: var(--ed-surface-2);">
								<div class="text-[10px] uppercase tracking-wide truncate" style="color: var(--ed-text-3);" title={k}>{k}</div>
								<div class="ed-num text-[14px] mt-1" style="color: var(--ed-text);">{fmtRaw(payload[k])}</div>
							</div>
						{/if}
					{/each}
				</div>
			</div>
		{/if}

		<!-- 기타 지표 -->
		{#if otherEntries.length > 0}
			<div class="ed-card">
				<div class="ed-eyebrow mb-3">추가 지표 ({otherEntries.length})</div>
				<div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-2">
					{#each otherEntries as [k, v]}
						<div class="rounded border p-2" style="border-color: var(--ed-line);">
							<div class="text-[10px] uppercase tracking-wide truncate" style="color: var(--ed-text-3);" title={k}>{k}</div>
							<div class="ed-num text-[12px] mt-1 truncate" style="color: var(--ed-text);">{fmtRaw(v)}</div>
						</div>
					{/each}
				</div>
			</div>
		{/if}
	</div>
{/if}
