<script lang="ts">
	// 회사 간 비교 매트릭스 — 좌측 sticky 라벨 거터 + N사 열, 한 시점(point-in-time).
	// 행 = 정렬된 공시 항목(disclosureKey/narrative), 셀 = 회사별 본문. 한쪽만=honest-gap(⌀).
	// landing 디자인(다크 네이비 + 오렌지). 단일 PanelMatrix 와 분리(섞임 0).
	import CellContent from './CellContent.svelte';
	import type { AlignedRow } from '$lib/viewer/align';

	let {
		rows,
		companies,
		period
	}: {
		rows: AlignedRow[];
		companies: { code: string; corpName: string }[];
		period: string;
	} = $props();

	// 거터(라벨) + 회사 열. 회사당 minmax(300px,1fr) — N≥5 가로 스크롤(.matrix-scroll overflow:auto).
	const template = $derived(`200px repeat(${companies.length}, minmax(300px, 1fr))`);
</script>

{#if !period}
	<div class="empty">기간을 선택하세요.</div>
{:else if rows.length === 0}
	<div class="empty">선택한 절·시점에는 비교할 공시 항목이 없습니다.</div>
{:else}
	<div class="matrix-scroll">
		<div class="matrix" style="grid-template-columns: {template}">
			<!-- 헤더: 거터 + 회사명 -->
			<div class="cell head gutter-head">
				<span class="period">{period}</span>
			</div>
			{#each companies as c (c.code)}
				<div class="cell head company-head">
					<span class="corp">{c.corpName || c.code}</span>
					<span class="code">{c.code}</span>
				</div>
			{/each}

			<!-- 본문: 행마다 거터 라벨 + 회사 셀 -->
			{#each rows as r (r.alignKey)}
				<div class="cell gutter" title={r.label}>
					<span class="label">{r.label}</span>
					{#if r.scope}<span class="scope" class:consol={r.scope === 'consolidated'}>{r.scope === 'consolidated' ? '연결' : '별도'}</span>{/if}
				</div>
				{#each companies as c, ci (c.code)}
					<div class="cell body-cell" class:gap={r.cells[ci] == null}>
						{#if r.cells[ci] != null}
							<CellContent value={r.cells[ci] ?? ''} />
						{:else}
							<span class="gap-mark" title="이 회사엔 해당 공시 항목이 없습니다">⌀ 해당 공시 없음</span>
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
	.gutter,
	.gutter-head {
		position: sticky;
		left: 0;
		z-index: 10;
		background: #070b14;
		border-right: 1px solid #263145;
	}
	.gutter-head {
		z-index: 30;
	}
	.company-head {
		display: flex;
		flex-direction: column;
		gap: 2px;
	}
	.corp {
		font-size: 13px;
		font-weight: 700;
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
		font-family: monospace;
		font-size: 12px;
		font-weight: 700;
		color: #fb923c;
	}
	.gutter {
		display: flex;
		flex-direction: column;
		gap: 3px;
		max-height: 480px;
		overflow: hidden;
	}
	.label {
		font-size: 12px;
		font-weight: 600;
		color: #cbd5e1;
		line-height: 1.35;
		word-break: break-word;
	}
	.scope {
		align-self: flex-start;
		padding: 0 5px;
		border-radius: 8px;
		font-size: 9px;
		font-weight: 700;
		background: rgba(148, 163, 184, 0.14);
		color: #94a3b8;
	}
	.scope.consol {
		background: rgba(251, 146, 60, 0.14);
		color: #fb923c;
	}
	.body-cell {
		color: #cbd5e1;
		max-height: 480px;
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
