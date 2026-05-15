<!--
	Macro Hub — Editorial 톤. dartlab.macro.* 12 sub-engines (회사 무관).
	각 sub-engine 별 dlCall 직접. 응답은 generic AnalysisAxisCard 가 dispatch
	(history shape / DataFrame envelope / flat dict 자동 분기).
-->
<script>
	import { onMount } from "svelte";
	import { dlCall } from "$lib/api/dlCall.js";
	import AnalysisAxisCard from "$lib/dashboard/cards/AnalysisAxisCard.svelte";

	const SUB_ENGINES = [
		{ apiRef: "macro.rates", label: "금리", desc: "기준금리 · 국고채 · 수익률곡선" },
		{ apiRef: "macro.assets", label: "자산", desc: "자산군별 수익률 · 상관" },
		{ apiRef: "macro.cycle", label: "사이클", desc: "경기 사이클 phase" },
		{ apiRef: "macro.liquidity", label: "유동성", desc: "통화·신용 유동성" },
		{ apiRef: "macro.sentiment", label: "심리", desc: "투자 sentiment gauge" },
		{ apiRef: "macro.inventory", label: "재고", desc: "재고 사이클 추이" },
		{ apiRef: "macro.trade", label: "교역", desc: "수출입 · 무역 흐름" },
		{ apiRef: "macro.corporate", label: "기업", desc: "법인 활동 거시 지표" },
		{ apiRef: "macro.forecast", label: "전망", desc: "거시 변수 예측" },
		{ apiRef: "macro.scenario", label: "시나리오", desc: "시나리오 충격 분석" },
		{ apiRef: "macro.crisis", label: "위기", desc: "위기 시그널 모니터" },
		{ apiRef: "macro.summary", label: "요약", desc: "거시 종합 요약" },
	];

	let selected = $state("macro.rates");
	let payload = $state(null);
	let loading = $state(true);
	let error = $state(null);
	let abortCtrl = null;

	async function fetchSub(apiRef) {
		if (abortCtrl) abortCtrl.abort();
		abortCtrl = new AbortController();
		loading = true;
		error = null;
		payload = null;
		try {
			const r = await dlCall(apiRef, { signal: abortCtrl.signal });
			payload = r?.data ?? null;
		} catch (e) {
			if (e?.name !== "AbortError") error = { message: e?.message || String(e) };
		} finally {
			loading = false;
		}
	}

	function select(apiRef) {
		selected = apiRef;
		fetchSub(apiRef);
	}

	onMount(() => fetchSub(selected));

	const currentMeta = $derived(SUB_ENGINES.find((s) => s.apiRef === selected) || SUB_ENGINES[0]);
</script>

<div class="flex flex-col gap-4">
	<div class="ed-card">
		<div class="flex items-baseline justify-between mb-2">
			<div class="flex items-baseline gap-2 min-w-0">
				<div class="ed-eyebrow whitespace-nowrap">Macro Sub</div>
				<h2 class="text-[15px] font-semibold truncate" style="color: var(--ed-text); font-family: var(--font-display);">{currentMeta.label}</h2>
			</div>
			<div class="text-[10.5px] ed-num" style="color: var(--ed-text-3);">{currentMeta.apiRef}</div>
		</div>
		<div class="text-[12px] mb-3" style="color: var(--ed-text-2);">{currentMeta.desc}</div>
		<div class="flex flex-wrap gap-1">
			{#each SUB_ENGINES as eng}
				<button type="button"
					class="px-2.5 py-1 rounded-md border text-[11.5px] font-medium transition-colors"
					style="background: {selected === eng.apiRef ? 'color-mix(in srgb, var(--ed-brand) 12%, transparent)' : 'transparent'}; border-color: {selected === eng.apiRef ? 'var(--ed-brand)' : 'var(--ed-line)'}; color: {selected === eng.apiRef ? 'var(--ed-text)' : 'var(--ed-text-2)'};"
					onclick={() => select(eng.apiRef)}
					title={eng.desc}>{eng.label}</button>
			{/each}
		</div>
	</div>

	{#if error}
		<div class="ed-card" style="border-color: var(--ed-down);">
			<div class="ed-eyebrow mb-1" style="color: var(--ed-down);">{currentMeta.label} 로드 실패</div>
			<div class="text-[12px]" style="color: var(--ed-text-2);">{error.message}</div>
			<button class="mt-2 px-3 py-1 rounded border text-[11px]" style="border-color: var(--ed-line); color: var(--ed-text);" onclick={() => fetchSub(selected)}>retry</button>
		</div>
	{:else}
		<AnalysisAxisCard {payload} {loading} />
	{/if}
</div>
