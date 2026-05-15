<!--
	Credit Grade — dCR 종합 등급 + 7축 가중평균 + outlook.
	응답: { grade, gradeRaw, gradeDescription, gradeCategory, investmentGrade, score, healthScore, currentScore, pdEstimate, eCR, outlook, sector, captiveFinance, holding, latestPeriod, chsAdjustment, notchAdjustment, divergenceExplanation, methodologyVersion, axes: [{name, score, weight, contribution, metrics}] }
-->
<script>
	import Gauge from "$lib/dashboard/chart/Gauge.svelte";
	import KpiTile from "$lib/dashboard/chart/KpiTile.svelte";
	import { isFiniteNum, fmtPct } from "$lib/dashboard/chart/util.js";

	let { payload = null, loading = false } = $props();

	const grade = $derived(payload?.grade || "—");
	const investmentGrade = $derived(payload?.investmentGrade);
	const outlook = $derived(payload?.outlook || "—");
	const axes = $derived(payload?.axes || []);

	const gradeColor = $derived.by(() => {
		const g = payload?.gradeRaw || "";
		if (g.startsWith("AAA") || g.startsWith("AA")) return "var(--ed-up)";
		if (g.startsWith("A")) return "var(--ed-up)";
		if (g.startsWith("BBB")) return "var(--ed-text)";
		if (g.startsWith("BB") || g.startsWith("B")) return "var(--ed-warn)";
		return "var(--ed-down)";
	});

	const outlookColor = $derived(
		outlook?.includes("긍정")
			? "var(--ed-up)"
			: outlook?.includes("부정")
				? "var(--ed-down)"
				: "var(--ed-text-2)"
	);
</script>

{#if loading}
	<div class="ed-card"><div class="ed-eyebrow mb-2">Loading</div><div class="editorial-skeleton h-32 w-full"></div></div>
{:else if !payload}
	<div class="ed-card" style="border-style: dashed;"><div class="ed-eyebrow mb-1">No data</div><div class="text-[12px]" style="color: var(--ed-text-2);">grade 데이터 없음</div></div>
{:else}
	<!-- Hero grade card -->
	<div class="ed-card mb-4">
		<div class="grid grid-cols-[auto_1fr_auto] gap-8 items-center">
			<div>
				<div class="ed-eyebrow mb-2">Credit Grade</div>
				<div class="text-[56px] leading-none font-semibold" style="color: {gradeColor}; font-family: var(--font-display); letter-spacing: -0.03em;">
					{grade}
				</div>
				<div class="text-[11px] mt-2" style="color: var(--ed-text-3);">
					{payload.gradeCategory || ""} {investmentGrade ? "· 투자적격" : "· 투기등급"}
				</div>
			</div>
			<div class="flex flex-col gap-3">
				<KpiTile label="Health Score" value={payload.healthScore} unit="%" />
				<div class="grid grid-cols-2 gap-3">
					<div>
						<div class="text-[10px]" style="color: var(--ed-text-3);">eCR</div>
						<div class="ed-num text-[16px]" style="color: var(--ed-text);">{payload.eCR || "—"}</div>
					</div>
					<div>
						<div class="text-[10px]" style="color: var(--ed-text-3);">PD 추정</div>
						<div class="ed-num text-[16px]" style="color: var(--ed-text);">{isFiniteNum(payload.pdEstimate) ? (payload.pdEstimate * 100).toFixed(2) + "%" : "—"}</div>
					</div>
				</div>
			</div>
			<div class="flex flex-col items-end gap-1">
				<div class="ed-eyebrow">Outlook</div>
				<div class="text-[18px] font-medium" style="color: {outlookColor};">{outlook}</div>
				<div class="text-[10px]" style="color: var(--ed-text-3);">{payload.latestPeriod ?? ""}</div>
			</div>
		</div>
	</div>

	<!-- 7축 contribution stacked bar -->
	{#if axes.length > 0}
		<div class="ed-card mb-4">
			<div class="ed-eyebrow mb-3">7축 가중 contribution (낮을수록 우량)</div>
			<ul class="flex flex-col gap-2">
				{#each axes as ax}
					{@const cMax = Math.max(...axes.map((a) => Math.abs(a.contribution || 0)), 1)}
					{@const w = Math.abs(ax.contribution || 0) / cMax * 100}
					<li class="grid grid-cols-[160px_1fr_100px] items-center gap-3 text-[11.5px]">
						<span style="color: var(--ed-text-2);" title={ax.name}>{ax.name}</span>
						<div class="relative h-3 rounded-sm" style="background: var(--ed-surface-2);">
							<div class="absolute top-0 left-0 bottom-0 rounded-sm" style="width: {w}%; background: var(--ed-brand); opacity: 0.78;"></div>
						</div>
						<span class="ed-num text-right" style="color: var(--ed-text);">
							{isFiniteNum(ax.score) ? ax.score.toFixed(2) : "—"} <span class="text-[10px]" style="color: var(--ed-text-3);">(w {isFiniteNum(ax.weight) ? ax.weight : "—"}%)</span>
						</span>
					</li>
				{/each}
			</ul>
		</div>
	{/if}

	<!-- Divergence / chs / notch explanations -->
	{#if Array.isArray(payload.divergenceExplanation) && payload.divergenceExplanation.length > 0}
		<div class="ed-card mb-4" style="border-left: 2px solid var(--ed-brand);">
			<div class="ed-eyebrow mb-2">Methodology Notes ({payload.methodologyVersion || ""})</div>
			<ul class="flex flex-col gap-1 text-[11.5px]" style="color: var(--ed-text-2);">
				{#each payload.divergenceExplanation as note}
					<li>· {note}</li>
				{/each}
			</ul>
		</div>
	{/if}

	{#if payload.chsAdjustment?.status}
		<div class="ed-card mb-4">
			<div class="ed-eyebrow mb-2">CHS Adjustment</div>
			<div class="grid grid-cols-4 gap-3 text-[12px]">
				<div><span style="color: var(--ed-text-3);">Status</span><div class="ed-num" style="color: var(--ed-text);">{payload.chsAdjustment.status}</div></div>
				<div><span style="color: var(--ed-text-3);">Adjusted Score</span><div class="ed-num" style="color: var(--ed-text);">{isFiniteNum(payload.chsAdjustment.adjustedScore) ? payload.chsAdjustment.adjustedScore.toFixed(2) : "—"}</div></div>
				<div><span style="color: var(--ed-text-3);">CHS Score</span><div class="ed-num" style="color: var(--ed-text);">{isFiniteNum(payload.chsAdjustment.chsScore) ? payload.chsAdjustment.chsScore.toFixed(2) : "—"}</div></div>
				<div><span style="color: var(--ed-text-3);">Adjustment</span><div class="ed-num" style="color: {isFiniteNum(payload.chsAdjustment.adjustment) && payload.chsAdjustment.adjustment < 0 ? 'var(--ed-up)' : 'var(--ed-down)'};">{isFiniteNum(payload.chsAdjustment.adjustment) ? (payload.chsAdjustment.adjustment > 0 ? "+" : "") + payload.chsAdjustment.adjustment.toFixed(2) : "—"}</div></div>
			</div>
		</div>
	{/if}
{/if}
