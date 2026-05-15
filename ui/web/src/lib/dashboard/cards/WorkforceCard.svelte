<!--
	WorkforceCard — Company.workforce 의 임직원 데이터 카드.
	구조가 가변적 (성별/근속/연봉 등 column) — generic key/value 표시.
-->
<script>
	import { Users } from "lucide-svelte";
	import * as Card from "$lib/ui/card";
	import * as Table from "$lib/ui/table";
	import { Skeleton } from "$lib/ui/skeleton";

	let { rows = [], columns = [], loading = false } = $props();
</script>

<Card.Root>
	<Card.Header>
		<Card.Title class="flex items-center gap-2 text-[14px]">
			<Users size={15} />
			임직원 현황
		</Card.Title>
		<Card.Description class="text-[11px]">성별 · 근속 · 평균 보수</Card.Description>
	</Card.Header>
	<Card.Content>
		{#if loading}
			<Skeleton class="h-36 w-full" />
		{:else if rows.length === 0}
			<div class="py-6 text-center text-[12px] text-muted-foreground">데이터 없음</div>
		{:else}
			<Table.Root>
				<Table.Header>
					<Table.Row>
						{#each columns as col}
							<Table.Head class="text-[10px] uppercase tracking-wide">{col}</Table.Head>
						{/each}
					</Table.Row>
				</Table.Header>
				<Table.Body>
					{#each rows as r}
						<Table.Row>
							{#each columns as col}
								<Table.Cell class="text-[12px] font-mono tabular-nums">
									{#if typeof r[col] === "number"}
										{r[col].toLocaleString()}
									{:else}
										{r[col] ?? "—"}
									{/if}
								</Table.Cell>
							{/each}
						</Table.Row>
					{/each}
				</Table.Body>
			</Table.Root>
		{/if}
	</Card.Content>
</Card.Root>
