<!--
	QuantScores — Z·F·M 단일 score 응답 통합 시각화.
	response: { stockCode, market, year, prevYear?, variant?, score, zone?, grade?, flag?, percentile?, universe?, components?, interpretation? }
-->
<script>
	import { isFiniteNum } from "$lib/dashboard/chart/util.js";

	let { payload = null, loading = false } = $props();

	const score = $derived(payload?.score);
	const zone = $derived(payload?.zone || payload?.grade || payload?.flag || "—");
	const interp = $derived(payload?.interpretation || payload?._meaning || "");
	const year = $derived(payload?.year || "—");
	const prevYear = $derived(payload?.prevYear || null);
	const variant = $derived(payload?.variant || null);
	const percentile = $derived(payload?.percentile);
	const universe = $derived(payload?.universe || null);
	const components = $derived(payload?.components || null);

	const tier = $derived(
		typeof zone === "string" && /safe|strong|high|conservative/i.test(zone) ? "up"
		: typeof zone === "string" && /distress|low|aggressive|manipulator|warn/i.test(zone) ? "down"
		: "neutral"
	);

	function fmtComp(v) {
		if (v == null) return "—";
		if (typeof v === "number") {
			if (!Number.isFinite(v)) return "—";
			if (Math.abs(v) >= 1e4) return v.toExponential(2);
			return v.toFixed(3);
		}
		return String(v);
	}
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
		<!-- Hero -->
		<div class="ed-card">
			<div class="flex items-baseline justify-between mb-3">
				<div class="ed-eyebrow">Score · {year}{prevYear ? ` (vs ${prevYear})` : ""}</div>
				<div class="text-[10px]" style="color: var(--ed-text-3);">
					{universe || ""}{variant ? ` · variant ${variant}` : ""}
				</div>
			</div>
			<div class="flex items-baseline gap-8 flex-wrap">
				<div>
					<div class="text-[10px] uppercase tracking-wide" style="color: var(--ed-text-3);">Score</div>
					<div class="text-[48px] ed-num leading-none mt-1" style="color: var(--ed-text); font-family: var(--font-display);">
						{isFiniteNum(score) ? score.toFixed(2) : "—"}
					</div>
				</div>
				<div>
					<div class="text-[10px] uppercase tracking-wide" style="color: var(--ed-text-3);">Zone / Grade</div>
					<div class="text-[24px] font-bold ed-num leading-none mt-1"
						style="color: {tier === 'up' ? 'var(--ed-up)' : tier === 'down' ? 'var(--ed-down)' : 'var(--ed-text)'}; font-family: var(--font-display);">
						{zone}
					</div>
				</div>
				{#if isFiniteNum(percentile)}
					<div>
						<div class="text-[10px] uppercase tracking-wide" style="color: var(--ed-text-3);">Percentile</div>
						<div class="ed-num text-[24px] leading-none mt-1" style="color: var(--ed-text);">{(percentile * 100).toFixed(1)}%</div>
					</div>
				{/if}
			</div>
			{#if interp}
				<div class="text-[12px] mt-3" style="color: var(--ed-text-2);">{interp}</div>
			{/if}
		</div>

		<!-- Components -->
		{#if components && typeof components === "object"}
			<div class="ed-card">
				<div class="ed-eyebrow mb-3">구성 변수 · contribution</div>
				{#if Array.isArray(components)}
					<div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-2">
						{#each components as c}
							<div class="rounded border p-2.5" style="border-color: var(--ed-line); background: var(--ed-surface-2);">
								<div class="text-[10px] uppercase tracking-wide truncate" style="color: var(--ed-text-3);" title={c.signal || c.name}>
									{c.signal || c.name || "—"}
								</div>
								<div class="ed-num text-[13px] mt-1" style="color: {c.pass ? 'var(--ed-up)' : c.pass === false ? 'var(--ed-down)' : 'var(--ed-text)'};">
									{c.pass !== undefined ? (c.pass ? "✓ pass" : "✗ fail") : fmtComp(c.value ?? c.score)}
								</div>
							</div>
						{/each}
					</div>
				{:else}
					<div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-2">
						{#each Object.entries(components) as [k, v]}
							<div class="rounded border p-2.5" style="border-color: var(--ed-line); background: var(--ed-surface-2);">
								<div class="text-[10px] uppercase tracking-wide truncate" style="color: var(--ed-text-3);" title={k}>{k}</div>
								<div class="ed-num text-[13px] mt-1" style="color: var(--ed-text);">{fmtComp(v)}</div>
							</div>
						{/each}
					</div>
				{/if}
			</div>
		{/if}
	</div>
{/if}
