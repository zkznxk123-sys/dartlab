<!--
	Quant Verdict — verdict (강세/중립/약세) + RSI/ADX/BB position + signals + beta.
	응답: { verdict, score, rsi, adx, aboveSma20, aboveSma60, bbPosition, signals: {goldenCross, rsiSignal, macdSignal}, relativeStrength, beta: {value, alpha, rSquared, tStat, nObs, capm}, benchmarkUsed: {...} }
-->
<script>
	import KpiTile from "$lib/dashboard/chart/KpiTile.svelte";
	import Gauge from "$lib/dashboard/chart/Gauge.svelte";
	import { fmtPct, isFiniteNum } from "$lib/dashboard/chart/util.js";

	let { payload = null, loading = false } = $props();

	const verdict = $derived(payload?.verdict || "—");
	const beta = $derived(payload?.beta || null);
	const signals = $derived(payload?.signals || {});
	const benchmark = $derived(payload?.benchmarkUsed || null);

	const verdictColor = $derived(
		verdict === "강세"
			? "var(--ed-up)"
			: verdict === "약세"
				? "var(--ed-down)"
				: "var(--ed-text-2)"
	);

	function signalLabel(v) {
		if (v === 1) return "BUY";
		if (v === -1) return "SELL";
		return "NEUTRAL";
	}
	function signalColor(v) {
		if (v > 0) return "var(--ed-up)";
		if (v < 0) return "var(--ed-down)";
		return "var(--ed-text-3)";
	}
</script>

{#if loading}
	<div class="ed-card"><div class="ed-eyebrow mb-2">Loading</div><div class="editorial-skeleton h-32 w-full"></div></div>
{:else if !payload}
	<div class="ed-card" style="border-style: dashed;"><div class="ed-eyebrow mb-1">No data</div><div class="text-[12px]" style="color: var(--ed-text-2);">verdict 데이터 없음</div></div>
{:else}
	<!-- Hero — verdict + score -->
	<div class="ed-card mb-4">
		<div class="grid grid-cols-[1fr_auto] gap-6 items-center">
			<div>
				<div class="ed-eyebrow mb-2">Technical Verdict</div>
				<div class="text-[44px] leading-none font-semibold" style="color: {verdictColor}; font-family: var(--font-display); letter-spacing: -0.02em;">
					{verdict}
				</div>
				<div class="text-[11px] mt-2" style="color: var(--ed-text-3);">
					{benchmark?.indexName || benchmark?.symbol || ""} {benchmark?.market ? `· ${benchmark.market}` : ""}
				</div>
			</div>
			<div class="flex flex-col items-end gap-1">
				<div class="ed-eyebrow">Score</div>
				<div class="ed-num text-[32px] font-medium" style="color: var(--ed-text);">
					{isFiniteNum(payload.score) ? payload.score.toFixed(0) : "—"}
				</div>
			</div>
		</div>
	</div>

	<!-- KPI 4 — RSI / ADX / BB position / relativeStrength -->
	<div class="grid grid-cols-4 gap-3 mb-4">
		<KpiTile label="RSI 14" value={payload.rsi} unit="%" />
		<KpiTile label="ADX 14" value={payload.adx} unit="%" />
		<KpiTile label="BB Position" value={payload.bbPosition} unit="%" />
		<KpiTile label="상대강도 RS" value={payload.relativeStrength} unit="" valueFormat={(v) => isFiniteNum(v) ? (v > 0 ? "+" : "") + v.toFixed(2) : "—"} />
	</div>

	<!-- Position vs SMA + Signals -->
	<div class="grid grid-cols-2 gap-4 mb-4">
		<div class="ed-card">
			<div class="ed-eyebrow mb-3">Trend Position</div>
			<ul class="flex flex-col gap-2 text-[12px]">
				<li class="flex items-center justify-between">
					<span style="color: var(--ed-text-2);">vs SMA-20</span>
					<span class="ed-num" style="color: {payload.aboveSma20 ? 'var(--ed-up)' : 'var(--ed-down)'};">
						{payload.aboveSma20 ? "▲ 위" : "▼ 아래"}
					</span>
				</li>
				<li class="flex items-center justify-between">
					<span style="color: var(--ed-text-2);">vs SMA-60</span>
					<span class="ed-num" style="color: {payload.aboveSma60 ? 'var(--ed-up)' : 'var(--ed-down)'};">
						{payload.aboveSma60 ? "▲ 위" : "▼ 아래"}
					</span>
				</li>
			</ul>
		</div>
		<div class="ed-card">
			<div class="ed-eyebrow mb-3">Signals</div>
			<ul class="flex flex-col gap-2 text-[12px]">
				<li class="flex items-center justify-between">
					<span style="color: var(--ed-text-2);">Golden Cross</span>
					<span class="editorial-chip" class:up={signals.goldenCross > 0} class:down={signals.goldenCross < 0} style="color: {signalColor(signals.goldenCross)};">
						{signalLabel(signals.goldenCross)}
					</span>
				</li>
				<li class="flex items-center justify-between">
					<span style="color: var(--ed-text-2);">RSI</span>
					<span class="editorial-chip" class:up={signals.rsiSignal > 0} class:down={signals.rsiSignal < 0} style="color: {signalColor(signals.rsiSignal)};">
						{signalLabel(signals.rsiSignal)}
					</span>
				</li>
				<li class="flex items-center justify-between">
					<span style="color: var(--ed-text-2);">MACD</span>
					<span class="editorial-chip" class:up={signals.macdSignal > 0} class:down={signals.macdSignal < 0} style="color: {signalColor(signals.macdSignal)};">
						{signalLabel(signals.macdSignal)}
					</span>
				</li>
			</ul>
		</div>
	</div>

	<!-- Beta breakdown -->
	{#if beta}
		<div class="ed-card mb-4">
			<div class="ed-eyebrow mb-3">CAPM · Beta vs {benchmark?.indexName || "Market"}</div>
			<div class="grid grid-cols-5 gap-3">
				<div class="flex flex-col gap-1">
					<div class="text-[10px]" style="color: var(--ed-text-3);">β</div>
					<div class="ed-num text-[18px]" style="color: var(--ed-text);">{isFiniteNum(beta.value) ? beta.value.toFixed(2) : "—"}</div>
				</div>
				<div class="flex flex-col gap-1">
					<div class="text-[10px]" style="color: var(--ed-text-3);">α (연환산)</div>
					<div class="ed-num text-[18px]" style="color: {isFiniteNum(beta.alpha) && beta.alpha > 0 ? 'var(--ed-up)' : 'var(--ed-down)'};">
						{isFiniteNum(beta.alpha) ? (beta.alpha > 0 ? "+" : "") + beta.alpha.toFixed(2) + "%" : "—"}
					</div>
				</div>
				<div class="flex flex-col gap-1">
					<div class="text-[10px]" style="color: var(--ed-text-3);">R²</div>
					<div class="ed-num text-[18px]" style="color: var(--ed-text);">{isFiniteNum(beta.rSquared) ? (beta.rSquared * 100).toFixed(1) + "%" : "—"}</div>
				</div>
				<div class="flex flex-col gap-1">
					<div class="text-[10px]" style="color: var(--ed-text-3);">t-stat</div>
					<div class="ed-num text-[18px]" style="color: var(--ed-text-2);">{isFiniteNum(beta.tStat) ? beta.tStat.toFixed(2) : "—"}</div>
				</div>
				<div class="flex flex-col gap-1">
					<div class="text-[10px]" style="color: var(--ed-text-3);">CAPM 기대수익</div>
					<div class="ed-num text-[18px]" style="color: var(--ed-text);">{isFiniteNum(beta.capm) ? beta.capm.toFixed(2) + "%" : "—"}</div>
				</div>
			</div>
		</div>
	{/if}
{/if}
