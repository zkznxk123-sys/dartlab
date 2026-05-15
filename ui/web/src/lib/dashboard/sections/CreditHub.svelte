<!--
	Credit Hub — Editorial 톤. 자체 axis tabs + specialized dispatcher.
	Phase E: grade specialized. 나머지 7 (repayment/leverage/liquidity/cashflow/business/reliability/disclosure) generic fallback — metrics nested array 가 generic 으로 표 표시.
-->
<script>
	import { onMount, untrack } from "svelte";
	import { getDashboardStore } from "$lib/stores/dashboardStore.svelte.js";
	import { loadEngineAxis } from "$lib/dashboard/data/loaders.js";
	import AnalysisAxisCard from "$lib/dashboard/cards/AnalysisAxisCard.svelte";
	import Grade from "$lib/dashboard/sections/credit/Grade.svelte";

	const dash = getDashboardStore();

	const CORE_AXES = [
		"grade",
		"repayment",
		"leverage",
		"liquidity",
		"cashflow",
		"business",
		"reliability",
		"disclosure",
	];

	const SPECIALIZED = { grade: Grade };

	let catalogue = $state([]);
	let axisPayload = $state(null);
	let axisLoading = $state(true);
	let axisError = $state(null);
	let abortCtrl = null;

	async function fetchCatalogue() {
		const r = await loadEngineAxis("Company.credit", dash.stockCode);
		catalogue = r.ok ? r.data.axes : [];
	}

	async function fetchAxis(axis) {
		if (abortCtrl) abortCtrl.abort();
		abortCtrl = new AbortController();
		axisLoading = true;
		axisError = null;
		axisPayload = null;
		try {
			const r = await loadEngineAxis("Company.credit", dash.stockCode, axis, { signal: abortCtrl.signal });
			if (r.ok) axisPayload = r.data.payload;
			else axisError = r.error;
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
		dash.stockCode;
		dash.axis;
		untrack(() => {
			fetchCatalogue();
			const a = dash.axis && CORE_AXES.includes(dash.axis) ? dash.axis : "grade";
			if (a) fetchAxis(a);
		});
	});

	onMount(() => {
		if (!dash.axis || !CORE_AXES.includes(dash.axis)) {
			dash.setAxis("grade");
		}
	});

	function axisMeta(axis) {
		return catalogue.find((c) => c.axis === axis) || null;
	}

	const currentAxis = $derived(
		dash.axis && CORE_AXES.includes(dash.axis) ? dash.axis : "grade"
	);
	const currentMeta = $derived(axisMeta(currentAxis));
	const SpecializedComp = $derived(SPECIALIZED[currentAxis] || null);
</script>

<div class="flex flex-col gap-4 relative">
	<div class="ed-card">
		<div class="flex items-baseline justify-between mb-2">
			<div class="flex items-baseline gap-2 min-w-0">
				<div class="ed-eyebrow whitespace-nowrap">Axis</div>
				<h2 class="text-[15px] font-semibold truncate" style="color: var(--ed-text); font-family: var(--font-display);">
					{currentMeta?.label || currentAxis}
				</h2>
			</div>
			<div class="text-[10.5px] ed-num" style="color: var(--ed-text-3);">dCR</div>
		</div>
		{#if currentMeta?.description}
			<div class="text-[12px] mb-3" style="color: var(--ed-text-2);">{currentMeta.description}</div>
		{/if}
		<div class="flex flex-wrap gap-1">
			{#each CORE_AXES as axis}
				{@const meta = axisMeta(axis)}
				{@const isSpecial = SPECIALIZED[axis]}
				<button type="button"
					class="px-2.5 py-1 rounded-md border text-[11.5px] font-medium transition-colors"
					style="background: {currentAxis === axis ? 'color-mix(in srgb, var(--ed-brand) 12%, transparent)' : 'transparent'}; border-color: {currentAxis === axis ? 'var(--ed-brand)' : 'var(--ed-line)'}; color: {currentAxis === axis ? 'var(--ed-text)' : 'var(--ed-text-2)'};"
					onclick={() => selectAxis(axis)}
					title={meta?.description || axis}>
					{meta?.label || axis}
					{#if isSpecial}<span class="ed-num text-[8.5px] ml-1" style="color: var(--ed-brand); opacity: 0.7;">●</span>{/if}
				</button>
			{/each}
		</div>
	</div>

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
