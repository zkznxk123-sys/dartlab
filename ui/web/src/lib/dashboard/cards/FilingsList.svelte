<!--
	FilingsList — Company.filings 표 (year/rceptDate/rceptNo/reportType/dartUrl).
	정기/수시 필터 + DART 원문 링크.
-->
<script>
	import { ExternalLink, FileText } from "lucide-svelte";
	import * as Card from "$lib/ui/card";
	import * as Table from "$lib/ui/table";
	import { Skeleton } from "$lib/ui/skeleton";
	import { Badge } from "$lib/ui/badge";
	import { cn } from "$lib/utils.js";

	let { rows = [], rowCount = 0, loading = false } = $props();

	let filter = $state("all"); // "all" | "regular" | "irregular"

	// 정기 보고서 키워드: 사업보고서, 분기보고서, 반기보고서
	const REGULAR_PATTERNS = ["사업보고서", "분기보고서", "반기보고서"];

	function classifyReport(reportType) {
		if (!reportType) return "irregular";
		return REGULAR_PATTERNS.some((p) => reportType.includes(p)) ? "regular" : "irregular";
	}

	const filtered = $derived(
		filter === "all"
			? rows
			: rows.filter((r) => classifyReport(r.reportType) === filter)
	);

	const counts = $derived({
		all: rows.length,
		regular: rows.filter((r) => classifyReport(r.reportType) === "regular").length,
		irregular: rows.filter((r) => classifyReport(r.reportType) === "irregular").length,
	});
</script>

<Card.Root>
	<Card.Header>
		<div class="flex items-center justify-between gap-3">
			<div>
				<Card.Title class="flex items-center gap-2 text-[14px]">
					<FileText size={15} />
					DART 공시
				</Card.Title>
				<Card.Description class="text-[11px]">
					최근 {rowCount} 건 중 {rows.length} 건 표시 · 정기 {counts.regular} · 수시 {counts.irregular}
				</Card.Description>
			</div>
			<div class="inline-flex rounded-md border border-border bg-card p-0.5 text-[11px]">
				{#each [["all", "전체"], ["regular", "정기"], ["irregular", "수시"]] as [key, label]}
					<button
						type="button"
						class={cn(
							"px-2.5 py-1 rounded transition-colors",
							filter === key
								? "bg-secondary text-foreground"
								: "text-muted-foreground hover:text-foreground"
						)}
						onclick={() => (filter = key)}
					>
						{label} <span class="ml-1 text-muted-foreground font-mono">{counts[key]}</span>
					</button>
				{/each}
			</div>
		</div>
	</Card.Header>
	<Card.Content>
		{#if loading}
			<div class="space-y-2">
				{#each Array(6) as _}
					<Skeleton class="h-9 w-full" />
				{/each}
			</div>
		{:else if filtered.length === 0}
			<div class="py-8 text-center text-[12px] text-muted-foreground">표시할 공시가 없습니다</div>
		{:else}
			<Table.Root>
				<Table.Header>
					<Table.Row>
						<Table.Head class="w-16">연도</Table.Head>
						<Table.Head class="w-28">접수일</Table.Head>
						<Table.Head>보고서</Table.Head>
						<Table.Head class="w-28 text-right">접수번호</Table.Head>
						<Table.Head class="w-12"></Table.Head>
					</Table.Row>
				</Table.Header>
				<Table.Body>
					{#each filtered as r}
						{@const type = classifyReport(r.reportType)}
						<Table.Row>
							<Table.Cell class="text-[12px] font-mono text-muted-foreground">{r.year}</Table.Cell>
							<Table.Cell class="text-[12px] font-mono text-muted-foreground">{r.rceptDate}</Table.Cell>
							<Table.Cell class="text-[12px]">
								<div class="flex items-center gap-2">
									<Badge variant={type === "regular" ? "secondary" : "outline"} class="text-[9px]">
										{type === "regular" ? "정기" : "수시"}
									</Badge>
									<span class="truncate">{r.reportType}</span>
								</div>
							</Table.Cell>
							<Table.Cell class="text-[11px] font-mono text-muted-foreground text-right">{r.rceptNo}</Table.Cell>
							<Table.Cell class="text-right">
								{#if r.dartUrl}
									<a
										href={r.dartUrl}
										target="_blank"
										rel="noopener noreferrer"
										class="inline-flex items-center justify-center p-1 rounded text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
										aria-label="DART 원문"
									>
										<ExternalLink size={12} />
									</a>
								{/if}
							</Table.Cell>
						</Table.Row>
					{/each}
				</Table.Body>
			</Table.Root>
		{/if}
	</Card.Content>
</Card.Root>
