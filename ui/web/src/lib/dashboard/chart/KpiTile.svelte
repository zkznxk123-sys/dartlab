<!--
	KpiTile — 단일 metric 큰 카드. label + value + delta (Δ vs prev period).
-->
<script>
	import { isFiniteNum, fmtKrw, fmtPct, fmtPp } from "./util.js";

	let {
		label = "",
		value = null,
		delta = null,
		unit = "",
		valueFormat = null,
		deltaFormat = null,
		deltaSuffix = null,
	} = $props();

	const valFmt = $derived(
		valueFormat || (unit === "%" ? fmtPct : unit === "KRW" ? fmtKrw : (v) => isFiniteNum(v) ? v.toLocaleString() : "—")
	);
	const dFmt = $derived(
		deltaFormat || (unit === "%" ? fmtPp : (v) => isFiniteNum(v) ? (v > 0 ? "+" : "") + v.toFixed(1) : "—")
	);

	const deltaSign = $derived(isFiniteNum(delta) ? (delta > 0 ? "up" : delta < 0 ? "down" : "flat") : "flat");
</script>

<div class="ed-card flex flex-col gap-1.5">
	<div class="ed-eyebrow truncate" title={label}>{label}</div>
	<div class="ed-num ed-num-lg" style="color: var(--ed-text);">
		{valFmt(value)}{#if unit && unit !== "KRW" && unit !== "%"}<span class="ed-num-sm ml-1" style="color: var(--ed-text-3);">{unit}</span>{/if}
	</div>
	{#if isFiniteNum(delta)}
		<div class="ed-num text-[11px]" class:up={deltaSign === "up"} class:down={deltaSign === "down"}
			style="color: {deltaSign === 'up' ? 'var(--ed-up)' : deltaSign === 'down' ? 'var(--ed-down)' : 'var(--ed-text-3)'};">
			{deltaSign === "up" ? "▲" : deltaSign === "down" ? "▼" : "—"} {dFmt(delta)}{deltaSuffix ? ` ${deltaSuffix}` : ""}
		</div>
	{/if}
</div>
