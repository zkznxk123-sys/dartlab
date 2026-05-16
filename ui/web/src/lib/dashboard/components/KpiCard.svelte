<script>
	import * as Card from "$lib/ui/card";

	let { label = "", value = null, unit = "", delta = null, deltaLabel = "" } = $props();

	function fmt(v, u) {
		if (v == null || Number.isNaN(v)) return "—";
		const abs = Math.abs(v);
		if (u === "%") return v.toFixed(2) + "%";
		if (abs >= 1e12) return (v / 1e12).toFixed(2) + "조";
		if (abs >= 1e8) return (v / 1e8).toFixed(0) + "억";
		return Math.round(v).toLocaleString();
	}
</script>

<Card.Root>
	<Card.Content class="py-3 px-4">
		<div class="text-xs text-muted-foreground font-medium">{label}</div>
		<div class="text-xl font-semibold tabular-nums mt-0.5 {typeof value === 'number' && value < 0 ? 'text-destructive' : ''}">
			{fmt(value, unit)}
		</div>
		{#if delta != null}
			<div class="text-[10px] mt-0.5 tabular-nums {delta < 0 ? 'text-destructive' : 'text-muted-foreground'}">
				{delta > 0 ? "+" : ""}{fmt(delta, "%")} {deltaLabel}
			</div>
		{/if}
	</Card.Content>
</Card.Root>
