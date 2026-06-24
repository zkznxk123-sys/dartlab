<script lang="ts">
	import { STORAGE_STEPS, ROLLOUT_STEPS } from '$lib/siteSignals/model';
	import type { SiteSignalsPublicPayload } from '$lib/siteSignals/types';

	let { payload }: { payload: SiteSignalsPublicPayload } = $props();
</script>

<aside class="boundary-panel" aria-label="수집 경계">
	<section class="pane">
		<div class="panel-title">수집 경계 <span>{payload.status}</span></div>
		<div class="rule-list">
			<div class="rule ok">
				<strong>집계만 누적</strong>
				<span>원시 이벤트 row를 오래 보관하지 않고 counter만 증가시킨다.</span>
			</div>
			<div class="rule no">
				<strong>식별자 저장 안 함</strong>
				<span>원시 IP, User-Agent 원문, 세션별 이동 경로는 저장하지 않는다.</span>
			</div>
			<div class="rule public">
				<strong>공개는 표본 기준 이후</strong>
				<span>최소 N={payload.minPublicSample} 이상인 집계만 공개 화면에 연결한다.</span>
			</div>
		</div>
	</section>

	<section class="pane">
		<div class="panel-title">저장 흐름 <span>D1</span></div>
		<div class="flow">
			{#each STORAGE_STEPS as step (step.label)}
				<div class="flow-row">
					<div class="flow-key">{step.label}</div>
					<div class="flow-body">
						<strong>{step.title}</strong>
						<span>{step.body}</span>
					</div>
				</div>
			{/each}
		</div>
	</section>

	<section class="pane">
		<div class="panel-title">출시 단계 <span>clean</span></div>
		<div class="rollout">
			{#each ROLLOUT_STEPS as step (step.label)}
				<div class="roll-row">
					<span class="roll-index">{step.label}</span>
					<div>
						<div class="roll-head">
							<strong>{step.title}</strong>
							<span>{step.state}</span>
						</div>
						<p>{step.body}</p>
					</div>
				</div>
			{/each}
		</div>
	</section>
</aside>

<style>
	.boundary-panel {
		min-height: 0;
		overflow-y: auto;
		border-left: 1px solid #1e2433;
		background: #070b14;
	}
	.pane {
		padding: 10px;
		border-bottom: 1px solid #1e2433;
	}
	.panel-title {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 10px;
		margin-bottom: 9px;
		color: #e2e8f0;
		font-size: 11px;
		font-weight: 800;
		letter-spacing: 0;
		text-transform: uppercase;
	}
	.panel-title span {
		padding: 2px 6px;
		border: 1px solid #263145;
		border-radius: 5px;
		color: #94a3b8;
		font-size: 10px;
		text-transform: none;
	}
	.rule-list,
	.flow,
	.rollout {
		display: flex;
		flex-direction: column;
		gap: 7px;
	}
	.rule {
		display: grid;
		gap: 3px;
		padding: 8px;
		border: 1px solid #1e2433;
		border-radius: 6px;
		background: #0a0e18;
	}
	.rule strong {
		color: #f8fafc;
		font-size: 12px;
	}
	.rule span {
		color: #94a3b8;
		font-size: 11px;
		line-height: 1.5;
	}
	.rule.ok {
		border-color: rgba(52, 211, 153, 0.24);
	}
	.rule.no {
		border-color: rgba(248, 113, 113, 0.22);
	}
	.rule.public {
		border-color: rgba(var(--dl-accent-rgb), 0.32);
	}
	.flow-row {
		display: grid;
		grid-template-columns: 72px minmax(0, 1fr);
		gap: 8px;
		padding: 8px 0;
		border-bottom: 1px dashed #1e2433;
	}
	.flow-row:last-child {
		border-bottom: none;
	}
	.flow-key,
	.roll-index {
		color: var(--dl-accent);
		font-family: monospace;
		font-size: 11px;
		font-weight: 700;
	}
	.flow-body {
		display: grid;
		gap: 3px;
		min-width: 0;
	}
	.flow-body strong {
		color: #cbd5e1;
		font-size: 12px;
	}
	.flow-body span,
	.roll-row p {
		margin: 0;
		color: #94a3b8;
		font-size: 11px;
		line-height: 1.5;
	}
	.roll-row {
		display: grid;
		grid-template-columns: 24px minmax(0, 1fr);
		gap: 8px;
		padding: 8px;
		border: 1px solid #1e2433;
		border-radius: 6px;
		background: #0a0e18;
	}
	.roll-head {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 8px;
		margin-bottom: 3px;
	}
	.roll-head strong {
		color: #e2e8f0;
		font-size: 12px;
	}
	.roll-head span {
		color: #64748b;
		font-size: 10px;
	}
</style>
