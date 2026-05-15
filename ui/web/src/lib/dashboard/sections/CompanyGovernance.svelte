<!--
	Company > Governance — Editorial 톤. 등급/총점 hero + 16 지표 scorecard inline.
-->
<script>
	import { onMount, untrack } from "svelte";
	import { getDashboardStore } from "$lib/stores/dashboardStore.svelte.js";
	import { loadGovernance } from "$lib/dashboard/data/loaders.js";
	import { isFiniteNum } from "$lib/dashboard/chart/util.js";

	const dash = getDashboardStore();

	let loading = $state(true);
	let row = $state({});
	let columns = $state([]);
	let error = $state(null);

	async function fetchAll() {
		loading = true;
		error = null;
		const result = await loadGovernance(dash.stockCode);
		if (result.ok) {
			row = result.data.row;
			columns = result.data.columns;
		} else {
			error = result.error;
			row = {};
			columns = [];
		}
		loading = false;
	}

	$effect(() => {
		dash.stockCode;
		untrack(() => fetchAll());
	});

	onMount(() => fetchAll());

	const HIGHLIGHT_KEYS = ["등급", "총점", "지분율", "사외이사비율"];
	const SUFFIX_PCT = ["비율", "지분율"];

	const grade = $derived(row["등급"] ?? "—");
	const totalScore = $derived(row["총점"]);
	const scoreLabel = $derived(isFiniteNum(totalScore) ? totalScore.toFixed(1) : "—");

	const gradeTier = $derived(
		typeof grade === "string" && /^A/.test(grade) ? "up"
			: typeof grade === "string" && /^B/.test(grade) ? "neutral"
			: typeof grade === "string" && /^[CDF]/.test(grade) ? "down"
			: "neutral"
	);

	const sortedKeys = $derived(
		columns
			.filter((c) => c !== "stockCode" && c !== "등급" && c !== "총점")
			.sort((a, b) => {
				const ai = HIGHLIGHT_KEYS.indexOf(a);
				const bi = HIGHLIGHT_KEYS.indexOf(b);
				if (ai >= 0 && bi >= 0) return ai - bi;
				if (ai >= 0) return -1;
				if (bi >= 0) return 1;
				return a.localeCompare(b, "ko");
			})
	);

	function formatValue(key, value) {
		if (value == null || value === "") return "—";
		if (typeof value === "number") {
			const isPct = SUFFIX_PCT.some((s) => key.includes(s));
			if (isPct) return (value * 100).toFixed(1) + "%";
			if (Number.isInteger(value)) return value.toLocaleString();
			return value.toFixed(2);
		}
		return String(value);
	}

	function isHighlight(key) {
		return HIGHLIGHT_KEYS.includes(key);
	}
</script>

<div class="flex flex-col gap-4">
	<!-- Hero: 등급 + 총점 -->
	<div class="ed-card">
		<div class="ed-eyebrow mb-3">Governance Grade</div>
		{#if loading}
			<div class="flex items-center gap-8">
				<div class="editorial-skeleton h-12 w-24"></div>
				<div class="editorial-skeleton h-10 w-32"></div>
			</div>
		{:else if error}
			<div class="text-[12px]" style="color: var(--ed-down);">{error.message}</div>
		{:else}
			<div class="flex items-baseline gap-10">
				<div>
					<div class="text-[10px] uppercase tracking-wide" style="color: var(--ed-text-3);">등급</div>
					<div class="text-[44px] font-bold ed-num leading-none mt-1"
						style="color: {gradeTier === 'up' ? 'var(--ed-up)' : gradeTier === 'down' ? 'var(--ed-down)' : 'var(--ed-text)'}; font-family: var(--font-display);">
						{grade}
					</div>
				</div>
				<div>
					<div class="text-[10px] uppercase tracking-wide" style="color: var(--ed-text-3);">총점</div>
					<div class="text-[28px] ed-num leading-none mt-1" style="color: var(--ed-text);">
						{scoreLabel}
					</div>
				</div>
				<div class="text-[11px] max-w-xs" style="color: var(--ed-text-2);">
					지분구조 · 이사회 · 임원 변동 · 자사주 처분의 가중 합성
				</div>
			</div>
		{/if}
	</div>

	<!-- 16 지표 scorecard -->
	<div class="ed-card">
		<div class="flex items-baseline justify-between mb-3">
			<div class="ed-eyebrow">지표 Scorecard</div>
			<div class="text-[10px]" style="color: var(--ed-text-3);">{sortedKeys.length} 지표</div>
		</div>
		{#if loading}
			<div class="grid grid-cols-2 md:grid-cols-4 gap-2">
				{#each Array(8) as _}
					<div class="editorial-skeleton h-16"></div>
				{/each}
			</div>
		{:else if sortedKeys.length === 0}
			<div class="text-[12px] py-6 text-center" style="color: var(--ed-text-3);">데이터 없음</div>
		{:else}
			<div class="grid grid-cols-2 md:grid-cols-4 gap-2">
				{#each sortedKeys as key}
					<div class="rounded border p-2.5"
						style="border-color: {isHighlight(key) ? 'var(--ed-brand)' : 'var(--ed-line)'}; background: {isHighlight(key) ? 'color-mix(in srgb, var(--ed-brand) 4%, transparent)' : 'var(--ed-surface-2)'};">
						<div class="text-[10px] uppercase tracking-wide truncate" style="color: var(--ed-text-3);" title={key}>{key}</div>
						<div class="ed-num text-[15px] truncate mt-1"
							style="color: {isHighlight(key) ? 'var(--ed-brand)' : 'var(--ed-text)'};"
							title={String(row[key] ?? '')}>
							{formatValue(key, row[key])}
						</div>
					</div>
				{/each}
			</div>
		{/if}
	</div>
</div>
