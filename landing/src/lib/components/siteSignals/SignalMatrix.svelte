<script lang="ts">
	import type {
		SignalWindowKey,
		SiteSignalKey,
		SiteSignalsPublicPayload,
		SiteSignalSpec
	} from '$lib/siteSignals/types';

	let {
		signals,
		payload,
		activeWindow
	}: {
		signals: SiteSignalSpec[];
		payload: SiteSignalsPublicPayload;
		activeWindow: SignalWindowKey;
	} = $props();

	function statusLabel(status: SiteSignalSpec['status']): string {
		if (status === 'active') return 'active';
		if (status === 'planned') return 'planned';
		if (status === 'excluded') return 'excluded';
		return 'inactive';
	}

	function summaryText(key: SiteSignalKey): string {
		const summary = payload.summaries?.[activeWindow]?.[key];
		if (!summary) return '수집 전';
		if (summary.count != null) return `${summary.count.toLocaleString('ko-KR')}회`;
		if (summary.sampleN != null) return `N=${summary.sampleN.toLocaleString('ko-KR')}`;
		if (summary.bucket) return summary.bucket;
		return '집계 있음';
	}
</script>

<div class="matrix-scroll">
	<div class="signal-matrix">
		<div class="cell head">신호</div>
		<div class="cell head">상태</div>
		<div class="cell head">저장 형태</div>
		<div class="cell head">공개 수준</div>
		<div class="cell head">현재 집계</div>
		<div class="cell head">목적</div>

		{#each signals as signal (signal.key)}
			<div class="cell signal-name">
				<span class="label">{signal.label}</span>
				<span class="event">{signal.eventName}</span>
			</div>
			<div class="cell">
				<span class="status" class:planned={signal.status === 'planned'} class:excluded={signal.status === 'excluded'} class:active={signal.status === 'active'}>
					{statusLabel(signal.status)}
				</span>
			</div>
			<div class="cell subtle">{signal.storage}</div>
			<div class="cell subtle">{signal.publicLevel}</div>
			<div class="cell mono">{summaryText(signal.key)}</div>
			<div class="cell purpose">{signal.purpose}</div>
		{/each}
	</div>
</div>

<style>
	.matrix-scroll {
		height: 100%;
		overflow: auto;
	}
	.signal-matrix {
		display: grid;
		grid-template-columns: minmax(150px, 0.9fr) 96px minmax(180px, 1.15fr) minmax(120px, 0.8fr) 110px minmax(260px, 1.4fr);
		min-width: 980px;
	}
	.cell {
		min-width: 0;
		padding: 9px 10px;
		border-bottom: 1px solid #1e2433;
		color: #cbd5e1;
		font-size: 12px;
		line-height: 1.45;
	}
	.head {
		position: sticky;
		top: 0;
		z-index: 10;
		background: #0a0e18;
		border-bottom: 1px solid #263145;
		color: #64748b;
		font-size: 10px;
		font-weight: 800;
		letter-spacing: 0;
		text-transform: uppercase;
	}
	.signal-name {
		display: flex;
		flex-direction: column;
		gap: 2px;
	}
	.label {
		color: #f1f5f9;
		font-weight: 700;
	}
	.event {
		color: #64748b;
		font-family: monospace;
		font-size: 10px;
	}
	.status {
		display: inline-flex;
		align-items: center;
		height: 22px;
		padding: 0 7px;
		border: 1px solid #263145;
		border-radius: 5px;
		color: #94a3b8;
		font-family: monospace;
		font-size: 10px;
	}
	.status.planned {
		border-color: rgba(251, 146, 60, 0.5);
		background: rgba(251, 146, 60, 0.1);
		color: #fdba74;
	}
	.status.active {
		border-color: rgba(52, 211, 153, 0.45);
		background: rgba(52, 211, 153, 0.08);
		color: #86efac;
	}
	.status.excluded {
		border-color: rgba(148, 163, 184, 0.22);
		background: rgba(148, 163, 184, 0.05);
		color: #64748b;
	}
	.subtle {
		color: #94a3b8;
	}
	.mono {
		color: #f8fafc;
		font-family: monospace;
		font-variant-numeric: tabular-nums;
	}
	.purpose {
		color: #cbd5e1;
	}
</style>
