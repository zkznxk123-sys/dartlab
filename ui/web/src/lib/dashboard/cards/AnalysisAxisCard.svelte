<!--
	AnalysisAxisCard — Company.analysis(axis) 결과의 generic 렌더러.
	응답 shape: { metricKey: { history: [...period objects...], ... }, ... }
	metricKey 하나당 카드 1 개. history 가 array of period objects 면 시계열 표.
-->
<script>
	import * as Card from "$lib/ui/card";
	import * as Table from "$lib/ui/table";
	import { Skeleton } from "$lib/ui/skeleton";
	import { cn } from "$lib/utils.js";

	let { payload = null, loading = false } = $props();

	function isHistoryShape(v) {
		return v && typeof v === "object" && Array.isArray(v.history);
	}

	function collectColumns(rows) {
		const seen = new Set();
		for (const r of rows) {
			if (r && typeof r === "object") {
				for (const k of Object.keys(r)) seen.add(k);
			}
		}
		return [...seen];
	}

	function formatCell(v) {
		if (v == null) return "—";
		if (typeof v === "number") {
			if (!Number.isFinite(v)) return "—";
			if (Math.abs(v) >= 1e9) return (v / 1e9).toFixed(2) + "B";
			if (Math.abs(v) >= 1e6) return (v / 1e6).toFixed(2) + "M";
			if (Math.abs(v) >= 1e3) return v.toLocaleString();
			if (Number.isInteger(v)) return v.toString();
			return v.toFixed(2);
		}
		return String(v);
	}

	// payload entries 정렬 — history 있는 metric 먼저
	const entries = $derived(
		payload && typeof payload === "object"
			? Object.entries(payload).sort(([, a], [, b]) => {
					const aH = isHistoryShape(a) ? 0 : 1;
					const bH = isHistoryShape(b) ? 0 : 1;
					return aH - bH;
				})
			: []
	);
</script>

{#if loading}
	<Card.Root>
		<Card.Header>
			<Skeleton class="h-5 w-32" />
		</Card.Header>
		<Card.Content>
			<Skeleton class="h-40 w-full" />
		</Card.Content>
	</Card.Root>
{:else if entries.length === 0}
	<Card.Root class="border-dashed">
		<Card.Content>
			<div class="py-6 text-center text-[12px] text-muted-foreground">분석 결과 없음</div>
		</Card.Content>
	</Card.Root>
{:else}
	<div class="grid grid-cols-1 gap-4">
		{#each entries as [metricKey, value]}
			<Card.Root>
				<Card.Header>
					<Card.Title class="text-[14px]">{metricKey}</Card.Title>
				</Card.Header>
				<Card.Content>
					{#if isHistoryShape(value)}
						{@const cols = collectColumns(value.history)}
						<Table.Root>
							<Table.Header>
								<Table.Row>
									{#each cols as col}
										<Table.Head class={cn("text-[10px] uppercase tracking-wide", col === "period" && "sticky left-0 bg-card")}>{col}</Table.Head>
									{/each}
								</Table.Row>
							</Table.Header>
							<Table.Body>
								{#each value.history as r}
									<Table.Row>
										{#each cols as col}
											<Table.Cell class={cn("text-[12px] font-mono tabular-nums", col === "period" && "sticky left-0 bg-card font-medium text-foreground")}>
												{formatCell(r[col])}
											</Table.Cell>
										{/each}
									</Table.Row>
								{/each}
							</Table.Body>
						</Table.Root>
						{#if value.summary}
							<div class="mt-3 text-[11px] text-muted-foreground border-t border-border pt-2">
								{typeof value.summary === "string" ? value.summary : JSON.stringify(value.summary)}
							</div>
						{/if}
					{:else if typeof value === "object"}
						<div class="grid grid-cols-2 md:grid-cols-4 gap-2">
							{#each Object.entries(value) as [k, v]}
								<div class="rounded-md border border-border bg-card/40 p-2">
									<div class="text-[10px] text-muted-foreground uppercase tracking-wide truncate">{k}</div>
									<div class="text-[13px] font-mono tabular-nums truncate">{formatCell(v)}</div>
								</div>
							{/each}
						</div>
					{:else}
						<div class="text-[13px] font-mono tabular-nums">{formatCell(value)}</div>
					{/if}
				</Card.Content>
			</Card.Root>
		{/each}
	</div>
{/if}
