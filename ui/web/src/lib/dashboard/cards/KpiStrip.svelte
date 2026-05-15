<!--
	KpiStrip — 4 KPI 타일 가로 strip. 모든 section 의 상단 공통.
	Props:
	  items: Array<{ label, value, sub?, delta?, deltaPositive? }>
	  loading: boolean
-->
<script>
	import { ArrowUp, ArrowDown } from "lucide-svelte";
	import * as Card from "$lib/ui/card";
	import { Skeleton } from "$lib/ui/skeleton";
	import { cn } from "$lib/utils.js";

	let { items = [], loading = false } = $props();
</script>

<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
	{#each items as item, i}
		<Card.Root class="p-4">
			<div class="text-[10px] text-muted-foreground uppercase tracking-wider font-medium mb-1.5">
				{item.label || "—"}
			</div>
			{#if loading}
				<Skeleton class="h-7 w-24" />
			{:else}
				<div class="text-[22px] font-semibold text-foreground font-mono tabular-nums leading-tight">
					{item.value ?? "—"}
				</div>
			{/if}
			<div class="mt-2 flex items-center justify-between gap-2 text-[11px]">
				{#if item.sub}
					<span class="text-muted-foreground truncate">{item.sub}</span>
				{:else}
					<span></span>
				{/if}
				{#if item.delta != null}
					<span
						class={cn(
							"inline-flex items-center gap-0.5 font-mono tabular-nums",
							item.deltaPositive ? "text-primary" : "text-muted-foreground"
						)}
					>
						{#if item.deltaPositive}
							<ArrowUp size={11} />
						{:else}
							<ArrowDown size={11} />
						{/if}
						{item.delta}
					</span>
				{/if}
			</div>
		</Card.Root>
	{/each}
</div>
