<!--
	QuantForecast — { stockCode, market, lastClose, lastDate, modelChosen, modelsConsidered, horizon, nObs, forecasts? }
	forecasts 가 history list 면 LineTrend, scalar 면 KPI.
-->
<script>
	import { isFiniteNum } from "$lib/dashboard/chart/util.js";
	import LineTrend from "$lib/dashboard/chart/LineTrend.svelte";

	let { payload = null, loading = false } = $props();

	const lastClose = $derived(payload?.lastClose);
	const lastDate = $derived(payload?.lastDate || "—");
	const modelChosen = $derived(payload?.modelChosen || "—");
	const modelsConsidered = $derived(Array.isArray(payload?.modelsConsidered) ? payload.modelsConsidered : []);
	const horizon = $derived(payload?.horizon);
	const nObs = $derived(payload?.nObs);

	const forecastSeries = $derived.by(() => {
		if (!payload) return null;
		const f = payload.forecasts || payload.predicted || payload.forecastPath;
		if (Array.isArray(f) && f.length > 0) {
			if (typeof f[0] === "object" && f[0] !== null) {
				const xKey = f[0].date ? "date" : f[0].period ? "period" : "step";
				const yKey = f[0].value !== undefined ? "value" : f[0].close !== undefined ? "close" : f[0].forecast !== undefined ? "forecast" : null;
				if (yKey) return { history: f, xKey, series: [{ key: yKey, label: "Forecast", color: "var(--ed-brand)" }] };
			} else if (typeof f[0] === "number") {
				const history = f.map((v, i) => ({ step: `t+${i+1}`, value: v }));
				return { history, xKey: "step", series: [{ key: "value", label: "Forecast", color: "var(--ed-brand)" }] };
			}
		}
		return null;
	});

	const metaEntries = $derived(
		payload
			? Object.entries(payload).filter(([k, v]) =>
				!["stockCode","market","lastClose","lastDate","modelChosen","modelsConsidered","horizon","nObs","forecasts","predicted","forecastPath"].includes(k)
				&& (typeof v === "number" || typeof v === "string"))
			: []
	);
</script>

{#if loading}
	<div class="flex flex-col gap-3">
		<div class="editorial-skeleton h-28"></div>
		<div class="editorial-skeleton h-56"></div>
	</div>
{:else if !payload}
	<div class="ed-card" style="border-style: dashed;"><div class="ed-eyebrow">No data</div></div>
{:else}
	<div class="flex flex-col gap-3">
		<!-- Model hero -->
		<div class="ed-card">
			<div class="flex items-baseline justify-between mb-3">
				<div class="ed-eyebrow">Forecast · {modelChosen}</div>
				<div class="text-[10px]" style="color: var(--ed-text-3);">
					obs {nObs ?? "—"} · horizon {horizon ?? "—"} · {lastDate}
				</div>
			</div>
			<div class="flex items-baseline gap-8 flex-wrap">
				<div>
					<div class="text-[10px] uppercase tracking-wide" style="color: var(--ed-text-3);">Last Close</div>
					<div class="ed-num text-[24px] leading-none mt-1" style="color: var(--ed-text); font-family: var(--font-display);">
						{isFiniteNum(lastClose) ? lastClose.toLocaleString() : "—"}
					</div>
				</div>
				<div>
					<div class="text-[10px] uppercase tracking-wide" style="color: var(--ed-text-3);">Model Chosen</div>
					<div class="text-[20px] font-medium leading-none mt-1" style="color: var(--ed-brand); font-family: var(--font-display);">
						{modelChosen}
					</div>
				</div>
				{#if modelsConsidered.length > 0}
					<div>
						<div class="text-[10px] uppercase tracking-wide" style="color: var(--ed-text-3);">Candidates</div>
						<div class="text-[12px] mt-1" style="color: var(--ed-text-2);">{modelsConsidered.join(" · ")}</div>
					</div>
				{/if}
			</div>
		</div>

		<!-- Forecast path -->
		{#if forecastSeries}
			<div class="ed-card">
				<div class="ed-eyebrow mb-3">예측 경로</div>
				<LineTrend history={forecastSeries.history} series={forecastSeries.series} xKey={forecastSeries.xKey} height={220} />
			</div>
		{/if}

		<!-- Other meta -->
		{#if metaEntries.length > 0}
			<div class="ed-card">
				<div class="ed-eyebrow mb-3">모델 지표 ({metaEntries.length})</div>
				<div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-2">
					{#each metaEntries as [k, v]}
						<div class="rounded border p-2" style="border-color: var(--ed-line);">
							<div class="text-[10px] uppercase tracking-wide truncate" style="color: var(--ed-text-3);" title={k}>{k}</div>
							<div class="ed-num text-[12px] mt-1 truncate" style="color: var(--ed-text);">
								{typeof v === "number" ? (Number.isInteger(v) ? v.toString() : v.toFixed(3)) : v}
							</div>
						</div>
					{/each}
				</div>
			</div>
		{/if}
	</div>
{/if}
