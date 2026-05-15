<!--
	Company > Filings — DART 공시 표 + 정기/수시 필터.
-->
<script>
	import { onMount } from "svelte";
	import { getDashboardStore } from "$lib/stores/dashboardStore.svelte.js";
	import { loadFilings } from "$lib/dashboard/data/loaders.js";
	import FilingsList from "$lib/dashboard/cards/FilingsList.svelte";
	import * as Card from "$lib/ui/card";

	const dash = getDashboardStore();

	let loading = $state(true);
	let rows = $state([]);
	let rowCount = $state(0);
	let error = $state(null);

	async function fetchAll() {
		loading = true;
		error = null;
		const result = await loadFilings(dash.stockCode);
		if (result.ok) {
			rows = result.data.rows;
			rowCount = result.data.rowCount;
		} else {
			error = result.error;
			rows = [];
			rowCount = 0;
		}
		loading = false;
	}

	$effect(() => {
		dash.stockCode;
		fetchAll();
	});

	onMount(() => {
		fetchAll();
	});
</script>

<div class="flex flex-col gap-4">
	{#if error}
		<Card.Root class="border-destructive/30">
			<Card.Header>
				<Card.Title class="text-[14px] text-destructive">공시 로드 실패</Card.Title>
				<Card.Description class="text-[11px]">{error.message}</Card.Description>
			</Card.Header>
		</Card.Root>
	{/if}

	<FilingsList {rows} {rowCount} {loading} />
</div>
