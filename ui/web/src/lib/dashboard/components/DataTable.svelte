<script>
	import * as Card from "$lib/ui/card";
	import * as Table from "$lib/ui/table";

	let { title = "", subtitle = "", payload = null, loading = false, error = null } = $props();

	function fmt(v, unit) {
		if (v == null || Number.isNaN(v)) return "—";
		const abs = Math.abs(v);
		if (unit === "%") return v.toFixed(2) + "%";
		if (abs >= 1e12) return (v / 1e12).toFixed(2) + "조";
		if (abs >= 1e8) return (v / 1e8).toFixed(0) + "억";
		if (abs >= 1e4) return (v / 1e4).toFixed(0) + "만";
		return Math.round(v).toLocaleString();
	}

	const periods = $derived(payload?.data?.periods || []);
	const rows = $derived(payload?.data?.rows || []);
</script>

<Card.Root class="overflow-hidden">
	<Card.Header class="pb-2">
		<Card.Title class="text-sm font-semibold tracking-tight">{title || payload?.chartSpec?.title || ""}</Card.Title>
		{#if subtitle}
			<Card.Description class="text-xs">{subtitle}</Card.Description>
		{/if}
	</Card.Header>
	<Card.Content class="pt-1 overflow-x-auto">
		{#if loading}
			<div class="w-full h-40 animate-pulse rounded-md bg-muted"></div>
		{:else if error}
			<div class="text-xs text-destructive p-4">{error}</div>
		{:else if !rows.length}
			<div class="text-xs text-muted-foreground p-4">데이터 없음</div>
		{:else}
			<Table.Root>
				<Table.Header>
					<Table.Row>
						<Table.Head>항목</Table.Head>
						{#each periods as p}
							<Table.Head class="text-right">{p}</Table.Head>
						{/each}
					</Table.Row>
				</Table.Header>
				<Table.Body>
					{#each rows as r}
						<Table.Row>
							<Table.Cell>{r.label}</Table.Cell>
							{#each r.values as v}
								<Table.Cell class="text-right tabular-nums {typeof v === 'number' && v < 0 ? 'text-destructive' : ''}">
									{fmt(v, r.unit)}
								</Table.Cell>
							{/each}
						</Table.Row>
					{/each}
				</Table.Body>
			</Table.Root>
		{/if}
	</Card.Content>
</Card.Root>
