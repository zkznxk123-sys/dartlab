<!--
	Macro > Sentiment — fearGreed / vixRegime / timeseries.
-->
<script>
	import { isFiniteNum } from "$lib/dashboard/chart/util.js";

	let { payload = null, loading = false } = $props();

	const fg = $derived(payload?.fearGreed || null);
	const vix = $derived(payload?.vixRegime || null);
	const ts = $derived(payload?.timeseries || null);
	const market = $derived(payload?.market || "—");

	function fgColor(v) {
		if (!isFiniteNum(v)) return "var(--ed-text-3)";
		if (v < 25) return "var(--ed-down)";
		if (v < 50) return "var(--ed-text-2)";
		if (v < 75) return "var(--ed-up)";
		return "var(--ed-brand)";
	}

	function fgLabel(v) {
		if (!isFiniteNum(v)) return "—";
		if (v < 25) return "Extreme Fear";
		if (v < 45) return "Fear";
		if (v < 55) return "Neutral";
		if (v < 75) return "Greed";
		return "Extreme Greed";
	}
</script>

{#if loading}
	<div class="flex flex-col gap-3">{#each Array(2) as _}<div class="editorial-skeleton h-28"></div>{/each}</div>
{:else if !payload}
	<div class="ed-card" style="border-style: dashed;"><div class="ed-eyebrow">No data</div></div>
{:else}
	<div class="flex flex-col gap-3">
		<div class="ed-card">
			<div class="flex items-baseline justify-between mb-3">
				<div class="ed-eyebrow">Sentiment Gauge · {market}</div>
			</div>
			<div class="flex items-baseline gap-10 flex-wrap">
				<div>
					<div class="text-[10px] uppercase tracking-wide" style="color: var(--ed-text-3);">Fear & Greed</div>
					{#if fg && isFiniteNum(fg.value ?? fg)}
						{@const v = fg.value ?? fg}
						<div class="ed-num text-[40px] leading-none mt-1" style="color: {fgColor(v)}; font-family: var(--font-display);">{Math.round(v)}</div>
						<div class="text-[12px] mt-1" style="color: {fgColor(v)};">{fgLabel(v)}</div>
					{:else}
						<div class="text-[20px] mt-1" style="color: var(--ed-text-3);">데이터 없음</div>
					{/if}
				</div>
				<div>
					<div class="text-[10px] uppercase tracking-wide" style="color: var(--ed-text-3);">VIX Regime</div>
					{#if vix && typeof vix === "object"}
						<div class="text-[20px] font-medium mt-1" style="color: var(--ed-text); font-family: var(--font-display);">{vix.regime || vix.label || "—"}</div>
						{#if isFiniteNum(vix.value)}
							<div class="ed-num text-[14px] mt-1" style="color: var(--ed-text-2);">VIX {vix.value.toFixed(1)}</div>
						{/if}
					{:else}
						<div class="text-[20px] mt-1" style="color: var(--ed-text-3);">데이터 없음</div>
					{/if}
				</div>
			</div>
		</div>

		{#if ts && typeof ts === "object" && Object.keys(ts).length > 0}
			<div class="ed-card">
				<div class="ed-eyebrow mb-3">시계열 컴포넌트 ({Object.keys(ts).length})</div>
				<div class="grid grid-cols-1 md:grid-cols-3 gap-2">
					{#each Object.entries(ts) as [k, v]}
						<div class="rounded border p-2.5" style="border-color: var(--ed-line); background: var(--ed-surface-2);">
							<div class="text-[10px] uppercase tracking-wide" style="color: var(--ed-text-3);">{k}</div>
							<div class="text-[12px] mt-1" style="color: var(--ed-text);">
								{Array.isArray(v) ? v.length + " pts" : (v == null ? "데이터 없음" : (typeof v === "object" ? Object.keys(v).length + " keys" : String(v)))}
							</div>
						</div>
					{/each}
				</div>
			</div>
		{/if}
	</div>
{/if}
