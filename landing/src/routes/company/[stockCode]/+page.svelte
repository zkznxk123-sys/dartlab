<script lang="ts">
	import { onMount, tick } from 'svelte';
	import Header from '$lib/components/sections/Header.svelte';
	import CompanyHeader from '$lib/components/company/CompanyHeader.svelte';
	import EvidencePanel from '$lib/components/company/EvidencePanel.svelte';
	import KpiRibbon from '$lib/components/company/KpiRibbon.svelte';
	import StatementSection from '$lib/components/company/StatementSection.svelte';
	import StoryReportSection from '$lib/components/company/StoryReportSection.svelte';
	import TocRail from '$lib/components/company/TocRail.svelte';
	import {
		buildEvidenceForAccount,
		buildStatementDashboard,
		loadLiveCompany,
		loadLiveCompanyChanges,
		loadLiveCompanyDocs,
		loadLiveCompanyReportFacts,
		loadLiveCompanyStatement,
		type LiveCompanyBundle,
		type LiveCompanyChange,
		type LiveCompanyDocExcerpt,
		type LiveCompanyReportFact,
		type LiveStatementSlot,
		type StatementFreq,
		type StatementGroupRow,
		type StatementKey
	} from '$lib/browser/companyLive';
	import {
		buildCompanyDashboardView,
		type FinancialTableGroup,
		type FinancialTableRow,
		type PeriodMode
	} from '$lib/browser/companyDashboardModel';
	import { loadStoryManifest, type StoryManifest } from '$lib/browser/storyDashboard';
	import type { BrowserTable } from '$lib/browser/types';
	import type { PageData } from './$types';
	import {
		loadAllChartSpecs,
		loadChartManifest,
		groupBySection,
		type ChartManifest,
		type ChartSpec,
		type ChartPointRef
	} from '$lib/browser/charts';
	import ChartRenderer from '$chart/ChartRenderer.svelte';
	import CopilotDock from '$lib/components/company/CopilotDock.svelte';

	let { data }: { data: PageData } = $props();

	const STATEMENTS: StatementKey[] = ['IS', 'BS', 'CF'];

	let manifest = $state<StoryManifest | null>(null);
	let company = $state<LiveCompanyBundle | null>(null);
	let statements = $state<Record<StatementKey, LiveStatementSlot> | null>(null);
	let periodMode = $state<PeriodMode>('Q');
	let loading = $state(true);
	let secondaryLoading = $state(false);
	let errorMessage = $state('');
	let statementLoading = $state<Record<StatementKey, boolean>>({ IS: false, BS: false, CF: false });
	let changes = $state<LiveCompanyChange[]>([]);
	let reportFacts = $state<LiveCompanyReportFact[]>([]);
	let docs = $state<LiveCompanyDocExcerpt[]>([]);
	let selectedRow = $state<StatementGroupRow | null>(null);
	let selectedPeriods = $state<string[]>([]);
	let evidenceOpen = $state(false);
	let activeSection = $state('summary');
	let observer: IntersectionObserver | null = null;

	// viz SSOT — Python dartlab.viz 가 빌드한 ChartSpec dump.
	// 매니페스트 + section 별 ChartSpec dict. 없으면 기존 view-based 회로 fallback.
	let chartManifest = $state<ChartManifest | null>(null);
	let chartSpecs = $state<Map<string, ChartSpec>>(new Map());

	onMount(() => {
		void boot();
		return () => observer?.disconnect();
	});

	async function boot() {
		loading = true;
		errorMessage = '';
		selectedRow = null;
		selectedPeriods = [];
		evidenceOpen = false;

		try {
			const [nextManifest, bundle, isQ, bsQ, cfQ, nextChartManifest] = await Promise.all([
				loadStoryManifest(fetch),
				loadLiveCompany(data.stockCode),
				loadLiveCompanyStatement(data.stockCode, 'IS', 'Q'),
				loadLiveCompanyStatement(data.stockCode, 'BS', 'Q'),
				loadLiveCompanyStatement(data.stockCode, 'CF', 'Q'),
				loadChartManifest(data.stockCode, fetch)
			]);
			manifest = nextManifest;
			company = bundle;
			statements = mergeQuarterly(bundle.statements, { IS: isQ, BS: bsQ, CF: cfQ });
			chartManifest = nextChartManifest;
			if (nextChartManifest) {
				chartSpecs = await loadAllChartSpecs(data.stockCode, nextChartManifest, fetch);
			}
			loading = false;
			await tick();
			observeSections();
			void loadSecondaryData();
		} catch (err) {
			errorMessage = err instanceof Error ? err.message : String(err);
			loading = false;
		}
	}

	async function loadSecondaryData() {
		secondaryLoading = true;
		try {
			const [nextChanges, nextFacts, nextDocs, isY, bsY, cfY] = await Promise.all([
				loadLiveCompanyChanges(data.stockCode, 12),
				loadLiveCompanyReportFacts(data.stockCode),
				loadLiveCompanyDocs(data.stockCode, 16),
				loadLiveCompanyStatement(data.stockCode, 'IS', 'Y'),
				loadLiveCompanyStatement(data.stockCode, 'BS', 'Y'),
				loadLiveCompanyStatement(data.stockCode, 'CF', 'Y')
			]);
			changes = nextChanges;
			reportFacts = nextFacts;
			docs = nextDocs;
			mergeAnnualDetails({ IS: isY, BS: bsY, CF: cfY });
			await tick();
			observeSections();
		} finally {
			secondaryLoading = false;
		}
	}

	function mergeAnnualDetails(annual: Record<StatementKey, BrowserTable | null>) {
		if (!statements) return;
		statements = {
			IS: { ...statements.IS, annual: betterTable(annual.IS, statements.IS.annual) },
			BS: { ...statements.BS, annual: betterTable(annual.BS, statements.BS.annual) },
			CF: { ...statements.CF, annual: betterTable(annual.CF, statements.CF.annual) }
		};
	}

	function betterTable(next: BrowserTable | null, current: BrowserTable | null): BrowserTable | null {
		if (!next) return current;
		if (!current) return next;
		return next.rows.length >= current.rows.length ? next : current;
	}

	function mergeQuarterly(
		base: Record<StatementKey, LiveStatementSlot>,
		quarterly: Record<StatementKey, BrowserTable | null>
	): Record<StatementKey, LiveStatementSlot> {
		return {
			IS: mergeSlot(base.IS, quarterly.IS),
			BS: mergeSlot(base.BS, quarterly.BS),
			CF: mergeSlot(base.CF, quarterly.CF)
		};
	}

	function mergeSlot(slot: LiveStatementSlot, quarterly: BrowserTable | null): LiveStatementSlot {
		return {
			annual: slot.annual,
			quarterly: quarterly ?? slot.quarterly,
			status: quarterly ? 'ready' : slot.status,
			source: quarterly?.source ?? slot.source
		};
	}

	function observeSections() {
		observer?.disconnect();
		observer = new IntersectionObserver(
			(entries) => {
				const visible = entries
					.filter((entry) => entry.isIntersecting)
					.sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
				if (visible?.target?.id) activeSection = visible.target.id;
			},
			{ rootMargin: '-18% 0px -64% 0px', threshold: [0.12, 0.35, 0.6] }
		);
		document.querySelectorAll<HTMLElement>('[data-section]').forEach((el) => observer?.observe(el));
	}

	async function setPeriodMode(next: PeriodMode) {
		periodMode = next;
		selectedRow = null;
		selectedPeriods = [];
		await Promise.all(STATEMENTS.map((topic) => hydrateStatement(topic, next === 'Y' ? 'Y' : 'Q')));
		await tick();
		observeSections();
	}

	async function hydrateStatement(topic: StatementKey, freq: StatementFreq) {
		const slot = statements?.[topic];
		const hasTable = freq === 'Y' ? slot?.annual : slot?.quarterly;
		if (hasTable) return;

		statementLoading = { ...statementLoading, [topic]: true };
		try {
			const live = await loadLiveCompanyStatement(data.stockCode, topic, freq);
			if (!live || !statements) return;
			const current = statements[topic];
			statements = {
				...statements,
				[topic]: {
					annual: freq === 'Y' ? live : current.annual,
					quarterly: freq === 'Q' ? live : current.quarterly,
					status: 'ready',
					source: live.source
				}
			};
		} finally {
			statementLoading = { ...statementLoading, [topic]: false };
		}
	}

	function tableFor(topic: StatementKey): BrowserTable | null {
		const slot = statements?.[topic];
		return periodMode === 'Y' ? (slot?.annual ?? null) : (slot?.quarterly ?? null);
	}

	function openEvidence() {
		selectedRow = null;
		selectedPeriods = [];
		evidenceOpen = true;
	}

	function selectTableRow(row: FinancialTableRow, group: FinancialTableGroup) {
		selectedRow = row.raw ?? null;
		selectedPeriods = group.periods;
		evidenceOpen = true;
	}

	let dashboards = $derived({
		IS: buildStatementDashboard('IS', tableFor('IS')),
		BS: buildStatementDashboard('BS', tableFor('BS')),
		CF: buildStatementDashboard('CF', tableFor('CF'))
	});
	let annualDashboards = $derived({
		IS: buildStatementDashboard('IS', statements?.IS.annual ?? null),
		BS: buildStatementDashboard('BS', statements?.BS.annual ?? null),
		CF: buildStatementDashboard('CF', statements?.CF.annual ?? null)
	});
	let view = $derived(
		buildCompanyDashboardView({ manifest, company, dashboards, annualDashboards, facts: reportFacts, docs, changes, periodMode })
	);
	let evidence = $derived(buildEvidenceForAccount(selectedRow, selectedPeriods, reportFacts, docs, changes));
	let tocItems = $derived([
		{ id: 'summary', label: '요약' },
		...view.questions.map((section) => ({ id: section.id, label: section.tocLabel })),
		{ id: 'is', label: 'IS' },
		{ id: 'bs', label: 'BS' },
		{ id: 'cf', label: 'CF' }
	]);
	let busyStatements = $derived(Object.values(statementLoading).some(Boolean));

	// ChartSpec 매니페스트의 section 별 grouping
	let chartSections = $derived(chartManifest ? groupBySection(chartManifest) : {});
	let heroCharts = $derived((chartSections.hero ?? []).map((e) => chartSpecs.get(e.key)).filter((s): s is ChartSpec => Boolean(s)));
	let narrativeCharts = $derived((chartSections.narrative ?? []).map((e) => ({ entry: e, spec: chartSpecs.get(e.key) })).filter((p): p is { entry: typeof p.entry; spec: ChartSpec } => Boolean(p.spec)));

	let copilotDock = $state<{ setContext: (ctx: Record<string, unknown>) => void } | null>(null);

	function onChartPoint(ref: object) {
		// drill-back 회로의 진입점.
		// 1. EvidencePanel 열기 (Phase 2 deep-link).
		// 2. CopilotDock 에 selection context 주입 (다음 질문이 그 selection 컨텍스트로).
		evidenceOpen = true;
		const point = ref as ChartPointRef;
		copilotDock?.setContext({
			chartId: point.name,
			accountKey: point.name,
			valueRef: point.valueRef,
			period: point.period,
			rcept_no: point.rcept_no
		});
	}
</script>

<svelte:head>
	<title>{view.title} Company · dartlab</title>
	<meta name="description" content="{view.title} 재무제표, 정기보고서, 사업보고서 원문 기반 company 대시보드." />
</svelte:head>

<Header context="landing" />

<main class="company-page">
	{#if loading}
		<section class="state">
			<div class="spinner"></div>
			<p>회사 재무제표와 근거 데이터를 여는 중</p>
		</section>
	{:else if errorMessage}
		<section class="state error">
			<h1>로드 실패</h1>
			<p>{errorMessage}</p>
			<button type="button" onclick={boot}>다시 시도</button>
		</section>
	{:else if company}
		<CompanyHeader
			title={view.title}
			subtitle={view.subtitle}
			tags={view.tags}
			latestPeriod={view.latestPeriod}
			{periodMode}
			{company}
			onPeriodChange={setPeriodMode}
			onOpenEvidence={openEvidence}
		/>

		<TocRail activeSection={activeSection} items={tocItems} />

		{#if heroCharts.length}
			<section class="hero-charts" data-section id="hero">
				{#each heroCharts as spec}
					<ChartRenderer {spec} onPointClick={onChartPoint} />
				{/each}
			</section>
		{/if}

		<KpiRibbon metrics={view.kpis} onSelect={() => (evidenceOpen = true)} />

		{#if busyStatements || secondaryLoading}
			<div class="load-note">
				<span>{busyStatements ? '재무제표 전환 중' : '보고서와 원문 근거 연결 중'}</span>
			</div>
		{/if}

		<div class="report-grid">
			{#each view.questions as section}
				<StoryReportSection {section} onOpenEvidence={openEvidence} onSelectRow={selectTableRow} />
			{/each}

			{#if narrativeCharts.length}
				<section class="viz-narrative-band" data-section id="viz-narrative">
					<div class="band-head">
						<div class="eyebrow">viz 엔진 산출</div>
						<h2>차트 SSOT</h2>
						<p>Python <code>dartlab.viz</code> 가 빌드한 ChartSpec — 모든 datapoint 가 tableRef 까지 drill 된다.</p>
					</div>
					<div class="viz-narrative-grid">
						{#each narrativeCharts as { entry, spec }}
							<article>
								<header>
									<small>{entry.purpose ?? entry.chartType}</small>
									<h3>{entry.title}</h3>
								</header>
								<ChartRenderer {spec} onPointClick={onChartPoint} />
							</article>
						{/each}
					</div>
				</section>
			{/if}

			<section class="statement-band">
				<div>
					<div class="eyebrow">원표 대조</div>
					<h2>IS · BS · CF</h2>
					<p>질문별 판단을 재무제표 원표와 바로 대조합니다. 표 내부만 가로 스크롤됩니다.</p>
				</div>
			</section>

			{#each STATEMENTS as topic}
				<StatementSection dashboard={dashboards[topic]} onSelect={selectTableRow} />
			{/each}
		</div>

		<EvidencePanel
			bind:open={evidenceOpen}
			{evidence}
			facts={reportFacts}
			{docs}
			{changes}
			sourceStatus={company.sourceStatus}
		/>

		<div class="copilot-anchor">
			<CopilotDock
				bind:this={copilotDock}
				stockCode={data.stockCode}
				onOpenEvidence={() => (evidenceOpen = true)}
			/>
		</div>
	{/if}
</main>

<style>
	.company-page {
		--company-shell-width: 72rem;
		min-height: 100vh;
		overflow-x: hidden;
		background:
			radial-gradient(circle at 16% 0%, rgba(251, 146, 60, 0.15), transparent 28%),
			linear-gradient(180deg, #050811 0%, #07101a 42%, #030509 100%);
		color: #f8fafc;
		padding: 68px 28px 80px;
	}
	.report-grid {
		display: grid;
		grid-template-columns: repeat(12, minmax(0, 1fr));
		gap: 12px;
		max-width: var(--company-shell-width);
		margin: 12px auto 0;
	}
	.report-grid > :global(.story-report-section),
	.report-grid > :global(.statement),
	.statement-band {
		grid-column: 1 / -1;
	}
	.statement-band,
	.viz-narrative-band {
		border: 1px solid #1e2433;
		border-radius: 8px;
		background: rgba(8, 13, 23, 0.96);
		padding: 16px;
	}
	.hero-charts {
		max-width: var(--company-shell-width);
		margin: 12px auto 0;
		display: grid;
		grid-template-columns: 1fr;
		gap: 12px;
	}
	.viz-narrative-band {
		display: grid;
		gap: 14px;
	}
	.viz-narrative-band .band-head {
		display: grid;
		gap: 4px;
	}
	.viz-narrative-grid {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(min(420px, 100%), 1fr));
		gap: 12px;
	}
	.viz-narrative-grid article {
		border: 1px solid #263145;
		border-radius: 7px;
		background: #060b13;
		padding: 11px 13px;
	}
	.viz-narrative-grid header small {
		display: block;
		font-size: 10px;
		color: #fb923c;
		font-weight: 700;
		text-transform: uppercase;
		letter-spacing: 0.04em;
	}
	.viz-narrative-grid header h3 {
		margin: 4px 0 8px;
		font-size: 14px;
		font-weight: 700;
		color: #f8fafc;
	}
	.copilot-anchor {
		position: fixed;
		right: 16px;
		bottom: 16px;
		width: min(360px, calc(100vw - 32px));
		max-height: calc(100vh - 32px);
		z-index: 60;
		pointer-events: auto;
	}
	@media (max-width: 880px) {
		.copilot-anchor {
			right: 8px;
			bottom: 8px;
			width: calc(100vw - 16px);
		}
	}
	.eyebrow {
		color: #fb923c;
		font-size: 11px;
		font-weight: 900;
		letter-spacing: 0;
	}
	h1,
	h2,
	p {
		margin: 0;
	}
	.statement-band h2 {
		margin-top: 5px;
		font-size: 24px;
	}
	.statement-band p {
		margin-top: 6px;
		color: #94a3b8;
		font-size: 13px;
		line-height: 1.45;
	}
	.load-note {
		max-width: 1480px;
		margin: 10px auto 0;
	}
	.load-note span {
		display: inline-block;
		border: 1px solid #263145;
		border-radius: 6px;
		background: #070c15;
		color: #94a3b8;
		font-size: 12px;
		padding: 7px 9px;
	}
	.state {
		display: grid;
		place-items: center;
		gap: 12px;
		min-height: 420px;
		text-align: center;
	}
	.state p {
		color: #94a3b8;
	}
	.state button {
		border: 1px solid #263145;
		border-radius: 7px;
		background: #070c15;
		color: #f8fafc;
		cursor: pointer;
		font: inherit;
		padding: 9px 12px;
	}
	.spinner {
		width: 28px;
		height: 28px;
		border: 2px solid #263145;
		border-top-color: #fb923c;
		border-radius: 50%;
		animation: spin 0.8s linear infinite;
	}
	@keyframes spin {
		to {
			transform: rotate(360deg);
		}
	}
	@media (max-width: 760px) {
		.company-page {
			padding: 60px 12px 48px;
		}
		.report-grid {
			gap: 10px;
		}
	}
</style>
