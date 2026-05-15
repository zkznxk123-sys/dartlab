<!--
	Analysis Hub — Company.analysis 22 axes 의 hub.
	상단: financial 14 axis tabs (필터)
	하단: 선택된 axis 의 AnalysisAxisCard
	catalogue (axis 없이 호출) 로 axis 메타 (label/description) 동적 채움.
-->
<script>
	import { onMount } from "svelte";
	import { BarChart3, Info } from "lucide-svelte";
	import { getDashboardStore } from "$lib/stores/dashboardStore.svelte.js";
	import { loadAnalysis } from "$lib/dashboard/data/loaders.js";
	import AnalysisAxisCard from "$lib/dashboard/cards/AnalysisAxisCard.svelte";
	import * as Card from "$lib/ui/card";
	import { Skeleton } from "$lib/ui/skeleton";
	import { cn } from "$lib/utils.js";

	const dash = getDashboardStore();

	// Phase 2a — core financial axes 14 (Company.analysis 의 financial 그룹)
	// catalogue 가 더 풍부하면 동적 채움.
	const CORE_AXES = [
		"수익구조",
		"비용구조",
		"수익성",
		"성장성",
		"이익품질",
		"자산구조",
		"자금조달",
		"안정성",
		"효율성",
		"현금흐름",
		"자본배분",
		"투자효율",
		"종합평가",
		"재무정합성",
	];

	let catalogue = $state([]); // [{ axis, label, description, group, ... }]
	let catalogueLoading = $state(true);

	let axisPayload = $state(null);
	let axisLoading = $state(true);
	let axisError = $state(null);

	async function fetchCatalogue() {
		catalogueLoading = true;
		const r = await loadAnalysis(dash.stockCode);
		catalogue = r.ok ? r.data.axes : [];
		catalogueLoading = false;
	}

	async function fetchAxis(axis) {
		axisLoading = true;
		axisError = null;
		axisPayload = null;
		const r = await loadAnalysis(dash.stockCode, axis);
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
		// stockCode change → refresh both
		dash.stockCode;
		fetchCatalogue();
		const currentAxis = dash.axis || CORE_AXES[0];
		fetchAxis(currentAxis);
	});

	onMount(() => {
		if (!dash.axis) dash.setAxis(CORE_AXES[0]);
	});

	// Catalogue 에서 axis 메타 찾기
	function axisMeta(axis) {
		return catalogue.find((c) => c.axis === axis) || null;
	}

	const currentAxis = $derived(dash.axis || CORE_AXES[0]);
	const currentMeta = $derived(axisMeta(currentAxis));
</script>

<div class="flex flex-col gap-4">
	<!-- Axis Tabs -->
	<Card.Root>
		<Card.Header>
			<Card.Title class="flex items-center gap-2 text-[14px]">
				<BarChart3 size={15} />
				분석 축 (Company.analysis 14 financial axes)
			</Card.Title>
			{#if currentMeta?.description}
				<Card.Description class="text-[11px] flex items-start gap-1.5 mt-1">
					<Info size={11} class="shrink-0 mt-0.5" />
					<span>{currentMeta.description}</span>
				</Card.Description>
			{/if}
		</Card.Header>
		<Card.Content>
			<div class="flex flex-wrap gap-1">
				{#each CORE_AXES as axis}
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

	<!-- Axis Payload -->
	{#if axisError}
		<Card.Root class="border-destructive/30">
			<Card.Header>
				<Card.Title class="text-[14px] text-destructive">분석 로드 실패</Card.Title>
				<Card.Description class="text-[11px]">{axisError.message}</Card.Description>
			</Card.Header>
		</Card.Root>
	{:else}
		<AnalysisAxisCard payload={axisPayload} loading={axisLoading} />
	{/if}
</div>
