<!--
	Company > Profile — 회사 메타 + market summary KPI strip.
-->
<script>
	import { onMount } from "svelte";
	import { getDashboardStore } from "$lib/stores/dashboardStore.svelte.js";
	import { loadMarket, loadWorkforce } from "$lib/dashboard/data/loaders.js";
	import KpiStrip from "$lib/dashboard/cards/KpiStrip.svelte";
	import WorkforceCard from "$lib/dashboard/cards/WorkforceCard.svelte";
	import * as Card from "$lib/ui/card";
	import { Skeleton } from "$lib/ui/skeleton";

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
		// stockCode change → refetch
		dash.stockCode;
		fetchAll();
	});

	onMount(() => {
		fetchAll();
	});

	// KPI strip — 시총 / 현재가 / 외국인 / 직원수 (market response 의 columns 가변)
	const kpis = $derived.by(() => {
		const m = market.rows[0] || {};
		return [
			{ label: "회사", value: dash.stockCode },
			{ label: "시가총액", value: m["시가총액"] || m["marketCap"] || "—", sub: "원" },
			{ label: "현재가", value: m["종가"] || m["price"] || "—", sub: "원" },
			{ label: "거래량", value: m["거래량"] || m["volume"] || "—" },
		];
	});
</script>

<div class="flex flex-col gap-4">
	<KpiStrip items={kpis} {loading} />

	{#if error}
		<Card.Root class="border-destructive/30">
			<Card.Header>
				<Card.Title class="text-[14px] text-destructive">데이터 로드 실패</Card.Title>
				<Card.Description class="text-[11px]">{error.message}</Card.Description>
			</Card.Header>
		</Card.Root>
	{/if}

	<WorkforceCard rows={workforce.rows} columns={workforce.columns} {loading} />

	<Card.Root>
		<Card.Header>
			<Card.Title class="text-[14px]">시장 데이터</Card.Title>
			<Card.Description class="text-[11px]">Company.market preview</Card.Description>
		</Card.Header>
		<Card.Content>
			{#if loading}
				<Skeleton class="h-24 w-full" />
			{:else if market.rows.length > 0}
				<div class="grid grid-cols-2 md:grid-cols-4 gap-2">
					{#each Object.entries(market.rows[0]) as [k, v]}
						<div class="rounded-md border border-border bg-card/40 p-2">
							<div class="text-[10px] text-muted-foreground uppercase tracking-wide truncate">{k}</div>
							<div class="text-[13px] font-mono tabular-nums truncate">{v ?? "—"}</div>
						</div>
					{/each}
				</div>
			{:else}
				<pre class="text-[11px] text-muted-foreground whitespace-pre-wrap font-mono">{market.preview || "데이터 없음"}</pre>
			{/if}
		</Card.Content>
	</Card.Root>
</div>
