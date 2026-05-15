<!--
	CreditAxisCard — Credit 7 axes 공통 shape 시각화.
	response: { axis, score, weight, metrics: [{name, value?, score, ...}], grade, overallScore, _scoreMeaning, assumptions }
-->
<script>
	import { isFiniteNum, fmtPct } from "$lib/dashboard/chart/util.js";
	import KpiTile from "$lib/dashboard/chart/KpiTile.svelte";

	let { payload = null, loading = false } = $props();

	const axisName = $derived(payload?.axis || "");
	const score = $derived(payload?.score);
	const weight = $derived(payload?.weight);
	const grade = $derived(payload?.grade || "—");
	const overallScore = $derived(payload?.overallScore);
	const meaning = $derived(payload?._scoreMeaning || "");
	const metrics = $derived(Array.isArray(payload?.metrics) ? payload.metrics : []);
	const assumptions = $derived(payload?.assumptions || null);

	const gradeTier = $derived(
		typeof grade === "string" && /^(dCR-AAA|dCR-AA|dCR-A)/.test(grade) ? "up"
		: typeof grade === "string" && /^(dCR-BBB|dCR-BB)/.test(grade) ? "neutral"
		: typeof grade === "string" && /^(dCR-B|dCR-CCC|dCR-CC|dCR-C|dCR-D)/.test(grade) ? "down"
		: "neutral"
	);

	function fmtNum(v, digits = 2) {
		if (!isFiniteNum(v)) return "—";
		const a = Math.abs(v);
		if (a >= 1e12) return (v / 1e12).toFixed(digits) + "조";
		if (a >= 1e8) return (v / 1e8).toFixed(digits) + "억";
		if (a >= 1e4) return (v / 1e4).toFixed(digits) + "만";
		if (Number.isInteger(v)) return v.toString();
		return v.toFixed(digits);
	}

	function metricColor(s) {
		if (!isFiniteNum(s)) return "var(--ed-text-3)";
		// metric score 일반적으로 0~100 또는 0~10 — 높을수록 우호
		if (s >= 70 || (s <= 10 && s >= 7)) return "var(--ed-up)";
		if (s >= 40 || (s <= 10 && s >= 4)) return "var(--ed-text-2)";
		return "var(--ed-down)";
	}
</script>

{#if loading}
	<div class="flex flex-col gap-3">
		<div class="editorial-skeleton h-24"></div>
		<div class="grid grid-cols-3 gap-2">
			{#each Array(3) as _}<div class="editorial-skeleton h-20"></div>{/each}
		</div>
	</div>
{:else if !payload}
	<div class="ed-card" style="border-style: dashed;"><div class="ed-eyebrow">No data</div></div>
{:else}
	<div class="flex flex-col gap-3">
		<!-- Hero: axis score + grade + weight -->
		<div class="ed-card">
			<div class="flex items-baseline justify-between mb-3">
				<div class="ed-eyebrow">{axisName || "축"} · Credit</div>
				<div class="text-[10px]" style="color: var(--ed-text-3);">
					weight {isFiniteNum(weight) ? weight + "%" : "—"} · overall {isFiniteNum(overallScore) ? overallScore.toFixed(1) : "—"}
				</div>
			</div>
			<div class="flex items-baseline gap-8 flex-wrap">
				<div>
					<div class="text-[10px] uppercase tracking-wide" style="color: var(--ed-text-3);">축 점수</div>
					<div class="text-[36px] ed-num leading-none mt-1" style="color: var(--ed-text); font-family: var(--font-display);">
						{isFiniteNum(score) ? score.toFixed(2) : "—"}
					</div>
				</div>
				<div>
					<div class="text-[10px] uppercase tracking-wide" style="color: var(--ed-text-3);">전체 등급</div>
					<div class="text-[28px] font-bold ed-num leading-none mt-1"
						style="color: {gradeTier === 'up' ? 'var(--ed-up)' : gradeTier === 'down' ? 'var(--ed-down)' : 'var(--ed-text)'}; font-family: var(--font-display);">
						{grade}
					</div>
				</div>
				{#if meaning}
					<div class="text-[11px] max-w-md" style="color: var(--ed-text-2);">{meaning}</div>
				{/if}
			</div>
		</div>

		<!-- Metrics breakdown -->
		{#if metrics.length > 0}
			<div class="ed-card">
				<div class="ed-eyebrow mb-3">구성 지표 ({metrics.length})</div>
				<div class="flex flex-col gap-2">
					{#each metrics as m}
						<div class="grid grid-cols-[1fr_auto_auto] items-center gap-3 px-3 py-2 rounded border"
							style="border-color: var(--ed-line); background: var(--ed-surface-2);">
							<div class="min-w-0">
								<div class="text-[12.5px] truncate" style="color: var(--ed-text);">{m.name ?? "—"}</div>
								{#if m.description}
									<div class="text-[10px] truncate" style="color: var(--ed-text-3);">{m.description}</div>
								{/if}
							</div>
							<div class="text-right">
								{#if isFiniteNum(m.value)}
									<div class="ed-num text-[14px]" style="color: var(--ed-text);">{fmtNum(m.value)}</div>
									{#if m.unit}<div class="text-[9px]" style="color: var(--ed-text-3);">{m.unit}</div>{/if}
								{:else if m.value !== undefined && m.value !== null}
									<div class="text-[12px]" style="color: var(--ed-text-2);">{m.value}</div>
								{:else}
									<div class="text-[12px]" style="color: var(--ed-text-3);">—</div>
								{/if}
							</div>
							<div class="text-right" style="min-width: 64px;">
								<div class="text-[10px] uppercase tracking-wide" style="color: var(--ed-text-3);">score</div>
								<div class="ed-num text-[14px]" style="color: {metricColor(m.score)};">
									{isFiniteNum(m.score) ? m.score.toFixed(2) : "—"}
								</div>
							</div>
						</div>
					{/each}
				</div>
			</div>
		{:else}
			<div class="ed-card" style="border-style: dashed;">
				<div class="text-[12px] text-center py-4" style="color: var(--ed-text-3);">구성 지표 데이터 없음</div>
			</div>
		{/if}

		<!-- Assumptions (collapsible) -->
		{#if assumptions && typeof assumptions === "object" && Object.keys(assumptions).length > 0}
			<details class="ed-card">
				<summary class="cursor-pointer select-none ed-eyebrow" style="color: var(--ed-text-3);">계산 가정 · 출처 ({Object.keys(assumptions).length})</summary>
				<div class="mt-3 grid grid-cols-1 md:grid-cols-2 gap-2">
					{#each Object.entries(assumptions) as [k, v]}
						<div class="rounded border p-2" style="border-color: var(--ed-line);">
							<div class="text-[10px] uppercase tracking-wide" style="color: var(--ed-text-3);">{k}</div>
							<div class="text-[11px] mt-1" style="color: var(--ed-text-2);">{typeof v === "string" ? v : JSON.stringify(v)}</div>
						</div>
					{/each}
				</div>
			</details>
		{/if}
	</div>
{/if}
