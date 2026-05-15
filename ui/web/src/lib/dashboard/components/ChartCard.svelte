<script>
	import ChartDispatch from "./ChartDispatch.svelte";

	let { title = "", subtitle = "", payload = null, loading = false, error = null, height = 280 } = $props();
</script>

<div class="rounded-lg border border-border bg-card text-card-foreground overflow-hidden">
	<div class="px-4 pt-3 pb-1">
		<div class="text-sm font-semibold tracking-tight">{title || payload?.chartSpec?.title || ""}</div>
		{#if subtitle}
			<div class="text-[11px] text-muted-foreground">{subtitle}</div>
		{/if}
	</div>
	<div class="px-4 pb-3 pt-1">
		{#if loading}
			<div class="w-full animate-pulse rounded-md bg-muted" style="height: {height}px"></div>
		{:else if error}
			<div class="flex items-center justify-center text-xs text-destructive" style="height: {height}px">
				{error}
			</div>
		{:else if !payload?.chartSpec}
			<div class="flex items-center justify-center text-xs text-muted-foreground" style="height: {height}px">데이터 없음</div>
		{:else}
			<div style="height: {height}px">
				<ChartDispatch spec={payload.chartSpec} />
			</div>
		{/if}
	</div>
</div>
