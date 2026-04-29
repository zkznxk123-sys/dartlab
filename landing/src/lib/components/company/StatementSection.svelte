<script lang="ts">
	import type {
		FinancialTableGroup,
		FinancialTableRow
	} from '$lib/browser/companyDashboardModel';
	import type { StatementDashboard } from '$lib/browser/companyLive';
	import FinancialTable from './FinancialTable.svelte';

	let {
		dashboard,
		onSelect
	}: {
		dashboard: StatementDashboard;
		onSelect?: (row: FinancialTableRow, group: FinancialTableGroup) => void;
	} = $props();

	let groups = $derived<FinancialTableGroup[]>(
		dashboard.groups.reduce<FinancialTableGroup[]>((acc, group) => {
			if (!group.rows.length) return acc;
			const rawRows: FinancialTableRow[] = group.rows.map((row) => ({
				key: row.key,
				label: row.label,
				unit: row.unit,
				values: row.values,
				yoy: row.yoy,
				source: row.source,
				raw: row
			}));
			const rows = rawRows.filter(hasDisplayValue);
			if (!rows.length) return acc;
			acc.push({
				key: `${dashboard.topic}-${group.key}`,
				label: `${dashboard.topic} · ${group.label}`,
				periods: dashboard.periods,
				statement: dashboard.topic as FinancialTableGroup['statement'],
				rows,
				coverageNotes:
					rows.length < rawRows.length
						? [{ label: `빈 행 ${rawRows.length - rows.length}개 숨김`, tone: 'neutral' as const }]
						: undefined
			});
			return acc;
		}, [])
	);

	function hasDisplayValue(row: FinancialTableRow): boolean {
		const nums = row.values.map(numberOrNull).filter((value): value is number => value != null && Number.isFinite(value));
		if (nums.length) return !nums.every((value) => Math.abs(value) < 1e-9);
		return row.values.some(isMeaningfulTextValue);
	}

	function numberOrNull(value: unknown): number | null {
		if (typeof value === 'number') return Number.isFinite(value) ? value : null;
		if (typeof value !== 'string') return null;
		const cleaned = value.replace(/[,％%]/g, '').trim();
		if (!cleaned || cleaned === '—' || cleaned === '-' || cleaned === '--') return null;
		const num = Number(cleaned);
		return Number.isFinite(num) ? num : null;
	}

	function isMeaningfulTextValue(value: unknown): boolean {
		if (typeof value !== 'string') return false;
		const text = value.trim();
		return Boolean(text && text !== '—' && text !== '-' && text !== '--' && text.toLowerCase() !== 'nan');
	}
</script>

<section class="statement" id={dashboard.topic.toLowerCase()} data-section>
	<header>
		<div>
			<div class="eyebrow">{dashboard.topic}</div>
			<h2>{dashboard.title}</h2>
			<p>{dashboard.subtitle}</p>
		</div>
		<div class="source">
			<strong>{dashboard.quality.sourceLabel}</strong>
			<span>{dashboard.periods.at(-1) ?? 'period 대기'}</span>
		</div>
	</header>

	{#if groups.length}
		<FinancialTable {groups} onSelect={onSelect} />
	{:else}
		<div class="empty-table">표시할 계정값 없음</div>
	{/if}

	{#if dashboard.quality.missingAccounts.length}
		<div class="missing">누락 계정: {dashboard.quality.missingAccounts.join(', ')}</div>
	{/if}
</section>

<style>
	.statement {
		display: grid;
		gap: 12px;
		border: 1px solid #1e2433;
		border-radius: 8px;
		background: rgba(8, 13, 23, 0.96);
		padding: 16px;
	}
	header {
		display: grid;
		grid-template-columns: minmax(0, 1fr) auto;
		gap: 16px;
		align-items: flex-start;
	}
	.eyebrow {
		color: #fb923c;
		font-size: 11px;
		font-weight: 900;
		letter-spacing: 0;
	}
	h2,
	p {
		margin: 0;
	}
	h2 {
		margin-top: 5px;
		color: #f8fafc;
		font-size: 23px;
		font-weight: 820;
		letter-spacing: 0;
	}
	p {
		margin-top: 6px;
		color: #94a3b8;
		font-size: 13px;
		line-height: 1.45;
	}
	.source {
		display: grid;
		gap: 3px;
		min-width: 122px;
		border: 1px solid #263145;
		border-radius: 6px;
		background: #070c15;
		padding: 8px 10px;
		text-align: right;
	}
	.source strong {
		color: #f8fafc;
		font-size: 12px;
	}
	.source span,
	.missing {
		color: #94a3b8;
		font-size: 11px;
	}
	.empty-table {
		border: 1px dashed #263145;
		border-radius: 7px;
		background: #070c15;
		color: #94a3b8;
		font-size: 12px;
		padding: 18px;
	}
	@media (max-width: 760px) {
		header {
			grid-template-columns: 1fr;
		}
		.source {
			text-align: left;
		}
	}
</style>
