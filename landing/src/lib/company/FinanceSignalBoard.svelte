<script lang="ts">
	import type { CompanyFinancePeriodRow } from '$lib/scan/financeLiteRuntime';
	import {
		buildFinanceSignalSummary,
		type FinanceSignalTone
	} from './financeSignalModel';

	let { periods = [] }: { periods?: CompanyFinancePeriodRow[] } = $props();

	const summary = $derived(buildFinanceSignalSummary(periods ?? []));

	function toneLabel(tone: FinanceSignalTone): string {
		if (tone === 'good') return '양호';
		if (tone === 'bad') return '위험';
		if (tone === 'watch') return '관찰';
		if (tone === 'neutral') return '중립';
		return '보류';
	}

	function barHeight(value: number | null, series: Array<number | null>): number {
		if (value == null) return 4;
		const maxAbs = Math.max(1, ...series.filter((item): item is number => item != null).map((item) => Math.abs(item)));
		return Math.max(4, Math.round((Math.abs(value) / maxAbs) * 24));
	}
</script>

<section class="signal-board" aria-label="재무 판단 신호">
	<header class="signal-head">
		<div>
			<strong>재무 판단</strong>
			<span>{summary.periodLabel ?? 'finance-lite'}</span>
		</div>
		<em>{summary.coverage.available}/{summary.coverage.total}</em>
	</header>

	<div class="signal-grid">
		{#each summary.signals as signal (signal.id)}
			<article class="signal-card" class:good={signal.tone === 'good'} class:bad={signal.tone === 'bad'} class:watch={signal.tone === 'watch'} class:neutral={signal.tone === 'neutral'} class:missing={signal.tone === 'missing'}>
				<div class="signal-top">
					<span>{signal.label}</span>
					<em>{toneLabel(signal.tone)}</em>
				</div>
				<strong>{signal.value}</strong>
				<small>{signal.detail}</small>
				<div class="spark" aria-hidden="true">
					{#each signal.series.slice(-8) as point, i}
						<span
							class="bar"
							class:neg={point != null && point < 0}
							class:blank={point == null}
							style={`height: ${barHeight(point, signal.series)}px`}
						></span>
					{/each}
				</div>
			</article>
		{/each}
	</div>

	{#if summary.notes.length}
		<ul class="notes">
			{#each summary.notes.slice(0, 3) as note}
				<li>{note}</li>
			{/each}
		</ul>
	{/if}
</section>

<style>
	.signal-board {
		min-height: 0;
		display: flex;
		flex-direction: column;
		gap: 10px;
		padding: 10px;
		border: 1px solid #1e2433;
		border-radius: 8px;
		background: #050811;
		color: #f1f5f9;
	}
	.signal-head {
		flex-shrink: 0;
		display: flex;
		align-items: baseline;
		justify-content: space-between;
		gap: 10px;
	}
	.signal-head div {
		display: flex;
		align-items: baseline;
		gap: 8px;
		min-width: 0;
	}
	.signal-head strong {
		font-size: 13px;
		font-weight: 800;
		white-space: nowrap;
	}
	.signal-head span {
		color: #64748b;
		font-size: 11px;
		font-family: monospace;
	}
	.signal-head em {
		flex-shrink: 0;
		color: #94a3b8;
		font-size: 11px;
		font-style: normal;
		font-variant-numeric: tabular-nums;
	}
	.signal-grid {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(145px, 1fr));
		gap: 8px;
		align-items: stretch;
	}
	.signal-card {
		min-height: 106px;
		display: flex;
		flex-direction: column;
		gap: 5px;
		padding: 9px;
		border: 1px solid #1e2433;
		border-left-width: 3px;
		border-radius: 7px;
		background: #080d17;
	}
	.signal-card.good {
		border-left-color: #34d399;
	}
	.signal-card.bad {
		border-left-color: #f87171;
	}
	.signal-card.watch {
		border-left-color: #fbbf24;
	}
	.signal-card.neutral {
		border-left-color: #60a5fa;
	}
	.signal-card.missing {
		border-left-color: #475569;
	}
	.signal-top {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 8px;
	}
	.signal-top span {
		color: #94a3b8;
		font-size: 11px;
		font-weight: 700;
	}
	.signal-top em {
		flex-shrink: 0;
		color: #64748b;
		font-size: 10px;
		font-style: normal;
	}
	.signal-card strong {
		font-size: 20px;
		line-height: 1.05;
		font-weight: 850;
		font-variant-numeric: tabular-nums;
		overflow-wrap: anywhere;
	}
	.signal-card small {
		min-height: 14px;
		color: #64748b;
		font-size: 10px;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}
	.spark {
		height: 26px;
		display: flex;
		align-items: flex-end;
		gap: 3px;
		margin-top: auto;
	}
	.bar {
		width: 100%;
		min-width: 5px;
		max-width: 18px;
		border-radius: 2px 2px 0 0;
		background: #38bdf8;
		opacity: 0.75;
	}
	.bar.neg {
		background: #fb7185;
	}
	.bar.blank {
		background: #334155;
		opacity: 0.55;
	}
	.notes {
		flex-shrink: 0;
		margin: 0;
		padding: 8px 0 0;
		border-top: 1px solid #1e2433;
		list-style: none;
		display: flex;
		flex-direction: column;
		gap: 4px;
		color: #64748b;
		font-size: 10px;
		line-height: 1.35;
	}
	.notes li {
		overflow-wrap: anywhere;
	}
	@media (max-width: 980px) {
		.signal-grid {
			grid-template-columns: repeat(3, minmax(0, 1fr));
		}
	}
	@media (max-width: 760px) {
		.signal-grid {
			grid-template-columns: repeat(2, minmax(0, 1fr));
		}
	}
	@media (max-width: 520px) {
		.signal-grid {
			grid-template-columns: 1fr;
		}
	}
</style>
