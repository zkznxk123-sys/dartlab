<script lang="ts">
	// 회사 간 비교 매트릭스 — 단일 PanelMatrix 와 같은 골격, 단 열 = period 대신 **회사**.
	// 각 회사의 섹션/블록 콘텐츠를 자기 열에 통째로(셀 = 본문). 한쪽만 = honest-gap(⌀).
	// 라벨 거터 없음(단일 뷰어와 동일 — 셀이 자기 식별).
	import CellContent from './CellContent.svelte';
	import type { AlignedRow } from '$lib/viewer/compare';

	let {
		rows,
		companies,
		period
	}: {
		rows: AlignedRow[];
		companies: { code: string; corpName: string }[];
		period: string;
	} = $props();

	// 열 = 회사. 회사당 minmax(280px,1fr) — N≥5 가로 스크롤(.matrix-scroll overflow:auto).
	const template = $derived(`repeat(${companies.length}, minmax(280px, 1fr))`);
</script>

{#if !period}
	<div class="empty">기간을 선택하세요.</div>
{:else if rows.length === 0}
	<div class="empty">선택한 절·시점에는 비교할 공시 항목이 없습니다.</div>
{:else}
	<div class="matrix-scroll">
		<div class="matrix" style="grid-template-columns: {template}">
			<!-- 헤더: 회사명 + 시점 -->
			{#each companies as c (c.code)}
				<div class="cell head company-head">
					<span class="corp">{c.corpName || c.code}</span>
					<span class="code">{c.code}</span>
					<span class="period">{period}</span>
				</div>
			{/each}

			<!-- 본문: 각 회사 셀(섹션/블록 콘텐츠 통째) -->
			{#each rows as r (r.alignKey)}
				{#each companies as c, ci (c.code)}
					<div class="cell body-cell" class:gap={r.cells[ci] == null}>
						{#if r.cells[ci] != null}
							<CellContent value={r.cells[ci] ?? ''} />
						{:else}
							<span class="gap-mark" title="이 회사엔 해당 공시가 없습니다">⌀ 해당 공시 없음</span>
						{/if}
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
		border-right: 1px solid #141a26;
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
	.company-head {
		display: flex;
		align-items: baseline;
		gap: 8px;
	}
	.corp {
		font-size: 14px;
		font-weight: 800;
		color: #f1f5f9;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}
	.code {
		font-family: monospace;
		font-size: 10px;
		color: #64748b;
	}
	.period {
		margin-left: auto;
		font-family: monospace;
		font-size: 11px;
		font-weight: 700;
		color: #fb923c;
	}
	.body-cell {
		color: #cbd5e1;
		max-height: 520px;
		overflow: auto;
	}
	.body-cell.gap {
		background: repeating-linear-gradient(45deg, transparent, transparent 6px, rgba(100, 116, 139, 0.04) 6px, rgba(100, 116, 139, 0.04) 12px);
	}
	.gap-mark {
		font-size: 11px;
		color: #475569;
		font-style: italic;
	}
</style>
