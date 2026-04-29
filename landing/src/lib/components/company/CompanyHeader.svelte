<script lang="ts">
	import FreshnessBadge from '$lib/components/industry/FreshnessBadge.svelte';
	import type { PeriodMode } from '$lib/browser/companyDashboardModel';
	import type { LiveCompanyBundle } from '$lib/browser/companyLive';

	let {
		title,
		subtitle,
		tags = [],
		latestPeriod = null,
		periodMode = 'Q',
		company = null,
		onPeriodChange,
		onOpenEvidence
	}: {
		title: string;
		subtitle: string;
		tags?: string[];
		latestPeriod?: string | null;
		periodMode?: PeriodMode;
		company?: LiveCompanyBundle | null;
		onPeriodChange?: (mode: PeriodMode) => void;
		onOpenEvidence?: () => void;
	} = $props();

	const modes: Array<{ key: PeriodMode; label: string; title: string }> = [
		{ key: 'Q', label: '분기', title: '최근 8분기' },
		{ key: 'TTM', label: 'TTM', title: '최근 4분기 합산' },
		{ key: 'Y', label: '연간', title: '최근 5년' }
	];
</script>

<section class="company-header" id="summary" data-section>
	<div class="identity">
		<div class="eyebrow">Company Analysis</div>
		<h1>{title}</h1>
		<p>{subtitle}</p>
		<div class="tags">
			{#each tags as tag}
				<span>{tag}</span>
			{/each}
		</div>
	</div>

	<div class="tools">
		<div class="periods" aria-label="기간 선택">
			{#each modes as mode}
				<button
					type="button"
					class:active={periodMode === mode.key}
					title={mode.title}
					onclick={() => onPeriodChange?.(mode.key)}
				>
					{mode.label}
				</button>
			{/each}
		</div>
		<div class="meta">
			<span>기준 {latestPeriod ?? '대기'}</span>
			{#if company?.meta?.dataAsOf}
				<FreshnessBadge dataAsOf={company.meta.dataAsOf} variant="compact" />
			{/if}
		</div>
		<button type="button" class="evidence" onclick={onOpenEvidence}>근거 보기</button>
	</div>
</section>

<style>
	.company-header {
		display: grid;
		grid-template-columns: minmax(0, 1fr) auto;
		gap: 24px;
		align-items: end;
		max-width: 1480px;
		margin: 0 auto;
		border-bottom: 1px solid #1e2433;
		padding: 18px 0 16px;
	}
	.eyebrow {
		color: #fb923c;
		font-size: 11px;
		font-weight: 900;
		letter-spacing: 0;
	}
	h1,
	p {
		margin: 0;
	}
	h1 {
		margin-top: 5px;
		color: #f8fafc;
		font-size: clamp(32px, 3.4vw, 42px);
		font-weight: 850;
		letter-spacing: 0;
		line-height: 1.08;
	}
	p {
		margin-top: 7px;
		color: #cbd5e1;
		font-size: 13px;
		line-height: 1.45;
	}
	.tags,
	.tools,
	.meta {
		display: flex;
		flex-wrap: wrap;
		gap: 7px;
	}
	.tags {
		margin-top: 12px;
	}
	.tags span,
	.meta span {
		border: 1px solid #263145;
		border-radius: 6px;
		background: #070c15;
		color: #bfdbfe;
		font-size: 11px;
		padding: 6px 8px;
	}
	.tools {
		justify-content: end;
		align-items: center;
		max-width: 560px;
	}
	.periods {
		display: flex;
		overflow: hidden;
		border: 1px solid #263145;
		border-radius: 7px;
		background: #070c15;
	}
	.periods button,
	.evidence {
		border: 0;
		background: transparent;
		color: #94a3b8;
		cursor: pointer;
		font: inherit;
		font-size: 12px;
		padding: 8px 11px;
	}
	.periods button.active {
		background: #fb923c;
		color: #050811;
		font-weight: 800;
	}
	.evidence {
		border: 1px solid #263145;
		border-radius: 7px;
		background: #0b111e;
		color: #f8fafc;
	}
	@media (max-width: 860px) {
		.company-header {
			grid-template-columns: 1fr;
			gap: 14px;
		}
		.tools {
			justify-content: flex-start;
		}
	}
</style>
