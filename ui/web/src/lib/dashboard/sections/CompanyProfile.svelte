<!--
	Company > Profile — 회사 메타 + market summary KPI strip. Editorial 톤.
-->
<script>
	import { onMount } from "svelte";
	import { getDashboardStore } from "$lib/stores/dashboardStore.svelte.js";
	import { loadMarket, loadWorkforce } from "$lib/dashboard/data/loaders.js";
	import KpiTile from "$lib/dashboard/chart/KpiTile.svelte";
	import { fmtKrw, isFiniteNum } from "$lib/dashboard/chart/util.js";

	const dash = getDashboardStore();

	let loading = $state(true);
	let market = $state({ rows: [], preview: "" });
	let workforce = $state({ rows: [], columns: [] });
	let error = $state(null);

	async function fetchAll() {
		loading = true;
		error = null;
		const code = dash.stockCode;
		const [m, w] = await Promise.all([loadMarket(code), loadWorkforce(code)]);
		if (m.ok) market = m.data;
		else error = m.error;
		if (w.ok) workforce = w.data;
		loading = false;
	}

	$effect(() => {
		dash.stockCode;
		fetchAll();
	});

	onMount(() => fetchAll());

	const m = $derived(market.rows[0] || {});
	const marketCap = $derived(m["시가총액"] ?? m["marketCap"] ?? null);
	const price = $derived(m["종가"] ?? m["price"] ?? null);
	const volume = $derived(m["거래량"] ?? m["volume"] ?? null);
	const foreigners = $derived(m["외국인보유"] ?? m["foreignOwnership"] ?? null);

	function toNum(v) {
		if (typeof v === "number") return v;
		if (typeof v === "string") {
			const n = parseFloat(v.replace(/[,\s]/g, ""));
			return Number.isFinite(n) ? n : null;
		}
		return null;
	}
</script>

<div class="flex flex-col gap-4">
	{#if loading}
		<div class="grid grid-cols-4 gap-3">
			{#each [1, 2, 3, 4] as _}
				<div class="ed-card">
					<div class="editorial-skeleton h-3 w-16 mb-2"></div>
					<div class="editorial-skeleton h-8 w-32"></div>
				</div>
			{/each}
		</div>
	{:else}
		<div class="grid grid-cols-4 gap-3">
			<KpiTile label="회사" value={dash.stockCode} valueFormat={(v) => v} />
			<KpiTile label="시가총액" value={toNum(marketCap)} unit="KRW" valueFormat={fmtKrw} />
			<KpiTile label="현재가" value={toNum(price)} unit="" valueFormat={(v) => isFiniteNum(v) ? v.toLocaleString() + "원" : "—"} />
			<KpiTile label="거래량" value={toNum(volume)} unit="" valueFormat={(v) => isFiniteNum(v) ? v.toLocaleString() : "—"} />
		</div>
	{/if}

	{#if error}
		<div class="ed-card" style="border-color: var(--ed-down);">
			<div class="ed-eyebrow mb-1" style="color: var(--ed-down);">데이터 로드 실패</div>
			<div class="text-[11px]" style="color: var(--ed-text-2);">{error.message}</div>
		</div>
	{/if}

	<!-- Workforce -->
	{#if workforce.rows?.length > 0}
		<div class="ed-card">
			<div class="ed-eyebrow mb-3">임직원 통계</div>
			<div class="overflow-x-auto">
				<table class="w-full text-[12px]" style="font-family: var(--font-num);">
					<thead><tr style="border-bottom: 1px solid var(--ed-line);">
						{#each workforce.columns as col}
							<th class="text-left p-1.5" style="color: var(--ed-text-3); font-weight: 600;">{col}</th>
						{/each}
					</tr></thead>
					<tbody>
						{#each workforce.rows as r}
							<tr style="border-bottom: 1px solid var(--ed-line);">
								{#each workforce.columns as col}
									<td class="p-1.5" style="color: var(--ed-text-2);">{r[col] ?? "—"}</td>
								{/each}
							</tr>
						{/each}
					</tbody>
				</table>
			</div>
		</div>
	{/if}

	<!-- Market data preview (raw) -->
	{#if !loading && market.rows.length > 0}
		<div class="ed-card">
			<div class="ed-eyebrow mb-3">시장 데이터</div>
			<div class="grid grid-cols-2 md:grid-cols-4 gap-2">
				{#each Object.entries(market.rows[0]) as [k, v]}
					<div class="rounded border p-2.5" style="border-color: var(--ed-line); background: var(--ed-surface-2);">
						<div class="text-[10px] uppercase tracking-wide truncate" style="color: var(--ed-text-3);">{k}</div>
						<div class="ed-num text-[13px] truncate" style="color: var(--ed-text);">{v ?? "—"}</div>
					</div>
				{/each}
			</div>
		</div>
	{/if}
</div>
