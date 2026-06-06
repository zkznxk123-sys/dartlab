<script lang="ts">
	// 수평화 매트릭스 — 행=panel 항목, 열=period. landing 디자인 언어(다크 네이비 + 오렌지).
	import CellContent from './CellContent.svelte';
	import { hasVisibleContent } from '$lib/viewer/diff';
	import type { PanelRow } from '$lib/viewer/types';

	let {
		rows,
		periods,
		dartUrlByPeriod,
		glow = null,
		highlight = null
	}: {
		rows: PanelRow[];
		periods: string[];
		dartUrlByPeriod: Record<string, string | null>;
		glow?: { rowIndex: number; period: string } | null;
		highlight?: { rowIndex: number; period: string; terms: string[] } | null;
	} = $props();

	// 섹션 내 build-order 인덱스 보존 — 행 식별(disclosureKey/NARR)은 leafSeq 미포함이라 EDGAR 동명 narrative
	// 행이 충돌(each_key_duplicate). 별개 행이므로 둘 다 표시하되 DOM 키는 안정·유일한 원본 인덱스로.
	const visible = $derived(rows.map((r, i) => ({ r, i })).filter(({ r }) => hasVisibleContent(r, periods)));
	// 항목 라벨 열 없음 — 셀 본문(표 제목 내장)이 자기 식별. 격자는 기간 열만.
	const template = $derived(`repeat(${periods.length}, minmax(260px, 1fr))`);

	// 검색 점프 셀 글로우 → 화면 중앙으로 스크롤(렌더 후).
	$effect(() => {
		const g = glow;
		if (!g) return;
		queueMicrotask(() => {
			const el = document.querySelector(`[data-cell="${g.rowIndex}|${CSS.escape(g.period)}"]`);
			el?.scrollIntoView({ block: 'center', inline: 'center', behavior: 'smooth' });
		});
	});
</script>

{#if periods.length === 0}
	<div class="empty">기간을 선택하세요.</div>
{:else if visible.length === 0}
	<div class="empty">선택한 기간에는 이 절의 본문이 없습니다.</div>
{:else}
	<div class="matrix-scroll">
		<div class="matrix" style="grid-template-columns: {template}">
			<!-- 헤더 -->
			{#each periods as p (p)}
				<div class="cell head period-head">
					<span class="period">{p}</span>
					{#if dartUrlByPeriod[p]}
						<a class="src-link" href={dartUrlByPeriod[p]} target="_blank" rel="noreferrer noopener" title={`${p} 시점 원본 공시`}>
							원본 ↗
						</a>
					{/if}
				</div>
			{/each}

			<!-- 본문 -->
			{#each visible as { r, i } (i)}
				{#each periods as p (p)}
					<div class="cell body-cell" class:glow={glow && glow.rowIndex === i && glow.period === p} data-cell={`${i}|${p}`}>
						<CellContent value={r.cells?.[p] ?? ''} highlightTerms={highlight && highlight.rowIndex === i && highlight.period === p ? highlight.terms : []} />
					</div>
				{/each}
			{/each}
		</div>
	</div>
{/if}

<style>
	.empty {
		padding: 24px;
		text-align: center;
		font-size: 12px;
		color: #64748b;
	}
	.matrix-scroll {
		height: 100%;
		overflow: auto;
	}
	.matrix {
		display: grid;
		align-items: stretch;
	}
	.cell {
		border-bottom: 1px solid #1e2433;
		padding: 8px 10px;
		min-width: 0;
	}
	.head {
		position: sticky;
		top: 0;
		z-index: 20;
		background: #0a0e18;
		border-bottom: 1px solid #263145;
	}
	.period-head {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 8px;
	}
	.period {
		font-family: monospace;
		font-size: 12px;
		font-weight: 700;
		color: #f1f5f9;
	}
	.src-link {
		flex-shrink: 0;
		display: inline-flex;
		align-items: center;
		gap: 4px;
		padding: 2px 7px;
		border: 1px solid #263145;
		border-radius: 4px;
		font-size: 10px;
		color: #94a3b8;
		text-decoration: none;
		white-space: nowrap;
	}
	.src-link:hover {
		border-color: rgba(251, 146, 60, 0.6);
		color: #fb923c;
	}
	.body-cell {
		color: #cbd5e1;
	}
	.body-cell.glow {
		animation: cellglow 2.2s ease-out;
	}
	@keyframes cellglow {
		0% {
			box-shadow: inset 0 0 0 2px #fb923c;
			background: rgba(251, 146, 60, 0.18);
		}
		100% {
			box-shadow: inset 0 0 0 0 transparent;
			background: transparent;
		}
	}
</style>
