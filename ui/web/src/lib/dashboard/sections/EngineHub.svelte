<!--
	EngineHub — 일반화된 axis hub.
	Analysis / Quant / Credit / Industry / Macro 모두 같은 패턴:
	  catalogue (no-args) 로 axis 메타 + core axes tabs + AnalysisAxisCard render.
	props:
	  apiRef: "Company.analysis" | "Company.quant" | ...
	  title: 헤더 라벨
	  icon: lucide component
	  coreAxes: 표시할 axis 의 priority list
	  axisKey: dashboardStore 의 axis 필드 사용 (단일)
-->
<script>
	import { onMount } from "svelte";
	import { Info } from "lucide-svelte";
	import { getDashboardStore } from "$lib/stores/dashboardStore.svelte.js";
	import { loadEngineAxis } from "$lib/dashboard/data/loaders.js";
	import AnalysisAxisCard from "$lib/dashboard/cards/AnalysisAxisCard.svelte";
	import * as Card from "$lib/ui/card";
	import { cn } from "$lib/utils.js";

	let {
		apiRef,
		title,
		icon: IconComp = null,
		coreAxes = [],
		descLabel = "",
	} = $props();

	const dash = getDashboardStore();

	let catalogue = $state([]);
	let axisPayload = $state(null);
	let axisLoading = $state(true);
	let axisError = $state(null);

	async function fetchCatalogue() {
		const r = await loadEngineAxis(apiRef, dash.stockCode);
		catalogue = r.ok ? r.data.axes : [];
	}

	async function fetchAxis(axis) {
		axisLoading = true;
		axisError = null;
		axisPayload = null;
		const r = await loadEngineAxis(apiRef, dash.stockCode, axis);
		if (r.ok) {
			axisPayload = r.data.payload;
		} else {
			axisError = r.error;
		}
		axisLoading = false;
	}

	function selectAxis(axis) {
		dash.setAxis(axis);
		fetchAxis(axis);
	}

	$effect(() => {
		dash.stockCode;
		fetchCatalogue();
		const currentAxis = dash.axis && coreAxes.includes(dash.axis) ? dash.axis : coreAxes[0];
		if (currentAxis) fetchAxis(currentAxis);
	});

	onMount(() => {
		if (!dash.axis || !coreAxes.includes(dash.axis)) {
			if (coreAxes[0]) dash.setAxis(coreAxes[0]);
		}
	});

	function axisMeta(axis) {
		return catalogue.find((c) => c.axis === axis) || null;
	}

	const currentAxis = $derived(
		dash.axis && coreAxes.includes(dash.axis) ? dash.axis : coreAxes[0]
	);
	const currentMeta = $derived(axisMeta(currentAxis));
</script>

<div class="flex flex-col gap-4">
	<Card.Root>
		<Card.Header>
			<Card.Title class="flex items-center gap-2 text-[14px]">
				{#if IconComp}<IconComp size={15} />{/if}
				{title}
			</Card.Title>
			{#if currentMeta?.description || descLabel}
				<Card.Description class="text-[11px] flex items-start gap-1.5 mt-1">
					<Info size={11} class="shrink-0 mt-0.5" />
					<span>{currentMeta?.description || descLabel}</span>
				</Card.Description>
			{/if}
		</Card.Header>
		<Card.Content>
			<div class="flex flex-wrap gap-1">
				{#each coreAxes as axis}
					{@const meta = axisMeta(axis)}
					<button
						type="button"
						class={cn(
							"px-2.5 py-1 rounded-md border text-[12px] font-medium transition-colors",
							currentAxis === axis
								? "border-primary bg-primary/10 text-foreground"
								: "border-border text-muted-foreground hover:border-foreground/30 hover:text-foreground"
						)}
						onclick={() => selectAxis(axis)}
						title={meta?.description || axis}
					>
						{meta?.label || axis}
					</button>
				{/each}
			</div>
		</Card.Content>
	</Card.Root>

	{#if axisError}
		<Card.Root class="border-destructive/30">
			<Card.Header>
				<Card.Title class="text-[14px] text-destructive">{title} 로드 실패</Card.Title>
				<Card.Description class="text-[11px]">{axisError.message}</Card.Description>
			</Card.Header>
		</Card.Root>
	{:else}
		<AnalysisAxisCard payload={axisPayload} loading={axisLoading} />
	{/if}
</div>
