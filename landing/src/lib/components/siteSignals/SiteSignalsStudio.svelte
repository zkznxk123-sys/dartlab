<script lang="ts">
	import { onMount } from 'svelte';
	import { Activity, Database, Eye, EyeOff, GitBranch, ShieldCheck } from 'lucide-svelte';
	import Header from '$lib/components/sections/Header.svelte';
	import SignalBoundaryPanel from '$lib/components/siteSignals/SignalBoundaryPanel.svelte';
	import SignalMatrix from '$lib/components/siteSignals/SignalMatrix.svelte';
	import SignalRail from '$lib/components/siteSignals/SignalRail.svelte';
	import { loadSiteSignals } from '$lib/siteSignals/load';
	import {
		INITIAL_PUBLIC_PAYLOAD,
		RAIL_SECTIONS,
		SIGNAL_SPECS,
		SIGNAL_WINDOWS
	} from '$lib/siteSignals/model';
	import type { RailSectionKey, SignalWindowKey, SiteSignalsPublicPayload } from '$lib/siteSignals/types';

	let payload = $state<SiteSignalsPublicPayload>(INITIAL_PUBLIC_PAYLOAD);
	let activeSection = $state<RailSectionKey>('overview');
	let activeWindow = $state<SignalWindowKey>('30d');
	let loading = $state(true);

	onMount(() => {
		void loadSiteSignals().then((next) => {
			payload = next;
			loading = false;
		});
	});

	const visibleSignals = $derived.by(() => {
		if (activeSection === 'collect' || activeSection === 'public' || activeSection === 'storage') {
			return SIGNAL_SPECS.filter((signal) => signal.group === 'collect');
		}
		if (activeSection === 'exclude') {
			return SIGNAL_SPECS.filter((signal) => signal.group === 'exclude');
		}
		return SIGNAL_SPECS;
	});
	const collectCount = $derived(SIGNAL_SPECS.filter((signal) => signal.group === 'collect').length);
	const excludedCount = $derived(SIGNAL_SPECS.filter((signal) => signal.group === 'exclude').length);

	function pickWindow(key: SignalWindowKey) {
		activeWindow = key;
	}
</script>

<Header context="landing" />

<main class="signals-page">
	<header class="page-head">
		<div class="ph-left">
			<h1 class="ph-title">사이트 신호</h1>
			<span class="ph-code">site-signals</span>
			<span class="ph-section">공개 문서 사이트의 집계 관측 원칙</span>
		</div>
		<div class="ph-right">
			<span class="status-chip" class:active={payload.status === 'active'}>{payload.status}</span>
			<span class="meta">min N={payload.minPublicSample}</span>
			<span class="meta">{loading ? '불러오는 중' : new Date(payload.generatedAt).toLocaleDateString('ko-KR')}</span>
		</div>
	</header>

	<div class="ribbon-bar">
		<div class="window-track" aria-label="집계 기간">
			{#each SIGNAL_WINDOWS as window (window.key)}
				<button type="button" class="window-chip" class:active={activeWindow === window.key} onclick={() => pickWindow(window.key)}>
					{window.label}
				</button>
			{/each}
		</div>
	</div>

	<div class="signals-studio">
		<aside class="toc">
			<SignalRail sections={RAIL_SECTIONS} active={activeSection} onpick={(key) => (activeSection = key)} />
		</aside>

		<section class="board">
			<div class="overview-strip">
				<div class="strip-card">
					<Eye size={16} />
					<div>
						<span>집계 예정</span>
						<strong>{collectCount}</strong>
					</div>
				</div>
				<div class="strip-card muted">
					<EyeOff size={16} />
					<div>
						<span>수집 제외</span>
						<strong>{excludedCount}</strong>
					</div>
				</div>
				<div class="strip-card">
					<Database size={16} />
					<div>
						<span>원시 저장</span>
						<strong>0</strong>
					</div>
				</div>
				<div class="strip-card">
					<ShieldCheck size={16} />
					<div>
						<span>공개 기준</span>
						<strong>{payload.minPublicSample}+</strong>
					</div>
				</div>
			</div>

			{#if activeSection === 'overview'}
				<section class="principle">
					<div class="principle-head">
						<Activity size={18} />
						<div>
							<h2>공개 문서의 사용성을 집계 신호로만 본다</h2>
							<p>방문자 개인을 따라가는 것이 아니라, 문서와 도구의 어느 지점이 실제로 읽히고 막히는지 확인한다.</p>
						</div>
					</div>
					<div class="principle-grid">
						<div>
							<strong>수집 전 고정</strong>
							<span>이 화면은 실제 계측보다 먼저 수집 범위와 제외 항목을 공개한다.</span>
						</div>
						<div>
							<strong>집계 우선</strong>
							<span>D1에는 counter만 남기고, 공개 화면에는 최소 표본 기준을 통과한 값만 연결한다.</span>
						</div>
						<div>
							<strong>제품 분석과 분리</strong>
							<span>나중에 생길 분석 뷰와 충돌하지 않게 운영 관측 페이지로 둔다.</span>
						</div>
					</div>
				</section>
			{:else if activeSection === 'rollout'}
				<section class="principle">
					<div class="principle-head">
						<GitBranch size={18} />
						<div>
							<h2>덕지덕지 붙이지 않는 출시 순서</h2>
							<p>페이지뷰와 CTA부터 켜고, 체류·스크롤은 공개 기준과 집계 품질을 검증한 뒤 추가한다.</p>
						</div>
					</div>
				</section>
			{/if}

			<div class="matrix-frame">
				<SignalMatrix signals={visibleSignals} {payload} {activeWindow} />
			</div>
		</section>

		<SignalBoundaryPanel {payload} />
	</div>
</main>

<style>
	.signals-page {
		height: 100vh;
		overflow: hidden;
		display: flex;
		flex-direction: column;
		padding: 56px 0 0;
		background: #050811;
		color: #f1f5f9;
	}
	.page-head {
		flex-shrink: 0;
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 16px;
		padding: 8px 12px;
		border-bottom: 1px solid #1e2433;
	}
	.ph-left {
		display: flex;
		align-items: baseline;
		gap: 8px;
		min-width: 0;
	}
	.ph-title {
		margin: 0;
		color: #f1f5f9;
		font-size: 20px;
		font-weight: 800;
		letter-spacing: 0;
		white-space: nowrap;
	}
	.ph-code {
		flex-shrink: 0;
		color: #64748b;
		font-family: monospace;
		font-size: 11px;
	}
	.ph-section {
		min-width: 0;
		overflow: hidden;
		color: #94a3b8;
		font-size: 12px;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	.ph-section::before {
		content: '·';
		margin-right: 6px;
		color: #475569;
	}
	.ph-right {
		display: flex;
		align-items: center;
		gap: 10px;
		flex-shrink: 0;
	}
	.status-chip {
		display: inline-flex;
		align-items: center;
		height: 24px;
		padding: 0 8px;
		border: 1px solid rgba(251, 146, 60, 0.45);
		border-radius: 5px;
		background: rgba(251, 146, 60, 0.1);
		color: #fdba74;
		font-family: monospace;
		font-size: 11px;
	}
	.status-chip.active {
		border-color: rgba(52, 211, 153, 0.45);
		background: rgba(52, 211, 153, 0.08);
		color: #86efac;
	}
	.meta {
		color: #94a3b8;
		font-size: 11px;
		white-space: nowrap;
	}
	.ribbon-bar {
		flex-shrink: 0;
		padding: 6px 12px;
		border-bottom: 1px solid #1e2433;
	}
	.window-track {
		display: flex;
		align-items: center;
		gap: 1px;
		overflow-x: auto;
	}
	.window-chip {
		flex-shrink: 0;
		padding: 4px 10px;
		border: 1px solid transparent;
		border-top-color: #1e2433;
		border-bottom-color: #1e2433;
		background: transparent;
		color: #64748b;
		font-family: monospace;
		font-size: 10px;
		cursor: pointer;
		white-space: nowrap;
	}
	.window-chip:hover {
		background: rgba(251, 146, 60, 0.06);
		color: #cbd5e1;
	}
	.window-chip.active {
		border-color: rgba(251, 146, 60, 0.4);
		border-radius: 5px;
		background: rgba(251, 146, 60, 0.12);
		color: #f1f5f9;
	}
	.signals-studio {
		flex: 1 1 auto;
		min-height: 0;
		display: grid;
		grid-template-columns: 240px minmax(0, 1fr) 360px;
	}
	.toc {
		min-height: 0;
		overflow-y: auto;
		padding: 8px;
		border-right: 1px solid #1e2433;
	}
	.board {
		min-width: 0;
		min-height: 0;
		overflow: hidden;
		display: flex;
		flex-direction: column;
	}
	.overview-strip {
		flex-shrink: 0;
		display: grid;
		grid-template-columns: repeat(4, minmax(0, 1fr));
		gap: 1px;
		border-bottom: 1px solid #1e2433;
		background: #1e2433;
	}
	.strip-card {
		display: flex;
		align-items: center;
		gap: 9px;
		min-width: 0;
		padding: 10px 12px;
		background: #0a0e18;
		color: #fb923c;
	}
	.strip-card.muted {
		color: #94a3b8;
	}
	.strip-card div {
		display: grid;
		min-width: 0;
	}
	.strip-card span {
		color: #64748b;
		font-size: 10px;
	}
	.strip-card strong {
		color: #f8fafc;
		font-size: 18px;
		line-height: 1.15;
	}
	.principle {
		flex-shrink: 0;
		padding: 14px 16px;
		border-bottom: 1px solid #1e2433;
		background: #070b14;
	}
	.principle-head {
		display: flex;
		align-items: flex-start;
		gap: 10px;
		color: #fb923c;
	}
	.principle h2 {
		margin: 0 0 3px;
		color: #f8fafc;
		font-size: 16px;
		letter-spacing: 0;
	}
	.principle p {
		margin: 0;
		color: #94a3b8;
		font-size: 12px;
		line-height: 1.55;
	}
	.principle-grid {
		display: grid;
		grid-template-columns: repeat(3, minmax(0, 1fr));
		gap: 8px;
		margin-top: 12px;
	}
	.principle-grid div {
		display: grid;
		gap: 4px;
		padding: 9px;
		border: 1px solid #1e2433;
		border-radius: 6px;
		background: #0a0e18;
	}
	.principle-grid strong {
		color: #e2e8f0;
		font-size: 12px;
	}
	.principle-grid span {
		color: #94a3b8;
		font-size: 11px;
		line-height: 1.5;
	}
	.matrix-frame {
		flex: 1 1 auto;
		min-height: 0;
	}
	@media (max-width: 1120px) {
		.signals-studio {
			grid-template-columns: 220px minmax(0, 1fr);
		}
		.signals-studio :global(.boundary-panel) {
			display: none;
		}
	}
	@media (max-width: 880px) {
		.signals-page {
			height: auto;
			min-height: 100vh;
			overflow: visible;
		}
		.page-head {
			flex-wrap: wrap;
			gap: 8px 10px;
			padding: 8px 10px;
		}
		.ph-left {
			flex: 1 0 100%;
		}
		.ph-title {
			font-size: 17px;
		}
		.ph-right {
			flex-wrap: wrap;
			gap: 6px;
		}
		.signals-studio {
			display: flex;
			flex-direction: column;
			min-height: 0;
		}
		.toc {
			max-height: 180px;
			border-right: none;
			border-bottom: 1px solid #1e2433;
		}
		.overview-strip,
		.principle-grid {
			grid-template-columns: repeat(2, minmax(0, 1fr));
		}
		.board {
			overflow: visible;
		}
		.matrix-frame {
			height: 62vh;
			min-height: 420px;
		}
	}
	@media (max-width: 560px) {
		.overview-strip,
		.principle-grid {
			grid-template-columns: 1fr;
		}
	}
</style>
