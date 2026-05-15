<!--
	Quant Momentum — 모멘텀 verdict + 12-1 / 6-1 / time-series momentum + streak.
	응답: { stockCode, market, dataPoints, momentum6_1, momentum12_1, tsMomentum: {1m: {return, signal}, 3m: {...}, 6m: {...}}, highRatio52w, crashRisk, realizedVol6m, streak, streakDirection, momentumVerdict }
-->
<script>
	import KpiTile from "$lib/dashboard/chart/KpiTile.svelte";
	import { fmtPct, isFiniteNum } from "$lib/dashboard/chart/util.js";

	let { payload = null, loading = false } = $props();

	const ts = $derived(payload?.tsMomentum || {});
	const verdict = $derived(payload?.momentumVerdict || "—");

	const VERDICT_LABEL = {
		strong_bullish: "강한 매수",
		bullish: "매수",
		neutral: "중립",
		bearish: "매도",
		strong_bearish: "강한 매도",
	};
	const VERDICT_COLOR = {
		strong_bullish: "var(--ed-up)",
		bullish: "var(--ed-up)",
		neutral: "var(--ed-text-2)",
		bearish: "var(--ed-down)",
		strong_bearish: "var(--ed-down)",
	};

	const fmtMom = (v) => (isFiniteNum(v) ? (v > 0 ? "+" : "") + (v * 100).toFixed(1) + "%" : "—");

	function signalChipClass(sig) {
		if (sig === "long") return "up";
		if (sig === "short") return "down";
		return "";
	}
	function signalLabel(sig) {
		if (sig === "long") return "LONG";
		if (sig === "short") return "SHORT";
		return "FLAT";
	}
</script>

{#if loading}
	<div class="ed-card"><div class="ed-eyebrow mb-2">Loading</div><div class="editorial-skeleton h-32 w-full"></div></div>
{:else if !payload}
	<div class="ed-card" style="border-style: dashed;"><div class="ed-eyebrow mb-1">No data</div><div class="text-[12px]" style="color: var(--ed-text-2);">momentum 데이터 없음</div></div>
{:else}
	<!-- Hero verdict -->
	<div class="ed-card mb-4">
		<div class="grid grid-cols-[1fr_auto] gap-6 items-center">
			<div>
				<div class="ed-eyebrow mb-2">Momentum Verdict</div>
				<div class="text-[40px] leading-none font-semibold" style="color: {VERDICT_COLOR[verdict] || 'var(--ed-text-2)'}; font-family: var(--font-display); letter-spacing: -0.02em;">
					{VERDICT_LABEL[verdict] || verdict}
				</div>
				<div class="text-[11px] mt-2" style="color: var(--ed-text-3);">
					{payload.market ?? ""} · 데이터 {payload.dataPoints ?? 0}일
				</div>
			</div>
			<div class="flex flex-col items-end gap-1">
				<div class="ed-eyebrow">52w 위치</div>
				<div class="ed-num text-[24px] font-medium" style="color: var(--ed-text);">
					{isFiniteNum(payload.highRatio52w) ? (payload.highRatio52w * 100).toFixed(0) + "%" : "—"}
				</div>
			</div>
		</div>
	</div>

	<!-- KPI 4 -->
	<div class="grid grid-cols-4 gap-3 mb-4">
		<KpiTile label="6-1 모멘텀" value={payload.momentum6_1} valueFormat={fmtMom} />
		<KpiTile label="12-1 모멘텀" value={payload.momentum12_1} valueFormat={fmtMom} />
		<KpiTile label="실현변동성 6m" value={payload.realizedVol6m} valueFormat={(v) => isFiniteNum(v) ? (v * 100).toFixed(1) + "%" : "—"} />
		<KpiTile label="연속 {payload.streakDirection || ''}" value={payload.streak} unit="일" valueFormat={(v) => isFiniteNum(v) ? v + "일" : "—"} />
	</div>

	<!-- TS Momentum 3 horizons -->
	<div class="ed-card mb-4">
		<div class="ed-eyebrow mb-3">Time-Series Momentum (return + signal)</div>
		<div class="grid grid-cols-3 gap-3">
			{#each ["1m", "3m", "6m"] as horizon}
				{@const m = ts[horizon]}
				<div class="ed-card" style="background: var(--ed-surface-2);">
					<div class="flex items-center justify-between mb-2">
						<div class="ed-eyebrow">{horizon}</div>
						<span class="editorial-chip {signalChipClass(m?.signal)}">{signalLabel(m?.signal)}</span>
					</div>
					<div class="ed-num text-[20px]" style="color: {isFiniteNum(m?.return) && m.return > 0 ? 'var(--ed-up)' : 'var(--ed-down)'};">
						{fmtMom(m?.return)}
					</div>
				</div>
			{/each}
		</div>
	</div>

	<!-- Crash risk -->
	{#if payload.crashRisk}
		<div class="ed-card" style="border-color: {payload.crashRisk === 'high' ? 'var(--ed-down)' : payload.crashRisk === 'medium' ? 'var(--ed-warn)' : 'var(--ed-up)'};">
			<div class="ed-eyebrow mb-1">Crash Risk</div>
			<div class="text-[14px]" style="color: {payload.crashRisk === 'high' ? 'var(--ed-down)' : payload.crashRisk === 'medium' ? 'var(--ed-warn)' : 'var(--ed-up)'};">
				{payload.crashRisk.toUpperCase()}
				{#if payload.crashRisk === 'high'}— 단기 급락 가능성 모니터{:else if payload.crashRisk === 'medium'}— 변동성 보통{:else}— 안정{/if}
			</div>
		</div>
	{/if}
{/if}
