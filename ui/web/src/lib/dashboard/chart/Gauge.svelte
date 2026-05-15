<!--
	Gauge — 단일 metric (gauge 또는 bullet). Editorial 톤.
	props:
	  value: 0~max 또는 percent
	  max: 100 (default)
	  min: 0
	  thresholds?: Array<{ at: number, color }> — 색 segment
	  label / valueLabel / unit
-->
<script>
	import { isFiniteNum, fmtPct, clamp, linearScale } from "./util.js";

	let {
		value = 0,
		min = 0,
		max = 100,
		label = "",
		valueLabel = null,
		unit = "%",
		thresholds = null,
		height = 70,
	} = $props();

	const W = 280;
	const barH = 8;
	const barTop = 24;

	const valid = $derived(isFiniteNum(value));
	const clamped = $derived(valid ? clamp(value, min, max) : min);
	const scale = $derived(linearScale([min, max], [16, W - 16]));
	const xVal = $derived(scale(clamped));

	const displayValue = $derived(
		valueLabel != null ? valueLabel : valid ? value.toFixed(1) + unit : "—"
	);

	const segments = $derived.by(() => {
		if (thresholds && thresholds.length > 0) return thresholds;
		// default: green→amber→red gradient by value range
		return [
			{ at: min + (max - min) * 0.33, color: "var(--ed-up)" },
			{ at: min + (max - min) * 0.66, color: "var(--ed-warn)" },
			{ at: max, color: "var(--ed-down)" },
		];
	});
</script>

<div class="w-full">
	<div class="flex items-baseline justify-between gap-2 mb-1">
		<div class="ed-eyebrow truncate" title={label}>{label}</div>
		<div class="ed-num text-[14px]" style="color: var(--ed-text);">{displayValue}</div>
	</div>
	<svg viewBox="0 0 {W} {height}" preserveAspectRatio="xMidYMid meet" class="w-full block">
		<!-- segments background -->
		{#each segments as seg, i}
			{@const x0 = i === 0 ? 16 : scale(segments[i - 1].at)}
			{@const x1 = scale(seg.at)}
			<rect x={x0} y={barTop} width={Math.max(0.5, x1 - x0)} height={barH} fill={seg.color} opacity="0.18" />
		{/each}
		<!-- main bar (filled portion) -->
		<rect x={16} y={barTop} width={Math.max(0, xVal - 16)} height={barH} fill="var(--ed-text)" opacity="0.86" rx="1" />
		<!-- tick marks -->
		{#each segments as seg}
			<line x1={scale(seg.at)} y1={barTop - 3} x2={scale(seg.at)} y2={barTop + barH + 3} stroke="var(--ed-line)" stroke-width="0.6" />
		{/each}
		<!-- pointer triangle -->
		{#if valid}
			<polygon points="{xVal - 3},{barTop - 4} {xVal + 3},{barTop - 4} {xVal},{barTop + 1}" fill="var(--ed-brand)" />
		{/if}
		<!-- min/max labels -->
		<text x={16} y={barTop + barH + 14} font-size="9.5" fill="var(--ed-text-3)" font-family="var(--font-num)">{min}</text>
		<text x={W - 16} y={barTop + barH + 14} text-anchor="end" font-size="9.5" fill="var(--ed-text-3)" font-family="var(--font-num)">{max}</text>
	</svg>
</div>
