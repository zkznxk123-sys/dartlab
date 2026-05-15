<!--
	Analysis Hub — Editorial 톤. 자체 axis tabs + specialized dispatcher.
	Phase D: 수익성·수익구조만 specialized. 나머지 axis 는 AnalysisAxisCard generic fallback.
	Phase 추후: 나머지 12 axis 도 specialized 로 점진.
-->
<script>
	import { onMount, untrack } from "svelte";
	import { getDashboardStore } from "$lib/stores/dashboardStore.svelte.js";
	import { loadEngineAxis } from "$lib/dashboard/data/loaders.js";
	import AnalysisAxisCard from "$lib/dashboard/cards/AnalysisAxisCard.svelte";
	import Profitability from "$lib/dashboard/sections/analysis/Profitability.svelte";
	import RevenueStructure from "$lib/dashboard/sections/analysis/RevenueStructure.svelte";
	import CashFlow from "$lib/dashboard/sections/analysis/CashFlow.svelte";
	import Stability from "$lib/dashboard/sections/analysis/Stability.svelte";
	import Growth from "$lib/dashboard/sections/analysis/Growth.svelte";
	import Efficiency from "$lib/dashboard/sections/analysis/Efficiency.svelte";
	import EarningsQuality from "$lib/dashboard/sections/analysis/EarningsQuality.svelte";
	import AssetStructure from "$lib/dashboard/sections/analysis/AssetStructure.svelte";
	import Funding from "$lib/dashboard/sections/analysis/Funding.svelte";
	import CostStructure from "$lib/dashboard/sections/analysis/CostStructure.svelte";
	import CapitalAllocation from "$lib/dashboard/sections/analysis/CapitalAllocation.svelte";
	import InvestmentEfficiency from "$lib/dashboard/sections/analysis/InvestmentEfficiency.svelte";
	import Summary from "$lib/dashboard/sections/analysis/Summary.svelte";
	import Integrity from "$lib/dashboard/sections/analysis/Integrity.svelte";

	const dash = getDashboardStore();

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

	// axis → specialized component map (없으면 fallback AnalysisAxisCard)
	const SPECIALIZED = {
		수익성: Profitability,
		수익구조: RevenueStructure,
		현금흐름: CashFlow,
		안정성: Stability,
		성장성: Growth,
		효율성: Efficiency,
		이익품질: EarningsQuality,
		자산구조: AssetStructure,
		자금조달: Funding,
		비용구조: CostStructure,
		자본배분: CapitalAllocation,
		투자효율: InvestmentEfficiency,
		종합평가: Summary,
		재무정합성: Integrity,
	};

	let catalogue = $state([]);
	let axisPayload = $state(null);
	let axisLoading = $state(true);
	let axisError = $state(null);
	let abortCtrl = null;

	async function fetchCatalogue() {
		const r = await loadEngineAxis("Company.analysis", dash.stockCode);
		catalogue = r.ok ? r.data.axes : [];
	}

	async function fetchAxis(axis) {
		// abort 이전 fetch
		if (abortCtrl) abortCtrl.abort();
		abortCtrl = new AbortController();
		axisLoading = true;
		axisError = null;
		axisPayload = null;
		try {
			const r = await loadEngineAxis("Company.analysis", dash.stockCode, axis, { signal: abortCtrl.signal });
			if (r.ok) {
				axisPayload = r.data.payload;
			} else {
				axisError = r.error;
			}
		} catch (e) {
			if (e?.name !== "AbortError") axisError = { message: e?.message || String(e) };
		} finally {
			axisLoading = false;
		}
	}

	function selectAxis(axis) {
		dash.setAxis(axis);
		fetchAxis(axis);
	}

	$effect(() => {
		// stockCode 만 트래킹 — axis 는 selectAxis 단일 경로로 fetch (race 차단).
		dash.stockCode;
		untrack(() => {
			fetchCatalogue();
			const a = dash.axis && CORE_AXES.includes(dash.axis) ? dash.axis : CORE_AXES[0];
			if (a) fetchAxis(a);
		});
	});

	onMount(() => {
		if (!dash.axis || !CORE_AXES.includes(dash.axis)) {
			dash.setAxis(CORE_AXES[0]);
		}
	});

	function axisMeta(axis) {
		return catalogue.find((c) => c.axis === axis) || null;
	}

	const currentAxis = $derived(
		dash.axis && CORE_AXES.includes(dash.axis) ? dash.axis : CORE_AXES[0]
	);
	const currentMeta = $derived(axisMeta(currentAxis));
	const SpecializedComp = $derived(SPECIALIZED[currentAxis] || null);
</script>

<div class="flex flex-col gap-4 relative">
	<!-- Axis tabs + description -->
	<div class="ed-card">
		<div class="flex items-baseline justify-between mb-2">
			<div class="flex items-baseline gap-2 min-w-0">
				<div class="ed-eyebrow whitespace-nowrap">Axis</div>
				<h2 class="text-[15px] font-semibold truncate" style="color: var(--ed-text); font-family: var(--font-display);">
					{currentMeta?.label || currentAxis}
				</h2>
			</div>
			{#if currentMeta?.items}
				<div class="text-[10.5px] ed-num" style="color: var(--ed-text-3);">
					{currentMeta.items} items
				</div>
			{/if}
		</div>
		{#if currentMeta?.description}
			<div class="text-[12px] mb-3" style="color: var(--ed-text-2);">
				{currentMeta.description}
			</div>
		{/if}
		<div class="flex flex-wrap gap-1">
			{#each CORE_AXES as axis}
				{@const meta = axisMeta(axis)}
				{@const isSpecial = SPECIALIZED[axis]}
				<button
					type="button"
					class="px-2.5 py-1 rounded-md border text-[11.5px] font-medium transition-colors"
					class:active={currentAxis === axis}
					style="
						background: {currentAxis === axis ? 'color-mix(in srgb, var(--ed-brand) 12%, transparent)' : 'transparent'};
						border-color: {currentAxis === axis ? 'var(--ed-brand)' : 'var(--ed-line)'};
						color: {currentAxis === axis ? 'var(--ed-text)' : 'var(--ed-text-2)'};
					"
					onclick={() => selectAxis(axis)}
					title={meta?.description || axis}
				>
					{meta?.label || axis}
					{#if isSpecial}<span class="ed-num text-[8.5px] ml-1" style="color: var(--ed-brand); opacity: 0.7;">●</span>{/if}
				</button>
			{/each}
		</div>
	</div>

	<!-- Body: specialized 또는 fallback generic -->
	{#if axisError}
		<div class="ed-card" style="border-color: var(--ed-down);">
			<div class="ed-eyebrow mb-1" style="color: var(--ed-down);">로드 실패</div>
			<div class="text-[12px]" style="color: var(--ed-text-2);">{axisError.message}</div>
			<button class="mt-2 px-3 py-1 rounded border text-[11px]" style="border-color: var(--ed-line); color: var(--ed-text);"
				onclick={() => fetchAxis(currentAxis)}>retry</button>
		</div>
	{:else if SpecializedComp}
		<SpecializedComp payload={axisPayload} loading={axisLoading} />
	{:else}
		<AnalysisAxisCard payload={axisPayload} loading={axisLoading} />
	{/if}
</div>
