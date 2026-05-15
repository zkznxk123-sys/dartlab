<!--
	Company > Filings — Editorial 톤. DART 공시 timeline + 정기/수시 필터.
-->
<script>
	import { onMount, untrack } from "svelte";
	import { ExternalLink } from "lucide-svelte";
	import { getDashboardStore } from "$lib/stores/dashboardStore.svelte.js";
	import { loadFilings } from "$lib/dashboard/data/loaders.js";

	const dash = getDashboardStore();

	let loading = $state(true);
	let rows = $state([]);
	let rowCount = $state(0);
	let error = $state(null);
	let filter = $state("all");

	const REGULAR_PATTERNS = ["사업보고서", "분기보고서", "반기보고서"];

	function classify(t) {
		if (!t) return "irregular";
		return REGULAR_PATTERNS.some((p) => t.includes(p)) ? "regular" : "irregular";
	}

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
		untrack(() => fetchAll());
	});

	onMount(() => fetchAll());

	const counts = $derived({
		all: rows.length,
		regular: rows.filter((r) => classify(r.reportType) === "regular").length,
		irregular: rows.filter((r) => classify(r.reportType) === "irregular").length,
	});

	const filtered = $derived(
		filter === "all" ? rows : rows.filter((r) => classify(r.reportType) === filter)
	);
</script>

<div class="flex flex-col gap-4">
	{#if error}
		<div class="ed-card" style="border-color: var(--ed-down);">
			<div class="ed-eyebrow mb-1" style="color: var(--ed-down);">공시 로드 실패</div>
			<div class="text-[12px]" style="color: var(--ed-text-2);">{error.message}</div>
		</div>
	{/if}

	<div class="ed-card">
		<div class="flex items-start justify-between gap-3 mb-3">
			<div>
				<div class="ed-eyebrow mb-1">DART Filings</div>
				<div class="text-[11px]" style="color: var(--ed-text-2);">
					최근 {rowCount} 건 중 {rows.length} 건 표시 · 정기 {counts.regular} · 수시 {counts.irregular}
				</div>
			</div>
			<div class="inline-flex rounded border text-[11px]" style="border-color: var(--ed-line);">
				{#each [["all", "전체"], ["regular", "정기"], ["irregular", "수시"]] as [key, label]}
					<button
						type="button"
						class="px-2.5 py-1 transition-colors first:rounded-l last:rounded-r"
						style="background: {filter === key ? 'color-mix(in srgb, var(--ed-brand) 10%, transparent)' : 'transparent'}; color: {filter === key ? 'var(--ed-text)' : 'var(--ed-text-3)'};"
						onclick={() => (filter = key)}>
						{label} <span class="ed-num ml-1" style="color: var(--ed-text-3);">{counts[key]}</span>
					</button>
				{/each}
			</div>
		</div>

		{#if loading}
			<div class="space-y-2">
				{#each Array(6) as _}
					<div class="editorial-skeleton h-8 w-full"></div>
				{/each}
			</div>
		{:else if filtered.length === 0}
			<div class="py-8 text-center text-[12px]" style="color: var(--ed-text-3);">표시할 공시가 없습니다</div>
		{:else}
			<div class="overflow-x-auto">
				<table class="w-full text-[12px]">
					<thead>
						<tr style="border-bottom: 1px solid var(--ed-line);">
							<th class="text-left p-1.5 w-16 text-[10px] uppercase tracking-wide" style="color: var(--ed-text-3);">연도</th>
							<th class="text-left p-1.5 w-28 text-[10px] uppercase tracking-wide" style="color: var(--ed-text-3);">접수일</th>
							<th class="text-left p-1.5 text-[10px] uppercase tracking-wide" style="color: var(--ed-text-3);">보고서</th>
							<th class="text-right p-1.5 w-32 text-[10px] uppercase tracking-wide" style="color: var(--ed-text-3);">접수번호</th>
							<th class="p-1.5 w-10"></th>
						</tr>
					</thead>
					<tbody>
						{#each filtered as r}
							{@const type = classify(r.reportType)}
							<tr style="border-bottom: 1px solid var(--ed-line);">
								<td class="p-1.5 ed-num" style="color: var(--ed-text-3);">{r.year ?? "—"}</td>
								<td class="p-1.5 ed-num" style="color: var(--ed-text-2);">{r.rceptDate ?? "—"}</td>
								<td class="p-1.5">
									<div class="flex items-center gap-2">
										<span class="editorial-chip text-[9px] uppercase tracking-wide px-1.5 py-0.5 rounded"
											style="border: 1px solid {type === 'regular' ? 'var(--ed-brand)' : 'var(--ed-line)'}; color: {type === 'regular' ? 'var(--ed-brand)' : 'var(--ed-text-3)'}; background: {type === 'regular' ? 'color-mix(in srgb, var(--ed-brand) 6%, transparent)' : 'transparent'};">
											{type === 'regular' ? '정기' : '수시'}
										</span>
										<span class="truncate" style="color: var(--ed-text);">{r.reportType ?? "—"}</span>
									</div>
								</td>
								<td class="p-1.5 ed-num text-right text-[11px]" style="color: var(--ed-text-3);">{r.rceptNo ?? "—"}</td>
								<td class="p-1.5 text-right">
									{#if r.dartUrl}
										<a href={r.dartUrl} target="_blank" rel="noopener noreferrer"
											class="inline-flex items-center justify-center p-1 rounded transition-colors"
											style="color: var(--ed-text-3);"
											aria-label="DART 원문">
											<ExternalLink size={12} />
										</a>
									{/if}
								</td>
							</tr>
						{/each}
					</tbody>
				</table>
			</div>
		{/if}
	</div>
</div>
