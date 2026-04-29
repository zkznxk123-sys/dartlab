<script lang="ts">
	import {
		formatTableValue,
		type FinancialTableGroup,
		type FinancialTableRow
	} from '$lib/browser/companyDashboardModel';

	let {
		groups = [],
		onSelect
	}: {
		groups?: FinancialTableGroup[];
		onSelect?: (row: FinancialTableRow, group: FinancialTableGroup) => void;
	} = $props();

	function yoyText(value: number | null): string {
		if (value == null || !Number.isFinite(value)) return '—';
		return `${value > 0 ? '+' : ''}${value.toFixed(1)}%`;
	}
</script>

{#if groups.length}
	<div class="table-stack">
		{#each groups as group}
			<section class="table-group">
				<header>
					<h3>{group.label}</h3>
					<span>{group.periods.at(-1) ?? 'period 대기'}</span>
				</header>
				<div class="scroll">
					<table>
						<thead>
							<tr>
								<th>계정</th>
								{#each group.periods as period}
									<th>{period}</th>
								{/each}
								<th>YoY</th>
							</tr>
						</thead>
						<tbody>
							{#each group.rows as row}
								<tr
									role="button"
									tabindex="0"
									onclick={() => onSelect?.(row, group)}
									onkeydown={(event) => {
										if (event.key === 'Enter' || event.key === ' ') onSelect?.(row, group);
									}}
								>
									<td>
										<strong>{row.label}</strong>
										<small>{row.source}</small>
									</td>
									{#each row.values as value}
										<td>{formatTableValue(value, row.unit)}</td>
									{/each}
									<td class:up={(row.yoy ?? 0) > 0} class:down={(row.yoy ?? 0) < 0}>{yoyText(row.yoy)}</td>
								</tr>
							{/each}
						</tbody>
					</table>
				</div>
			</section>
		{/each}
	</div>
{/if}

<style>
	.table-stack {
		display: grid;
		gap: 10px;
	}
	.table-group {
		min-width: 0;
		border: 1px solid #172033;
		border-radius: 7px;
		background: #070c15;
	}
	header {
		display: flex;
		justify-content: space-between;
		gap: 12px;
		align-items: center;
		border-bottom: 1px solid #172033;
		padding: 10px 12px;
	}
	h3 {
		margin: 0;
		color: #f8fafc;
		font-size: 14px;
		font-weight: 780;
	}
	header span {
		color: #94a3b8;
		font-size: 11px;
	}
	.scroll {
		max-width: 100%;
		overflow-x: auto;
	}
	table {
		width: 100%;
		min-width: 760px;
		border-collapse: collapse;
		font-size: 12px;
	}
	th,
	td {
		border-bottom: 1px solid #172033;
		padding: 8px 10px;
		text-align: right;
		white-space: nowrap;
	}
	th {
		background: #0d1422;
		color: #94a3b8;
		font-size: 11px;
		font-weight: 700;
	}
	th:first-child,
	td:first-child {
		position: sticky;
		left: 0;
		z-index: 1;
		width: 220px;
		min-width: 220px;
		max-width: 220px;
		background: #070c15;
		text-align: left;
	}
	td:first-child strong,
	td:first-child small {
		display: block;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	td:first-child small {
		margin-top: 2px;
		color: #64748b;
		font-size: 10px;
	}
	tr {
		cursor: pointer;
	}
	tr:hover td,
	tr:focus-within td {
		background: #0d1422;
	}
	td.up {
		color: #34d399;
	}
	td.down {
		color: #f87171;
	}
</style>
