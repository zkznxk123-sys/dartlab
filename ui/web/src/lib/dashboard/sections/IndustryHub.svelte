<!--
	Industry Hub — Editorial 톤. Company.industry / Company.rank / Company.network 통합.
-->
<script>
	import { onMount } from "svelte";
	import { dlCall } from "$lib/api/dlCall.js";
	import { getDashboardStore } from "$lib/stores/dashboardStore.svelte.js";
	import AnalysisAxisCard from "$lib/dashboard/cards/AnalysisAxisCard.svelte";
	import IndustryPeers from "$lib/dashboard/sections/industry/IndustryPeers.svelte";

	const dash = getDashboardStore();

	const VIEWS = [
		{ apiRef: "Company.industry", label: "산업/Peers", desc: "산업 분류 · 가치사슬 위치 · 동종업계 peer list" },
		{ apiRef: "Company.rank", label: "Peer Ranking", desc: "주요 지표 동종업계 순위" },
		{ apiRef: "Company.network", label: "Network", desc: "공급망 · 고객 · 경쟁자 네트워크" },
	];

	const SPECIALIZED = {
		"Company.industry": IndustryPeers,
	};

	let selected = $state("Company.industry");
	let payload = $state(null);
	let loading = $state(true);
	let error = $state(null);
	let abortCtrl = null;

	async function fetchView(apiRef) {
		if (abortCtrl) abortCtrl.abort();
		abortCtrl = new AbortController();
		loading = true;
		error = null;
		payload = null;
		try {
			const r = await dlCall(apiRef, { target: dash.stockCode, signal: abortCtrl.signal });
			payload = r?.data ?? null;
		} catch (e) {
			if (e?.name !== "AbortError") error = { message: e?.message || String(e) };
		} finally {
			loading = false;
		}
	}

	function select(apiRef) {
		selected = apiRef;
		fetchView(apiRef);
	}

	$effect(() => {
		dash.stockCode;
		fetchView(selected);
	});

	onMount(() => fetchView(selected));

	const currentMeta = $derived(VIEWS.find((v) => v.apiRef === selected) || VIEWS[0]);
	const SpecializedComp = $derived(SPECIALIZED[selected] || null);
</script>

<div class="flex flex-col gap-4">
	<div class="ed-card">
		<div class="flex items-baseline justify-between mb-2">
			<div class="flex items-baseline gap-2 min-w-0">
				<div class="ed-eyebrow whitespace-nowrap">View</div>
				<h2 class="text-[15px] font-semibold truncate" style="color: var(--ed-text); font-family: var(--font-display);">{currentMeta.label}</h2>
			</div>
		</div>
		<div class="text-[12px] mb-3" style="color: var(--ed-text-2);">{currentMeta.desc}</div>
		<div class="flex flex-wrap gap-1">
			{#each VIEWS as v}
				{@const isSpecial = SPECIALIZED[v.apiRef]}
				<button type="button"
					class="px-2.5 py-1 rounded-md border text-[11.5px] font-medium transition-colors"
					style="background: {selected === v.apiRef ? 'color-mix(in srgb, var(--ed-brand) 12%, transparent)' : 'transparent'}; border-color: {selected === v.apiRef ? 'var(--ed-brand)' : 'var(--ed-line)'}; color: {selected === v.apiRef ? 'var(--ed-text)' : 'var(--ed-text-2)'};"
					onclick={() => select(v.apiRef)}>
					{v.label}
					{#if isSpecial}<span class="ed-num text-[8.5px] ml-1" style="color: var(--ed-brand); opacity: 0.7;">●</span>{/if}
				</button>
			{/each}
		</div>
	</div>

	{#if error}
		<div class="ed-card" style="border-color: var(--ed-down);">
			<div class="ed-eyebrow mb-1" style="color: var(--ed-down);">{currentMeta.label} 로드 실패</div>
			<div class="text-[12px]" style="color: var(--ed-text-2);">{error.message}</div>
			<button class="mt-2 px-3 py-1 rounded border text-[11px]" style="border-color: var(--ed-line); color: var(--ed-text);" onclick={() => fetchView(selected)}>retry</button>
		</div>
	{:else if SpecializedComp}
		<SpecializedComp {payload} {loading} />
	{:else}
		<AnalysisAxisCard {payload} {loading} />
	{/if}
</div>
