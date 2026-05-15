<script>
	let { title = "", subtitle = "", payload = null, loading = false, error = null } = $props();

	function fmt(v, unit) {
		if (v == null || Number.isNaN(v)) return "—";
		const abs = Math.abs(v);
		if (unit === "%") return v.toFixed(2) + "%";
		if (abs >= 1e12) return (v / 1e12).toFixed(2) + "조";
		if (abs >= 1e8) return (v / 1e8).toFixed(0) + "억";
		if (abs >= 1e4) return (v / 1e4).toFixed(0) + "만";
		return Math.round(v).toLocaleString();
	}
</script>

<div class="rounded-lg border border-border bg-card text-card-foreground overflow-hidden">
	<div class="px-4 pt-3 pb-1">
		<div class="text-sm font-semibold tracking-tight">{title || payload?.chartSpec?.title || ""}</div>
		{#if subtitle}
			<div class="text-[11px] text-muted-foreground">{subtitle}</div>
		{/if}
	</div>
	<div class="px-4 pb-3 pt-1 overflow-x-auto">
		{#if loading}
			<div class="w-full h-40 animate-pulse rounded-md bg-muted"></div>
		{:else if error}
			<div class="text-xs text-destructive p-4">{error}</div>
		{:else if !payload?.data?.rows?.length}
			<div class="text-xs text-muted-foreground p-4">데이터 없음</div>
		{:else}
			{@const periods = payload.data.periods || []}
			{@const rows = payload.data.rows || []}
			<table class="w-full text-xs tabular-nums">
				<thead>
					<tr class="border-b border-border">
						<th class="text-left py-1.5 px-2 font-medium text-muted-foreground">항목</th>
						{#each periods as p}
							<th class="text-right py-1.5 px-2 font-medium text-muted-foreground">{p}</th>
						{/each}
					</tr>
				</thead>
				<tbody>
					{#each rows as r}
						<tr class="border-b border-border/40 hover:bg-accent/40">
							<td class="py-1.5 px-2">{r.label}</td>
							{#each r.values as v}
								<td class="py-1.5 px-2 text-right" class:text-destructive={typeof v === "number" && v < 0}>
									{fmt(v, r.unit)}
								</td>
							{/each}
						</tr>
					{/each}
				</tbody>
			</table>
		{/if}
	</div>
</div>
