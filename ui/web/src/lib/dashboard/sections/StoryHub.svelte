<!--
	Story Hub — Editorial 톤. 14 analysis axis 의 perspective 묶음 (UI layer).
	상단 perspective tabs · 좌측 axis list · 본문 선택 axis 의 specialized 또는 generic 렌더.
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

	const dash = getDashboardStore();

	const SPECIALIZED = {
		"수익성": Profitability,
		"수익구조": RevenueStructure,
		"현금흐름": CashFlow,
		"안정성": Stability,
		"성장성": Growth,
		"효율성": Efficiency,
	};

	const PERSPECTIVES = [
		{ key: "investor", label: "투자", desc: "수익 창출력 · 성장 동력 · 자본 효율", axes: ["수익성", "성장성", "효율성", "이익품질", "투자효율"] },
		{ key: "credit", label: "신용", desc: "지급능력 · 부채 부담 · 현금흐름 안정성", axes: ["안정성", "현금흐름", "자금조달", "자산구조"] },
		{ key: "ma", label: "M&A", desc: "수익원 다각화 · 자본배분 · 사업부 강점", axes: ["수익구조", "자본배분", "비용구조", "투자효율"] },
		{ key: "esg", label: "ESG", desc: "거버넌스 · 재무 신뢰성 · 공시 품질", axes: ["재무정합성", "종합평가"] },
		{ key: "shock", label: "거시충격", desc: "외부 충격 회복 탄력 · 유동성 buffer", axes: ["안정성", "현금흐름", "자금조달"] },
	];

	const ALL_AXES = [
		"수익구조", "비용구조", "수익성", "성장성", "이익품질",
		"자산구조", "자금조달", "안정성", "효율성", "현금흐름",
		"자본배분", "투자효율", "종합평가", "재무정합성",
	];

	let perspectiveKey = $state("investor");
	let selectedAxis = $state("수익성");
	let payload = $state(null);
	let loading = $state(true);
	let error = $state(null);
	let abortCtrl = null;

	async function fetchAxis(axis) {
		if (abortCtrl) abortCtrl.abort();
		abortCtrl = new AbortController();
		loading = true;
		error = null;
		payload = null;
		const r = await loadEngineAxis("Company.analysis", dash.stockCode, axis, { signal: abortCtrl.signal });
		if (r.ok) payload = r.data.payload;
		else if (r.error?.message !== "AbortError") error = r.error;
		loading = false;
	}

	function selectPerspective(key) {
		perspectiveKey = key;
		const persp = PERSPECTIVES.find((p) => p.key === key);
		if (persp && persp.axes.length) {
			selectedAxis = persp.axes[0];
			fetchAxis(selectedAxis);
		}
	}

	function selectAxis(axis) {
		selectedAxis = axis;
		fetchAxis(axis);
	}

	$effect(() => {
		dash.stockCode;
		untrack(() => fetchAxis(selectedAxis));
	});

	onMount(() => fetchAxis(selectedAxis));

	const currentPersp = $derived(PERSPECTIVES.find((p) => p.key === perspectiveKey) || PERSPECTIVES[0]);
	const SpecializedComp = $derived(SPECIALIZED[selectedAxis] || null);

	function isPersAxis(axis) {
		return currentPersp.axes.includes(axis);
	}
</script>

<div class="flex flex-col gap-4">
	<!-- Perspective tabs -->
	<div class="ed-card">
		<div class="flex items-baseline justify-between mb-2">
			<div class="flex items-baseline gap-2 min-w-0">
				<div class="ed-eyebrow whitespace-nowrap">Perspective</div>
				<h2 class="text-[15px] font-semibold truncate" style="color: var(--ed-text); font-family: var(--font-display);">{currentPersp.label}</h2>
			</div>
		</div>
		<div class="text-[12px] mb-3" style="color: var(--ed-text-2);">{currentPersp.desc}</div>
		<div class="flex flex-wrap gap-1">
			{#each PERSPECTIVES as p}
				<button type="button"
					class="px-2.5 py-1 rounded-md border text-[11.5px] font-medium transition-colors"
					style="background: {perspectiveKey === p.key ? 'color-mix(in srgb, var(--ed-brand) 12%, transparent)' : 'transparent'}; border-color: {perspectiveKey === p.key ? 'var(--ed-brand)' : 'var(--ed-line)'}; color: {perspectiveKey === p.key ? 'var(--ed-text)' : 'var(--ed-text-2)'};"
					onclick={() => selectPerspective(p.key)}
					title={p.desc}>{p.label}</button>
			{/each}
		</div>
	</div>

	<!-- Axis list (좌) + 본문 (우) -->
	<div class="grid grid-cols-1 md:grid-cols-[200px_1fr] gap-4">
		<div class="ed-card self-start">
			<div class="ed-eyebrow mb-2">14 분석 축</div>
			<div class="text-[10px] mb-2" style="color: var(--ed-text-3);">{currentPersp.label} 강조</div>
			<ul class="flex flex-col gap-0.5">
				{#each ALL_AXES as axis}
					{@const pers = isPersAxis(axis)}
					{@const isSpecial = SPECIALIZED[axis]}
					<li>
						<button
							type="button"
							class="w-full px-2 py-1.5 rounded text-left text-[12px] transition-colors flex items-center justify-between gap-2"
							style="background: {selectedAxis === axis ? 'color-mix(in srgb, var(--ed-brand) 10%, transparent)' : 'transparent'}; color: {selectedAxis === axis ? 'var(--ed-text)' : pers ? 'var(--ed-text-2)' : 'var(--ed-text-3)'}; font-weight: {selectedAxis === axis ? 600 : 400}; opacity: {pers || selectedAxis === axis ? 1 : 0.6};"
							onclick={() => selectAxis(axis)}>
							<span class="truncate">{axis}</span>
							<span class="flex items-center gap-1">
								{#if isSpecial}<span class="ed-num text-[8px]" style="color: var(--ed-brand);">●</span>{/if}
								{#if pers}<span class="text-[8px] uppercase tracking-wide" style="color: var(--ed-brand); opacity: 0.7;">▸</span>{/if}
							</span>
						</button>
					</li>
				{/each}
			</ul>
		</div>

		<div>
			{#if error}
				<div class="ed-card" style="border-color: var(--ed-down);">
					<div class="ed-eyebrow mb-1" style="color: var(--ed-down);">{selectedAxis} 로드 실패</div>
					<div class="text-[12px]" style="color: var(--ed-text-2);">{error.message}</div>
					<button class="mt-2 px-3 py-1 rounded border text-[11px]" style="border-color: var(--ed-line); color: var(--ed-text);" onclick={() => fetchAxis(selectedAxis)}>retry</button>
				</div>
			{:else if SpecializedComp}
				<SpecializedComp {payload} {loading} />
			{:else}
				<AnalysisAxisCard {payload} {loading} />
			{/if}
		</div>
	</div>
</div>
