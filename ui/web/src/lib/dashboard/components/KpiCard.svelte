<script>
	let { label = "", value = null, unit = "", delta = null, deltaLabel = "" } = $props();

	function fmt(v, unit) {
		if (v == null || Number.isNaN(v)) return "—";
		const abs = Math.abs(v);
		if (unit === "%") return v.toFixed(2) + "%";
		if (abs >= 1e12) return (v / 1e12).toFixed(2) + "조";
		if (abs >= 1e8) return (v / 1e8).toFixed(0) + "억";
		return Math.round(v).toLocaleString();
	}
</script>

<div class="rounded-lg border border-border bg-card text-card-foreground py-3 px-4">
	<div class="text-[11px] text-muted-foreground font-medium">{label}</div>
	<div class="text-xl font-semibold tabular-nums mt-0.5" class:text-destructive={typeof value === "number" && value < 0}>
		{fmt(value, unit)}
	</div>
	{#if delta != null}
		<div class="text-[10px] mt-0.5 tabular-nums" class:text-destructive={delta < 0}>
			{delta > 0 ? "+" : ""}{fmt(delta, "%")} {deltaLabel}
		</div>
	{/if}
</div>
