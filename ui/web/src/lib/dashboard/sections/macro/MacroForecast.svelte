<!--
	Macro > Forecast — recessionProb / LEI / sahmRule / hamiltonRegime / nowcast.
-->
<script>
	import { isFiniteNum } from "$lib/dashboard/chart/util.js";

	let { payload = null, loading = false } = $props();

	const lei = $derived(payload?.lei || null);
	const recessionProb = $derived(payload?.recessionProb);
	const sahmRule = $derived(payload?.sahmRule || null);
	const hamiltonRegime = $derived(payload?.hamiltonRegime || null);
	const nowcast = $derived(payload?.nowcast || null);
	const market = $derived(payload?.market || "—");

	function signalColor(s) {
		if (!s) return "var(--ed-text-3)";
		const str = String(s).toLowerCase();
		if (str.includes("recess") || str.includes("warning") || str.includes("contract")) return "var(--ed-down)";
		if (str.includes("expan") || str.includes("growth")) return "var(--ed-up)";
		if (str.includes("caution")) return "var(--ed-text-2)";
		return "var(--ed-text)";
	}
</script>

{#if loading}
	<div class="flex flex-col gap-3">{#each Array(3) as _}<div class="editorial-skeleton h-28"></div>{/each}</div>
{:else if !payload}
	<div class="ed-card" style="border-style: dashed;"><div class="ed-eyebrow">No data</div></div>
{:else}
	<div class="flex flex-col gap-3">
		<div class="ed-card">
			<div class="flex items-baseline justify-between mb-3">
				<div class="ed-eyebrow">Recession Forecast · {market}</div>
				<div class="text-[10px]" style="color: var(--ed-text-3);">LEI · Sahm · Hamilton · Nowcast 종합</div>
			</div>
			<div class="grid grid-cols-2 md:grid-cols-4 gap-3">
				<div class="rounded border p-3" style="border-color: var(--ed-line); background: var(--ed-surface-2);">
					<div class="text-[10px] uppercase tracking-wide" style="color: var(--ed-text-3);">Recession Prob</div>
					<div class="ed-num text-[24px] mt-1" style="color: {isFiniteNum(recessionProb) && recessionProb > 0.3 ? 'var(--ed-down)' : 'var(--ed-text)'}; font-family: var(--font-display);">
						{isFiniteNum(recessionProb) ? (recessionProb * 100).toFixed(1) + "%" : "—"}
					</div>
				</div>
				<div class="rounded border p-3" style="border-color: var(--ed-line); background: var(--ed-surface-2);">
					<div class="text-[10px] uppercase tracking-wide" style="color: var(--ed-text-3);">LEI MoM</div>
					<div class="ed-num text-[24px] mt-1" style="color: {isFiniteNum(lei?.mom) && lei.mom < 0 ? 'var(--ed-down)' : 'var(--ed-text)'}; font-family: var(--font-display);">
						{isFiniteNum(lei?.mom) ? (lei.mom > 0 ? "+" : "") + lei.mom.toFixed(2) + "%" : "—"}
					</div>
					<div class="text-[10px] mt-0.5" style="color: {signalColor(lei?.signalLabel || lei?.signal)};">{lei?.signalLabel || lei?.signal || "—"}</div>
				</div>
				<div class="rounded border p-3" style="border-color: var(--ed-line); background: var(--ed-surface-2);">
					<div class="text-[10px] uppercase tracking-wide" style="color: var(--ed-text-3);">Sahm Rule</div>
					<div class="text-[16px] mt-1" style="color: {signalColor(sahmRule?.signal)};">
						{sahmRule?.signal || sahmRule?.value || "—"}
					</div>
				</div>
				<div class="rounded border p-3" style="border-color: var(--ed-line); background: var(--ed-surface-2);">
					<div class="text-[10px] uppercase tracking-wide" style="color: var(--ed-text-3);">Hamilton</div>
					<div class="text-[16px] mt-1" style="color: {signalColor(hamiltonRegime?.regime)};">
						{hamiltonRegime?.regimeLabel || hamiltonRegime?.regime || "—"}
					</div>
				</div>
			</div>
		</div>

		{#if lei && typeof lei === "object"}
			<div class="ed-card">
				<div class="ed-eyebrow mb-3">LEI 세부 · {lei.description || ""}</div>
				<div class="grid grid-cols-2 md:grid-cols-4 gap-2">
					{#each Object.entries(lei) as [k, v]}
						<div class="rounded border p-2" style="border-color: var(--ed-line);">
							<div class="text-[10px] uppercase tracking-wide truncate" style="color: var(--ed-text-3);" title={k}>{k}</div>
							<div class="ed-num text-[12px] mt-1 truncate" style="color: var(--ed-text);">
								{typeof v === "number" ? (Number.isInteger(v) ? v : v.toFixed(3)) : (typeof v === "string" ? v : "—")}
							</div>
						</div>
					{/each}
				</div>
			</div>
		{/if}

		{#if nowcast}
			<div class="ed-card">
				<div class="ed-eyebrow mb-3">Nowcast</div>
				<pre class="text-[11px] overflow-x-auto" style="color: var(--ed-text-2);">{typeof nowcast === "string" ? nowcast : JSON.stringify(nowcast, null, 2)}</pre>
			</div>
		{/if}
	</div>
{/if}
