<!--
	QuantSignals — { signals:{goldenCross,rsiSignal,macdSignal,bollingerSignal}, signalSummary:{bullish,bearish}, recentEvents:[{date,type,direction}] }
-->
<script>
	import { isFiniteNum } from "$lib/dashboard/chart/util.js";

	let { payload = null, loading = false } = $props();

	const signals = $derived(payload?.signals || {});
	const summary = $derived(payload?.signalSummary || {});
	const events = $derived(Array.isArray(payload?.recentEvents) ? payload.recentEvents : []);

	const SIGNAL_LABELS = {
		goldenCross: "Golden / Death Cross",
		rsiSignal: "RSI",
		macdSignal: "MACD",
		bollingerSignal: "Bollinger",
		stochSignal: "Stochastic",
		volumeSignal: "Volume",
	};

	function signalTone(v) {
		if (!isFiniteNum(v)) return { color: "var(--ed-text-3)", label: "—" };
		if (v > 0) return { color: "var(--ed-up)", label: v >= 2 ? "Strong ↑" : "Bullish ↑" };
		if (v < 0) return { color: "var(--ed-down)", label: v <= -2 ? "Strong ↓" : "Bearish ↓" };
		return { color: "var(--ed-text-2)", label: "Neutral" };
	}

	function eventColor(dir) {
		if (!dir) return "var(--ed-text-3)";
		const s = String(dir).toLowerCase();
		if (s.includes("bull") || s === "up" || s === "+") return "var(--ed-up)";
		if (s.includes("bear") || s === "down" || s === "-") return "var(--ed-down)";
		return "var(--ed-text-2)";
	}
</script>

{#if loading}
	<div class="flex flex-col gap-3">
		<div class="editorial-skeleton h-28"></div>
		<div class="grid grid-cols-4 gap-2">{#each Array(4) as _}<div class="editorial-skeleton h-16"></div>{/each}</div>
	</div>
{:else if !payload}
	<div class="ed-card" style="border-style: dashed;"><div class="ed-eyebrow">No data</div></div>
{:else}
	<div class="flex flex-col gap-3">
		<!-- Hero: bullish vs bearish 카운트 -->
		<div class="ed-card">
			<div class="ed-eyebrow mb-3">Signal Summary</div>
			<div class="flex items-baseline gap-10 flex-wrap">
				<div>
					<div class="text-[10px] uppercase tracking-wide" style="color: var(--ed-text-3);">Bullish</div>
					<div class="text-[36px] ed-num leading-none mt-1" style="color: var(--ed-up); font-family: var(--font-display);">
						{isFiniteNum(summary.bullish) ? summary.bullish : "—"}
					</div>
				</div>
				<div>
					<div class="text-[10px] uppercase tracking-wide" style="color: var(--ed-text-3);">Bearish</div>
					<div class="text-[36px] ed-num leading-none mt-1" style="color: var(--ed-down); font-family: var(--font-display);">
						{isFiniteNum(summary.bearish) ? summary.bearish : "—"}
					</div>
				</div>
				<div>
					<div class="text-[10px] uppercase tracking-wide" style="color: var(--ed-text-3);">Net</div>
					<div class="text-[24px] ed-num leading-none mt-1" style="color: var(--ed-text); font-family: var(--font-display);">
						{(summary.bullish ?? 0) - (summary.bearish ?? 0) >= 0 ? "+" : ""}{(summary.bullish ?? 0) - (summary.bearish ?? 0)}
					</div>
				</div>
			</div>
		</div>

		<!-- Individual signals -->
		<div class="ed-card">
			<div class="ed-eyebrow mb-3">개별 시그널</div>
			<div class="grid grid-cols-2 md:grid-cols-4 gap-2">
				{#each Object.entries(signals) as [k, v]}
					{@const tone = signalTone(v)}
					<div class="rounded border p-2.5" style="border-color: var(--ed-line); background: var(--ed-surface-2);">
						<div class="text-[10px] uppercase tracking-wide truncate" style="color: var(--ed-text-3);">{SIGNAL_LABELS[k] || k}</div>
						<div class="text-[14px] mt-1" style="color: {tone.color};">{tone.label}</div>
						<div class="ed-num text-[11px] mt-0.5" style="color: var(--ed-text-3);">{isFiniteNum(v) ? v : "—"}</div>
					</div>
				{/each}
			</div>
		</div>

		<!-- Recent events -->
		{#if events.length > 0}
			<div class="ed-card">
				<div class="ed-eyebrow mb-3">최근 이벤트 ({events.length})</div>
				<ul class="flex flex-col gap-1.5">
					{#each events as e}
						<li class="grid grid-cols-[96px_1fr_96px] items-center gap-2 px-2.5 py-1.5 rounded border text-[12px]"
							style="border-color: var(--ed-line); background: var(--ed-surface-2);">
							<span class="ed-num text-[11px]" style="color: var(--ed-text-3);">{e.date || "—"}</span>
							<span style="color: var(--ed-text);">{e.type || "—"}</span>
							<span class="text-right" style="color: {eventColor(e.direction)};">{e.direction || "—"}</span>
						</li>
					{/each}
				</ul>
			</div>
		{/if}
	</div>
{/if}
