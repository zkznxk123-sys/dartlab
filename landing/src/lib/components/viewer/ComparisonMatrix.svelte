<script lang="ts">
	// 회사 간 비교 매트릭스 — 단일 PanelMatrix 와 같은 골격, 단 열 = period 대신 **회사**.
	// 적응: 재무 섹션이면 셀(항목) 단위 숫자행(financeRows), 그 외는 통짜 본문 셀(rows). 둘 다 회사 열만.
	// 한쪽만 = honest-gap(⌀). 라벨 거터 없음(단일 뷰어와 동일 — 셀이 자기 식별).
	import CellContent from './CellContent.svelte';
	import type { AlignedRow, FinanceRow, UnitInfo } from '$lib/viewer/compare';

	let {
		rows,
		financeRows = null,
		financeUnits = null,
		companies,
		period
	}: {
		rows: AlignedRow[];
		financeRows?: FinanceRow[] | null;
		financeUnits?: UnitInfo[] | null;
		companies: { code: string; corpName: string }[];
		period: string;
	} = $props();

	// 열 = 회사. 회사당 minmax(280px,1fr) — N≥5 가로 스크롤(.matrix-scroll overflow:auto).
	const template = $derived(`repeat(${companies.length}, minmax(280px, 1fr))`);

	// 원 → 읽기 쉬운 조/억.
	function fmtWon(v: number): string {
		const a = Math.abs(v);
		if (a >= 1e12) return `${(v / 1e12).toFixed(1)}조`;
		if (a >= 1e8) return `${Math.round(v / 1e8).toLocaleString()}억`;
		return v.toLocaleString();
	}
	// 같은 행 N값의 max 대비 상대 폭(%).
	function barWidth(values: (number | null)[], v: number | null): number {
		if (v == null) return 0;
		const max = Math.max(...values.filter((x): x is number => x != null).map(Math.abs), 1);
		return Math.min(100, (Math.abs(v) / max) * 100);
	}
</script>

{#if !period}
	<div class="empty">기간을 선택하세요.</div>
{:else if financeRows}
	<!-- 재무 셀(항목) 단위 — 행=acode 항목, 셀=원 환산 숫자 (단위 착시 0) -->
	{#if financeRows.length === 0}
		<div class="empty">이 시점에는 비교할 재무 항목이 없습니다.</div>
	{:else}
		<div class="matrix-scroll">
			<div class="matrix" style="grid-template-columns: {template}">
				{#each companies as c, ci (c.code)}
					{@const unit = financeUnits?.[ci]}
					<div class="cell head company-head">
						<span class="corp">{c.corpName || c.code}</span>
						<span class="code">{c.code}</span>
						<span class="period">{period}</span>
						<span
							class="unit-badge"
							class:warn={unit?.confidence === 'magnitude'}
							title={unit?.confidence === 'magnitude'
								? '표머리 단위 캡션을 못 찾아 자릿수로 추정 — 천원↔백만원 불확실'
								: `원 환산 (소스 단위 ${unit?.label ?? '백만원'})`}
						>
							{unit?.label ?? '백만원'}{unit?.confidence === 'magnitude' ? '?' : ''}→원
						</span>
					</div>
				{/each}
				{#each financeRows as r (r.acode)}
					{#each companies as c, ci (c.code)}
						<div class="cell fin-cell" class:gap={r.values[ci] == null} class:d0={r.depth === 0} class:d2={r.depth >= 2}>
							{#if r.values[ci] != null}
								<span class="fin-label" title={r.acode}>{r.label}</span>
								<span class="fin-value" class:neg={(r.values[ci] ?? 0) < 0}>{fmtWon(r.values[ci] ?? 0)}</span>
								<span class="fin-bar" style="width: {barWidth(r.values, r.values[ci])}%" class:neg={(r.values[ci] ?? 0) < 0}></span>
							{:else}
								<span class="fin-label dim">{r.label}</span>
								<span class="gap-mark">⌀</span>
							{/if}
						</div>
					{/each}
				{/each}
			</div>
		</div>
	{/if}
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

			<!-- 본문: 정렬된 항목 행마다 회사별 셀 -->
			{#each rows as r (r.alignKey)}
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
	.unit-badge {
		border: 1px solid rgba(251, 146, 60, 0.3);
		border-radius: 4px;
		padding: 1px 5px;
		background: rgba(251, 146, 60, 0.08);
		font-size: 10px;
		font-weight: 700;
		color: #fdba74;
		white-space: nowrap;
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

	/* 재무 셀(항목) — 라벨 + 원환산 숫자 + 상대막대 */
	.fin-cell {
		position: relative;
		display: flex;
		flex-direction: column;
		gap: 2px;
		padding: 7px 12px 9px;
	}
	.fin-label {
		font-size: 11px;
		color: #94a3b8;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}
	.fin-label.dim {
		color: #475569;
	}
	.fin-value {
		font-family: monospace;
		font-size: 15px;
		font-weight: 700;
		color: #f1f5f9;
		text-align: right;
		font-variant-numeric: tabular-nums;
	}
	.fin-value.neg {
		color: #f87171;
	}
	.fin-bar {
		height: 3px;
		border-radius: 2px;
		background: rgba(251, 146, 60, 0.55);
		align-self: flex-end;
	}
	.fin-bar.neg {
		background: rgba(248, 113, 113, 0.55);
	}
	/* 위계(accountDepth) — 총계 굵게·구분선, 리프 들여쓰기·톤다운 (새 마크업 0, CSS만) */
	.fin-cell.d0 {
		border-top: 1px solid #263145;
	}
	.fin-cell.d0 .fin-label {
		color: #e2e8f0;
		font-weight: 700;
	}
	.fin-cell.d2 .fin-label {
		padding-left: 10px;
		color: #64748b;
	}
	.unit-badge.warn {
		border-color: rgba(251, 191, 36, 0.45);
		background: rgba(251, 191, 36, 0.1);
		color: #fbbf24;
	}
</style>
