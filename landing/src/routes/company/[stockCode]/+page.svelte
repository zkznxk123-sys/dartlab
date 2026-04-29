<script lang="ts">
	import { onMount, tick } from 'svelte';
	import { base } from '$app/paths';
	import Header from '$lib/components/sections/Header.svelte';
	import FreshnessBadge from '$lib/components/industry/FreshnessBadge.svelte';
	import EvidencePanel from '$lib/components/company/EvidencePanel.svelte';
	import StatementSection from '$lib/components/company/StatementSection.svelte';
	import StorySection from '$lib/components/company/StorySection.svelte';
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
		type StatementDashboard,
		type StatementFreq,
		type StatementGroupRow,
		type StatementKey
	} from '$lib/browser/companyLive';
	import {
		buildStoryDashboardView,
		loadStoryManifest,
		type StoryManifest
	} from '$lib/browser/storyDashboard';
	import { fmtKrw, fmtPrice } from '$lib/format/krw';
	import { fmtMul, fmtPct } from '$lib/format/pct';
	import type { BrowserTable } from '$lib/browser/types';
	import type { PageData } from './$types';

	let { data }: { data: PageData } = $props();

	const STATEMENTS: StatementKey[] = ['IS', 'BS', 'CF'];
	const FREQS: StatementFreq[] = ['Y', 'Q'];

	let manifest = $state<StoryManifest | null>(null);
	let company = $state<LiveCompanyBundle | null>(null);
	let statements = $state<Record<StatementKey, LiveStatementSlot> | null>(null);
	let frequency = $state<StatementFreq>('Y');
	let loading = $state(true);
	let errorMessage = $state('');
	let statementLoading = $state<Record<StatementKey, boolean>>({ IS: false, BS: false, CF: false });
	let changes = $state<LiveCompanyChange[]>([]);
	let reportFacts = $state<LiveCompanyReportFact[]>([]);
	let docs = $state<LiveCompanyDocExcerpt[]>([]);
	let selectedRow = $state<StatementGroupRow | null>(null);
	let selectedPeriods = $state<string[]>([]);
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
		try {
			const [nextManifest, bundle] = await Promise.all([
				loadStoryManifest(fetch),
				loadLiveCompany(data.stockCode)
			]);
			manifest = nextManifest;
			company = bundle;
			statements = bundle.statements;
			loading = false;
			await Promise.all(STATEMENTS.map((topic) => hydrateStatement(topic, 'Y')));
			void loadEvidence();
			await tick();
			observeSections();
		} catch (err) {
			errorMessage = err instanceof Error ? err.message : String(err);
			loading = false;
		}
	}

	async function loadEvidence() {
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

	async function setFrequency(next: StatementFreq) {
		frequency = next;
		selectedRow = null;
		selectedPeriods = [];
		await Promise.all(STATEMENTS.map((topic) => hydrateStatement(topic, next)));
	}

	async function hydrateStatement(topic: StatementKey, freq: StatementFreq) {
		const slot = statements?.[topic];
		const hasAnnual = freq === 'Y' && slot?.annual?.source?.includes('dart/finance');
		const hasQuarterly = freq === 'Q' && slot?.quarterly;
		if (hasAnnual || hasQuarterly) return;

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
		return frequency === 'Y' ? (slot?.annual ?? null) : (slot?.quarterly ?? null);
	}

	function selectAccount(row: StatementGroupRow, dashboard: StatementDashboard) {
		selectedRow = row;
		selectedPeriods = dashboard.periods;
	}

	let ego = $derived(company?.companyMeta?.ego ?? null);
	let title = $derived(ego?.corpName ?? data.stockCode);
	let price = $derived(company?.price ?? null);
	let summary = $derived(company?.summary ?? null);
	let dashboards = $derived({
		IS: buildStatementDashboard('IS', tableFor('IS')),
		BS: buildStatementDashboard('BS', tableFor('BS')),
		CF: buildStatementDashboard('CF', tableFor('CF'))
	});
	let storyView = $derived(
		buildStoryDashboardView({ manifest, company, dashboards, facts: reportFacts, docs, changes })
	);
	let evidence = $derived(
		buildEvidenceForAccount(selectedRow, selectedPeriods, reportFacts, docs, changes)
	);
	let debtRatioDisplay = $derived(
		dashboards.BS.metrics.find((metric) => metric.key === 'debtRatio')?.display ?? fmtPct(summary?.debtRatio)
	);
	let tocItems = $derived([
		{ id: 'summary', label: '요약' },
		...storyView.sections.map((section) => ({ id: section.id, label: section.key })),
		{ id: 'income', label: 'IS' },
		{ id: 'balance', label: 'BS' },
		{ id: 'cashflow', label: 'CF' },
		{ id: 'report', label: '근거' },
		{ id: 'docs', label: '원문' }
	]);
</script>

<svelte:head>
	<title>{title} Company · dartlab</title>
	<meta
		name="description"
		content="{title} story 기반 재무제표, 정기보고서, 사업보고서 원문 대시보드."
	/>
</svelte:head>

<Header context="landing" />

<main class="company-page">
	<TocRail activeSection={activeSection} items={tocItems} />

	<section class="hero" id="summary" data-section>
		<div class="hero-copy">
			<div class="eyebrow">Company · Story Dashboard</div>
			<h1>{title}</h1>
			<p>{storyView.template} · {storyView.templateDescription}</p>
			<div class="tags">
				<span>{data.stockCode}</span>
				{#if ego?.market}<span>{ego.market}</span>{/if}
				{#if ego?.industry}<span>{ego.industry}</span>{/if}
				{#if ego?.stage}<span>{ego.stage}</span>{/if}
				{#if ego?.role}<span>{ego.role}</span>{/if}
			</div>
		</div>
		<div class="hero-actions">
			{#if company?.meta?.dataAsOf}
				<FreshnessBadge dataAsOf={company.meta.dataAsOf} variant="compact" />
			{/if}
			<a href="{base}/map?focus={data.stockCode}">산업지도에서 보기</a>
		</div>
	</section>

	{#if loading}
		<section class="state">
			<div class="spinner"></div>
			<p>story 구조와 회사 데이터를 여는 중</p>
		</section>
		<div class="layout loading-layout">
			<div class="main-column">
				{#each storyView.sections as section}
					<section class="story-skeleton" id={section.id} data-section>
						<div class="eyebrow">{section.key}</div>
						<h2>{section.title}</h2>
						<p>{section.summary}</p>
						<div class="skeleton-grid">
							<span></span>
							<span></span>
							<span></span>
						</div>
					</section>
				{/each}
				<section class="story-skeleton" id="income" data-section>
					<div class="eyebrow">IS</div>
					<h2>손익계산서</h2>
					<p>매출에서 영업이익과 순이익까지 이어지는 수익 구조를 준비합니다.</p>
				</section>
				<section class="story-skeleton" id="balance" data-section>
					<div class="eyebrow">BS</div>
					<h2>재무상태표</h2>
					<p>자산, 부채, 자본의 균형과 레버리지 구조를 준비합니다.</p>
				</section>
				<section class="story-skeleton" id="cashflow" data-section>
					<div class="eyebrow">CF</div>
					<h2>현금흐름표</h2>
					<p>영업현금, 투자현금, 재무현금의 연결을 준비합니다.</p>
				</section>
				<section class="story-skeleton" id="report" data-section>
					<div class="eyebrow">정기보고서</div>
					<h2>구조화 팩트</h2>
					<p>배당, 사채, 감사의견, 지배구조 팩트를 준비합니다.</p>
				</section>
				<section class="story-skeleton" id="docs" data-section>
					<div class="eyebrow">원문</div>
					<h2>사업보고서 문장</h2>
					<p>사업, 위험, 주석 원문 발췌를 준비합니다.</p>
				</section>
			</div>
		</div>
	{:else if errorMessage}
		<section class="state error">
			<h2>로드 실패</h2>
			<p>{errorMessage}</p>
			<button type="button" onclick={boot}>다시 시도</button>
		</section>
	{:else if company}
		<section class="snapshot">
			<div class="metric major">
				<span>매출</span>
				<strong>{fmtKrw(summary?.revenue)}</strong>
				<small>{summary?.year ?? 'latest'}</small>
			</div>
			<div class="metric">
				<span>영업이익</span>
				<strong>{fmtKrw(summary?.op)}</strong>
				<small>IS</small>
			</div>
			<div class="metric">
				<span>순이익</span>
				<strong>{fmtKrw(summary?.net)}</strong>
				<small>IS</small>
			</div>
			<div class="metric">
				<span>영업이익률</span>
				<strong>{fmtPct(summary?.opMargin)}</strong>
				<small>수익성</small>
			</div>
			<div class="metric">
				<span>부채비율</span>
				<strong>{debtRatioDisplay}</strong>
				<small>BS</small>
			</div>
			<div class="metric">
				<span>현재가</span>
				<strong>{fmtPrice(price?.currentPrice)}</strong>
				<small>{price?.snapshotAt ?? '가격 스냅샷'}</small>
			</div>
			<div class="metric">
				<span>PER / PBR</span>
				<strong>{fmtMul(price?.per)} · {fmtMul(price?.pbr)}</strong>
				<small>시장 배수</small>
			</div>
		</section>

		<section class="focus-strip">
			{#each storyView.focusQuestions as question}
				<div>{question}</div>
			{/each}
		</section>

		<div class="layout">
			<div class="main-column">
				{#each storyView.sections as section}
					<StorySection {section} />
				{/each}

				<section class="controls-band">
					<div>
						<strong>재무제표 근거</strong>
						<span>story 판단을 IS/BS/CF 원표와 바로 대조합니다.</span>
					</div>
					<div class="segment" aria-label="기간 단위">
						{#each FREQS as freq}
							<button type="button" class:active={frequency === freq} onclick={() => setFrequency(freq)}>
								{freq === 'Y' ? '연간' : '분기'}
							</button>
						{/each}
					</div>
				</section>

				{#each STATEMENTS as topic}
					<StatementSection
						dashboard={dashboards[topic]}
						selectedKey={selectedRow?.key}
						onSelect={(row) => selectAccount(row, dashboards[topic])}
					/>
				{/each}

				<section class="evidence-section" id="report" data-section>
					<header>
						<div>
							<div class="eyebrow">정기보고서 근거</div>
							<h2>정기보고서 팩트</h2>
							<p>배당, 사채, 감사의견, 주주, 임원 등 구조화된 report 데이터를 story 판단 근거로 붙입니다.</p>
						</div>
					</header>
					<div class="fact-grid">
						{#each reportFacts.slice(0, 12) as fact}
							<article>
								<span>{fact.label}</span>
								<strong>{fact.value}</strong>
								<p>{fact.detail || '세부 값 없음'}</p>
							</article>
						{:else}
							<p>정기보고서 팩트를 불러오는 중입니다.</p>
						{/each}
					</div>
				</section>

				<section class="evidence-section" id="docs" data-section>
					<header>
						<div>
							<div class="eyebrow">사업보고서 원문</div>
							<h2>사업보고서 원문</h2>
							<p>사업, 제품, 매출, 위험, 재무 주석을 story 판단 근거와 연결합니다.</p>
						</div>
					</header>
					<div class="doc-list">
						{#each docs as doc}
							<article>
								<strong>{doc.title}</strong>
								<span>{doc.year ?? '연도 없음'} · {doc.reportType ?? '보고서'}</span>
								<p>{doc.excerpt}</p>
							</article>
						{:else}
							<p>원문 발췌를 불러오는 중입니다.</p>
						{/each}
					</div>
				</section>
			</div>

			<EvidencePanel {evidence} facts={reportFacts} {docs} {changes} />
		</div>
	{/if}
</main>

<style>
	.company-page {
		min-height: 100vh;
		background:
			radial-gradient(circle at 18% 0%, rgba(234, 70, 71, 0.22), transparent 28%),
			linear-gradient(180deg, #0a0710 0%, #050811 34%, #030509 100%);
		color: #f8fafc;
		padding: 76px 28px 80px;
	}
	.hero,
	.snapshot,
	.focus-strip,
	.controls-band,
	.layout {
		max-width: 1280px;
		margin: 0 auto;
	}
	.hero {
		display: flex;
		justify-content: space-between;
		gap: 24px;
		align-items: end;
		min-height: 180px;
		border-bottom: 1px solid #1e2433;
		padding-bottom: 22px;
	}
	.eyebrow {
		color: #fb923c;
		font-size: 12px;
		font-weight: 900;
		letter-spacing: 0.08em;
		text-transform: uppercase;
	}
	h1,
	h2,
	p {
		margin: 0;
	}
	h1 {
		margin-top: 10px;
		font-size: clamp(48px, 7vw, 96px);
		font-weight: 700;
		letter-spacing: 0;
		line-height: 0.96;
	}
	.hero-copy p {
		margin-top: 12px;
		color: #cbd5e1;
		font-size: 15px;
	}
	.tags {
		display: flex;
		flex-wrap: wrap;
		gap: 8px;
		margin-top: 18px;
	}
	.tags span,
	.hero-actions a {
		border: 1px solid #263145;
		border-radius: 6px;
		background: rgba(7, 12, 21, 0.72);
		color: #bfdbfe;
		font-size: 12px;
		padding: 8px 10px;
		text-decoration: none;
	}
	.hero-actions {
		display: flex;
		flex-wrap: wrap;
		justify-content: end;
		gap: 8px;
	}
	.snapshot {
		display: grid;
		grid-template-columns: repeat(7, minmax(0, 1fr));
		gap: 8px;
		margin-top: 18px;
	}
	.metric {
		min-height: 102px;
		border: 1px solid #1e2433;
		border-radius: 8px;
		background: #070c15;
		padding: 14px;
	}
	.metric.major {
		border-color: rgba(234, 70, 71, 0.72);
	}
	.metric span,
	.metric small {
		display: block;
		color: #94a3b8;
		font-size: 12px;
	}
	.metric strong {
		display: block;
		margin-top: 12px;
		font-size: 23px;
	}
	.metric small {
		margin-top: 8px;
	}
	.focus-strip {
		display: grid;
		grid-template-columns: repeat(5, minmax(0, 1fr));
		gap: 8px;
		margin-top: 8px;
	}
	.focus-strip div {
		border: 1px solid #172033;
		border-left: 2px solid #ea4647;
		border-radius: 6px;
		background: rgba(7, 12, 21, 0.82);
		color: #cbd5e1;
		font-size: 12px;
		line-height: 1.45;
		padding: 10px;
	}
	.controls-band {
		display: flex;
		justify-content: space-between;
		gap: 16px;
		align-items: center;
		border: 1px solid #1e2433;
		border-radius: 8px;
		background: #070c15;
		padding: 12px 14px;
	}
	.controls-band strong,
	.controls-band span {
		display: block;
	}
	.controls-band span {
		margin-top: 3px;
		color: #94a3b8;
		font-size: 12px;
	}
	.segment {
		display: flex;
		border: 1px solid #263145;
		border-radius: 7px;
		overflow: hidden;
	}
	.segment button {
		border: 0;
		background: #0b111e;
		color: #94a3b8;
		cursor: pointer;
		font: inherit;
		font-size: 12px;
		padding: 8px 12px;
	}
	.segment button.active {
		background: #ea4647;
		color: white;
	}
	.layout {
		display: grid;
		grid-template-columns: minmax(0, 1fr) 330px;
		gap: 14px;
		margin-top: 14px;
	}
	.main-column {
		display: grid;
		gap: 12px;
	}
	.loading-layout {
		grid-template-columns: minmax(0, 1fr);
	}
	.story-skeleton {
		border: 1px solid #1e2433;
		border-radius: 8px;
		background: rgba(8, 13, 23, 0.72);
		padding: 16px;
	}
	.story-skeleton h2 {
		margin-top: 6px;
		font-size: 24px;
		letter-spacing: 0;
	}
	.story-skeleton p {
		margin-top: 7px;
		color: #94a3b8;
		font-size: 13px;
		line-height: 1.45;
	}
	.skeleton-grid {
		display: grid;
		grid-template-columns: repeat(3, minmax(0, 1fr));
		gap: 8px;
		margin-top: 14px;
	}
	.skeleton-grid span {
		display: block;
		height: 54px;
		border: 1px solid #172033;
		border-radius: 7px;
		background: linear-gradient(90deg, #070c15, #111827, #070c15);
	}
	.evidence-section {
		border: 1px solid #1e2433;
		border-radius: 8px;
		background: rgba(8, 13, 23, 0.9);
		padding: 16px;
	}
	.evidence-section h2 {
		margin-top: 5px;
	}
	.evidence-section p {
		margin-top: 6px;
		color: #94a3b8;
		font-size: 13px;
		line-height: 1.5;
	}
	.fact-grid {
		display: grid;
		grid-template-columns: repeat(3, minmax(0, 1fr));
		gap: 8px;
		margin-top: 12px;
	}
	.fact-grid article,
	.doc-list article {
		border: 1px solid #172033;
		border-radius: 7px;
		background: #070c15;
		padding: 12px;
	}
	.fact-grid span,
	.doc-list span {
		color: #94a3b8;
		font-size: 12px;
	}
	.fact-grid strong,
	.doc-list strong {
		display: block;
		margin-top: 5px;
	}
	.doc-list {
		display: grid;
		gap: 8px;
		margin-top: 12px;
	}
	.state {
		display: grid;
		place-items: center;
		gap: 12px;
		min-height: 360px;
	}
	.spinner {
		width: 28px;
		height: 28px;
		border: 2px solid #263145;
		border-top-color: #ea4647;
		border-radius: 50%;
		animation: spin 0.8s linear infinite;
	}
	@keyframes spin {
		to {
			transform: rotate(360deg);
		}
	}
	@media (max-width: 1180px) {
		.snapshot,
		.focus-strip {
			grid-template-columns: repeat(2, minmax(0, 1fr));
		}
		.layout {
			grid-template-columns: 1fr;
		}
	}
	@media (max-width: 720px) {
		.company-page {
			padding: 68px 12px 48px;
		}
		.hero,
		.controls-band {
			flex-direction: column;
			align-items: stretch;
		}
		.hero-actions {
			justify-content: start;
		}
		.snapshot,
		.focus-strip,
		.fact-grid {
			grid-template-columns: 1fr;
		}
	}
</style>
