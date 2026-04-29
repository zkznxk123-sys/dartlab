<script lang="ts">
	import { onMount, tick } from 'svelte';
	import Header from '$lib/components/sections/Header.svelte';
	import CompanyHeader from '$lib/components/company/CompanyHeader.svelte';
	import EvidencePanel from '$lib/components/company/EvidencePanel.svelte';
	import KpiRibbon from '$lib/components/company/KpiRibbon.svelte';
	import QuestionSection from '$lib/components/company/QuestionSection.svelte';
	import StatementSection from '$lib/components/company/StatementSection.svelte';
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
			const [nextManifest, bundle, isQ, bsQ, cfQ] = await Promise.all([
				loadStoryManifest(fetch),
				loadLiveCompany(data.stockCode),
				loadLiveCompanyStatement(data.stockCode, 'IS', 'Q'),
				loadLiveCompanyStatement(data.stockCode, 'BS', 'Q'),
				loadLiveCompanyStatement(data.stockCode, 'CF', 'Q')
			]);
			manifest = nextManifest;
			company = bundle;
			statements = mergeQuarterly(bundle.statements, { IS: isQ, BS: bsQ, CF: cfQ });
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
			const [nextChanges, nextFacts, nextDocs] = await Promise.all([
				loadLiveCompanyChanges(data.stockCode, 12),
				loadLiveCompanyReportFacts(data.stockCode),
				loadLiveCompanyDocs(data.stockCode, 16)
			]);
			changes = nextChanges;
			reportFacts = nextFacts;
			docs = nextDocs;
			await tick();
			observeSections();
		} finally {
			secondaryLoading = false;
		}
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
	let view = $derived(
		buildCompanyDashboardView({ manifest, company, dashboards, facts: reportFacts, docs, changes, periodMode })
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
</script>

<svelte:head>
	<title>{view.title} Company · dartlab</title>
	<meta name="description" content="{view.title} 재무제표, 정기보고서, 사업보고서 원문 기반 company 대시보드." />
</svelte:head>

<Header context="landing" />

<main class="company-page">
	{#if !loading && company}
		<TocRail activeSection={activeSection} items={tocItems} />
	{/if}

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

		<KpiRibbon metrics={view.kpis} />

		{#if busyStatements || secondaryLoading}
			<div class="load-note">
				<span>{busyStatements ? '재무제표 전환 중' : '보고서와 원문 근거 연결 중'}</span>
			</div>
		{/if}

		<div class="report-grid">
			{#each view.questions as section}
				<QuestionSection {section} onOpenEvidence={openEvidence} onSelectRow={selectTableRow} />
			{/each}

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
	{/if}
</main>

<style>
	.company-page {
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
		max-width: 1480px;
		margin: 12px auto 0;
	}
	.report-grid > :global(.question-section),
	.report-grid > :global(.statement),
	.statement-band {
		grid-column: 1 / -1;
	}
	.statement-band {
		border: 1px solid #1e2433;
		border-radius: 8px;
		background: rgba(8, 13, 23, 0.96);
		padding: 16px;
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
