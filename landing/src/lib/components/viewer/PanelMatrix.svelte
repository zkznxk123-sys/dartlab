<script lang="ts">
	// 수평화 매트릭스 — 행=panel 항목, 열=period. ui/web PanelMatrix 이식 (sticky 헤더/레일).
	import CellContent from './CellContent.svelte';
	import { rowKey, rowLabel, hasVisibleContent } from '$lib/viewer/diff';
	import type { PanelRow } from '$lib/viewer/types';

	let {
		rows,
		periods,
		dartUrlByPeriod
	}: { rows: PanelRow[]; periods: string[]; dartUrlByPeriod: Record<string, string | null> } = $props();

	const visible = $derived(rows.filter((r) => hasVisibleContent(r, periods)));
	const hasLabel = $derived(new Set(visible.map(rowLabel).filter(Boolean)).size >= 2);
	const template = $derived(
		`${hasLabel ? 'minmax(120px, 200px) ' : ''}repeat(${periods.length}, minmax(260px, 1fr))`
	);
</script>

{#if periods.length === 0}
	<div class="py-6 text-center text-xs text-muted-foreground">기간을 선택하세요.</div>
{:else if visible.length === 0}
	<div class="py-6 text-center text-xs text-muted-foreground">선택한 기간에는 이 절의 본문이 없습니다.</div>
{:else}
	<div class="h-full overflow-auto">
		<div class="grid items-stretch" style="grid-template-columns: {template}">
			<!-- 헤더 -->
			{#if hasLabel}
				<div class="sticky left-0 top-0 z-30 border-b border-r bg-background px-2 py-2 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
					항목
				</div>
			{/if}
			{#each periods as p (p)}
				<div class="sticky top-0 z-20 flex items-center justify-between gap-2 border-b bg-background px-2 py-2">
					<div class="font-mono text-xs font-semibold">{p}</div>
					{#if dartUrlByPeriod[p]}
						<a
							href={dartUrlByPeriod[p]}
							target="_blank"
							rel="noreferrer noopener"
							title={`${p} 시점 원본 공시`}
							class="inline-flex shrink-0 items-center gap-1 rounded border px-1.5 py-0.5 text-[10px] text-muted-foreground hover:bg-accent"
						>
							원본 ↗
						</a>
					{/if}
				</div>
			{/each}

			<!-- 본문 -->
			{#each visible as r (rowKey(r))}
				{#if hasLabel}
					<div class="sticky left-0 z-10 border-b border-r bg-card/70 px-2 py-2 text-[11px] font-medium backdrop-blur-sm" title={rowLabel(r)}>
						<div class="line-clamp-6 break-words">{rowLabel(r)}</div>
					</div>
				{/if}
				{#each periods as p (p)}
					<div class="min-w-0 border-b px-2 py-2">
						<CellContent value={r.cells?.[p] ?? ''} />
					</div>
				{/each}
			{/each}
		</div>
	</div>
{/if}
