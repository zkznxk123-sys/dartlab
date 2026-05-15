<script>
	import { getDashboardStore } from "$lib/stores/dashboardStore.svelte.js";

	const dash = getDashboardStore();

	const items = [
		{ key: "annual", label: "연간" },
		{ key: "quarterly", label: "분기" },
	];
</script>

<div class="inline-flex items-center rounded-md border border-border bg-card p-0.5">
	{#each items as it}
		<button
			class="px-2.5 py-1 text-[11px] rounded-sm transition-colors {dash.mode === it.key ? 'bg-foreground text-background' : 'text-muted-foreground hover:text-foreground'}"
			onclick={() => dash.setMode(it.key)}
		>{it.label}</button>
	{/each}
</div>
