<!--
	Company > Governance — Editorial 톤. 등급/총점 Hero + 3 그룹 카드 (지분구조 · 이사회/감사 · 임원·보수).
	각 KPI 는 단위 정직 (지분율 24.1 = 24.1% 직접, 곱하기 X) + 점수 게이지.
-->
<script>
	import { onMount, untrack } from "svelte";
	import { getDashboardStore } from "$lib/stores/dashboardStore.svelte.js";
	import { loadGovernance } from "$lib/dashboard/data/loaders.js";
	import { isFiniteNum } from "$lib/dashboard/chart/util.js";

	const dash = getDashboardStore();

	let loading = $state(true);
	let row = $state({});
	let error = $state(null);

	async function fetchAll() {
		loading = true;
		error = null;
		const result = await loadGovernance(dash.stockCode);
		if (result.ok) row = result.data.row;
		else { error = result.error; row = {}; }
		loading = false;
	}

	$effect(() => {
		dash.stockCode;
		untrack(() => fetchAll());
	});

	onMount(() => fetchAll());

	// 각 S_xxx 의 max (governance 엔진 가중치 기준)
	const SCORE_MAX = {
		S_지분: 20,
		S_사외: 30,
		S_보수: 10,
		S_감사: 15,
		S_분산: 25,
	};

	const grade = $derived(row["등급"] ?? "—");
	const totalScore = $derived(row["총점"]);
	const effectiveAxes = $derived(row["유효축수"]);
	const auditOpinion = $derived(row["감사의견"] || "");

	const gradeTier = $derived(
		typeof grade === "string" && /^A/.test(grade) ? "up"
		: typeof grade === "string" && /^B/.test(grade) ? "neutral"
		: typeof grade === "string" && /^[CDF]/.test(grade) ? "down"
		: "neutral"
	);

	function scorePct(scoreKey) {
		const v = row[scoreKey];
		const max = SCORE_MAX[scoreKey];
		if (!isFiniteNum(v) || !max) return null;
		return (v / max) * 100;
	}

	function scoreColor(pct) {
		if (pct == null) return "var(--ed-text-3)";
		if (pct >= 70) return "var(--ed-up)";
		if (pct >= 40) return "var(--ed-text-2)";
		return "var(--ed-down)";
	}

	function fmt1(v) {
		return isFiniteNum(v) ? v.toFixed(1) : "—";
	}

	// 그룹 정의 — 각 KPI: { key, label, unit, format, score? (S_xxx), note? }
	const GROUPS = $derived([
		{
			title: "지분구조",
			eyebrow: "지분 · 분산",
			items: [
				{ key: "지분율", label: "최대주주 지분율", value: row["지분율"], unit: "%", display: fmt1(row["지분율"]) + "%", scoreKey: "S_지분" },
				{ key: "소액주주지분", label: "소액주주 지분", value: row["소액주주지분"], unit: "%", display: fmt1(row["소액주주지분"]) + "%", scoreKey: "S_분산" },
			],
		},
		{
			title: "이사회·감사",
			eyebrow: "독립성 · 감사품질",
			items: [
				{ key: "사외이사비율", label: "사외이사 비율", value: row["사외이사비율"], unit: "%", display: fmt1(row["사외이사비율"]) + "%", scoreKey: "S_사외" },
				{ key: "감사의견", label: "감사의견", value: auditOpinion, unit: "", display: auditOpinion || "—", scoreKey: "S_감사", hideIfEmpty: !auditOpinion },
			],
		},
		{
			title: "임원·보수",
			eyebrow: "보수 · 안정성",
			items: [
				{ key: "pay_ratio", label: "최고/직원 보수배수", value: row["pay_ratio"], unit: "배", display: isFiniteNum(row["pay_ratio"]) ? row["pay_ratio"].toFixed(1) + "배" : "—", scoreKey: "S_보수" },
				{ key: "중도사임", label: "임원 중도사임", value: row["중도사임"], unit: "건", display: (row["중도사임"] ?? 0) + "건", warnIf: (v) => v > 0 },
				{ key: "겸직", label: "겸직", value: row["겸직"], unit: "건", display: (row["겸직"] ?? 0) + "건", warnIf: (v) => v > 0 },
			],
		},
	]);
</script>

<div class="flex flex-col gap-4">
	<!-- Hero — 등급 + 총점 + 5 축 게이지 미리보기 -->
	<div class="ed-card">
		<div class="flex items-baseline justify-between mb-3">
			<div class="ed-eyebrow">Governance Grade</div>
			<div class="text-[10px]" style="color: var(--ed-text-3);">
				5 축 가중 평가 · 유효 {effectiveAxes ?? "—"} 축
			</div>
		</div>

		{#if loading}
			<div class="flex items-center gap-8">
				<div class="editorial-skeleton h-12 w-24"></div>
				<div class="editorial-skeleton h-10 w-32"></div>
			</div>
		{:else if error}
			<div class="text-[12px]" style="color: var(--ed-down);">{error.message}</div>
		{:else}
			<div class="flex items-baseline gap-10 flex-wrap mb-4">
				<div>
					<div class="text-[10px] uppercase tracking-wide" style="color: var(--ed-text-3);">등급</div>
					<div class="text-[48px] font-bold ed-num leading-none mt-1"
						style="color: {gradeTier === 'up' ? 'var(--ed-up)' : gradeTier === 'down' ? 'var(--ed-down)' : 'var(--ed-text)'}; font-family: var(--font-display);">
						{grade}
					</div>
				</div>
				<div>
					<div class="text-[10px] uppercase tracking-wide" style="color: var(--ed-text-3);">총점</div>
					<div class="text-[32px] ed-num leading-none mt-1" style="color: var(--ed-text); font-family: var(--font-display);">
						{isFiniteNum(totalScore) ? totalScore.toFixed(1) : "—"}<span class="text-[16px]" style="color: var(--ed-text-3);">/100</span>
					</div>
				</div>
				<div class="text-[11px] max-w-md" style="color: var(--ed-text-2);">
					지분구조 · 이사회 · 감사 · 보수 · 분산 5 축 가중. 점수 높을수록 거버넌스 우수.
				</div>
			</div>

			<!-- 5 축 mini gauge -->
			<div class="grid grid-cols-5 gap-2">
				{#each Object.entries(SCORE_MAX) as [key, max]}
					{@const v = row[key]}
					{@const pct = isFiniteNum(v) ? (v / max) * 100 : null}
					<div class="rounded border p-2" style="border-color: var(--ed-line); background: var(--ed-surface-2);">
						<div class="text-[10px] uppercase tracking-wide" style="color: var(--ed-text-3);">{key.replace("S_", "")}</div>
						<div class="ed-num text-[16px] mt-1" style="color: {scoreColor(pct)};">
							{isFiniteNum(v) ? v.toFixed(1) : "—"}<span class="text-[9px]" style="color: var(--ed-text-3);">/{max}</span>
						</div>
						<div class="mt-1.5 h-1 rounded-full overflow-hidden" style="background: var(--ed-line);">
							<div class="h-full rounded-full" style="width: {pct ?? 0}%; background: {scoreColor(pct)};"></div>
						</div>
					</div>
				{/each}
			</div>
		{/if}
	</div>

	<!-- 3 그룹 카드 -->
	{#if !loading && !error}
		{#each GROUPS as g}
			{@const visibleItems = g.items.filter((it) => !it.hideIfEmpty)}
			{#if visibleItems.length > 0}
				<div class="ed-card">
					<div class="flex items-baseline justify-between mb-3">
						<div class="ed-eyebrow">{g.title}</div>
						<div class="text-[10px]" style="color: var(--ed-text-3);">{g.eyebrow}</div>
					</div>
					<div class="grid grid-cols-1 md:grid-cols-3 gap-3">
						{#each visibleItems as it}
							{@const sPct = it.scoreKey ? scorePct(it.scoreKey) : null}
							{@const sMax = SCORE_MAX[it.scoreKey]}
							{@const sVal = it.scoreKey ? row[it.scoreKey] : null}
							{@const warn = it.warnIf && isFiniteNum(it.value) && it.warnIf(it.value)}
							<div class="rounded border p-3" style="border-color: {warn ? 'var(--ed-down)' : 'var(--ed-line)'}; background: {warn ? 'color-mix(in srgb, var(--ed-down) 6%, transparent)' : 'var(--ed-surface-2)'};">
								<div class="text-[10.5px] uppercase tracking-wide truncate" style="color: var(--ed-text-3);">{it.label}</div>
								<div class="ed-num text-[24px] mt-1" style="color: {warn ? 'var(--ed-down)' : 'var(--ed-text)'}; font-family: var(--font-display);">
									{it.display}
								</div>
								{#if it.scoreKey && isFiniteNum(sVal) && sMax}
									<div class="mt-2 flex items-center gap-2">
										<div class="flex-1 h-1 rounded-full overflow-hidden" style="background: var(--ed-line);">
											<div class="h-full rounded-full" style="width: {sPct}%; background: {scoreColor(sPct)};"></div>
										</div>
										<span class="text-[10px] ed-num" style="color: {scoreColor(sPct)};">{sVal.toFixed(1)}/{sMax}</span>
									</div>
								{/if}
							</div>
						{/each}
					</div>
				</div>
			{/if}
		{/each}
	{/if}
</div>
