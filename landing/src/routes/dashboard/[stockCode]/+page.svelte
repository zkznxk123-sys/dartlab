<script lang="ts">
	import { base } from '$app/paths';
	import type { PageData } from './$types';

	let { data }: { data: PageData } = $props();

	const sections = $derived(data.dashboard?.sections || []);
	const node = $derived(data.node);
	const industry = $derived(data.industry);

	function fmtRev(v: number | null | undefined): string {
		if (v == null) return '-';
		if (v >= 1e12) return `${(v / 1e12).toFixed(1)}조`;
		if (v >= 1e8) return `${Math.round(v / 1e8).toLocaleString()}억`;
		return v.toLocaleString();
	}

	function fmtPct(v: number | null | undefined): string {
		if (v == null) return '-';
		return `${v.toFixed(1)}%`;
	}
</script>

<svelte:head>
	<title>{data.dashboard?.corpName || data.stockCode} 대시보드 · dartlab</title>
	<meta name="description" content="{data.dashboard?.corpName} 회사 종합 대시보드 — 스코어·재무·리스크·가치평가·매크로·AI논제" />
</svelte:head>

<div class="dashboard-page">
	<!-- 좌측 sticky: 회사 컨텍스트 -->
	<aside class="sidebar">
		<a class="back-link" href="{base}/map?focus={data.stockCode}">
			<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
				<path d="M19 12H5M12 19l-7-7 7-7" />
			</svg>
			<span>산업지도</span>
		</a>

		<header class="corp-header">
			<h1>{data.dashboard?.corpName || data.stockCode}</h1>
			<div class="corp-code">{data.stockCode}</div>
			{#if industry}
				<div class="industry-pill" style:--ind-color={industry.color || '#fbbf24'}>
					<span class="pill-dot"></span>
					{industry.name}
				</div>
			{/if}
		</header>

		{#if node}
			<div class="key-stats">
				{#if node.revenue}
					<div class="stat">
						<span class="stat-label">매출</span>
						<span class="stat-value">{fmtRev(node.revenue)}</span>
					</div>
				{/if}
				{#if node.roe != null}
					<div class="stat">
						<span class="stat-label">ROE</span>
						<span class="stat-value" class:positive={node.roe > 0} class:negative={node.roe < 0}>
							{fmtPct(node.roe)}
						</span>
					</div>
				{/if}
				{#if node.opMargin != null}
					<div class="stat">
						<span class="stat-label">영업이익률</span>
						<span class="stat-value" class:positive={node.opMargin > 0} class:negative={node.opMargin < 0}>
							{fmtPct(node.opMargin)}
						</span>
					</div>
				{/if}
				{#if node.debtRatio != null}
					<div class="stat">
						<span class="stat-label">부채비율</span>
						<span class="stat-value">{fmtPct(node.debtRatio)}</span>
					</div>
				{/if}
				{#if node.industryRank}
					<div class="stat">
						<span class="stat-label">업종 순위</span>
						<span class="stat-value">{node.industryRank}위 / {node.industryPeerCount}사</span>
					</div>
				{/if}
			</div>
		{/if}

		<nav class="section-nav">
			{#each sections as sec, i}
				<a href="#sec-{i}" class="nav-item">
					<span class="nav-index">{String(i + 1).padStart(2, '0')}</span>
					<span class="nav-name">{sec.title?.split('--')[0]?.trim() || sec.title || '섹션'}</span>
				</a>
			{/each}
		</nav>

		<footer class="sidebar-footer">
			<a href="{base}/" class="footer-link">dartlab.io</a>
		</footer>
	</aside>

	<!-- 우측 메인: 섹션들 -->
	<main class="main">
		<div class="hero">
			<div class="kicker">DASHBOARD</div>
			<h2>한 페이지 회사 스냅샷</h2>
			<p class="hero-sub">
				scan 13축 · macro 11축 · credit 20등급 · analysis 140+ calc를
				한 화면에 집약한 구조화 리포트.
				<a href="{base}/blog/?q={data.dashboard?.corpName || ''}">블로그 심층 분석 →</a>
			</p>
		</div>

		{#each sections as sec, i}
			<section class="dash-section" id="sec-{i}">
				<header class="sec-header">
					<span class="sec-index">{String(i + 1).padStart(2, '0')}</span>
					<h3>{sec.title?.split('--')[0]?.trim() || sec.title || '섹션'}</h3>
					{#if sec.title?.includes('--')}
						<p class="sec-subtitle">{sec.title.split('--')[1]?.trim()}</p>
					{/if}
				</header>

				{#if sec.helper}
					<p class="sec-helper">{sec.helper}</p>
				{/if}

				{#if sec.summary}
					<blockquote class="sec-summary">
						{sec.summary}
					</blockquote>
				{/if}

				<div class="sec-blocks">
					{#if sec.blocks && sec.blocks.length > 0}
						{#each sec.blocks as block}
							<div class="block block-{block.type || 'unknown'}">
								{#if block.title}<h4 class="block-title">{block.title}</h4>{/if}
								{#if block.text}
									<p class="block-text">{block.text}</p>
								{/if}
								{#if block.rows}
									<table class="block-table">
										{#each block.rows as row}
											<tr>
												{#each row as cell}
													<td>{cell}</td>
												{/each}
											</tr>
										{/each}
									</table>
								{/if}
								{#if block.label && block.value !== undefined}
									<div class="metric-row">
										<span class="metric-label">{block.label}</span>
										<span class="metric-value">{block.value}</span>
									</div>
								{/if}
							</div>
						{/each}
					{:else}
						<div class="sec-empty">
							이 섹션은 현재 표시할 블록이 없습니다.
							<br />
							<a href="{base}/map?focus={data.stockCode}">산업지도에서 확인 →</a>
						</div>
					{/if}
				</div>

				{#if sec.aiOpinion}
					<div class="sec-ai">
						<span class="ai-label">AI 코멘트</span>
						<p>{sec.aiOpinion}</p>
					</div>
				{/if}
			</section>
		{/each}

		<footer class="disclaimer">
			<p>
				dartlab은 공시·재무 데이터를 시각화합니다. 투자 자문이 아닙니다.
				<br />
				원본 DART 공시 및 증권사 리포트와 교차 검증하세요.
			</p>
		</footer>
	</main>
</div>

<style>
	.dashboard-page {
		display: grid;
		grid-template-columns: 320px 1fr;
		min-height: 100dvh;
		background: var(--color-dl-bg-dark);
		color: var(--color-dl-text);
	}

	/* ── 사이드바 ── */
	.sidebar {
		position: sticky;
		top: 0;
		align-self: start;
		height: 100dvh;
		padding: 24px 24px 24px 28px;
		border-right: 1px solid var(--color-dl-border);
		background: linear-gradient(180deg, rgba(15, 18, 25, 0.8) 0%, rgba(5, 8, 17, 0.95) 100%);
		display: flex;
		flex-direction: column;
		gap: 20px;
		overflow-y: auto;
	}

	.back-link {
		display: inline-flex;
		align-items: center;
		gap: 6px;
		font-family: var(--font-mono);
		font-size: 11px;
		letter-spacing: 0.06em;
		text-transform: uppercase;
		color: var(--color-dl-text-dim);
		text-decoration: none;
		padding: 6px 10px;
		border: 1px solid var(--color-dl-border);
		border-radius: 6px;
		width: fit-content;
		transition: all 180ms ease;
	}
	.back-link:hover {
		color: var(--color-dl-primary-light);
		border-color: var(--color-dl-primary);
		background: rgba(234, 70, 71, 0.08);
	}

	.corp-header h1 {
		margin: 0;
		font-size: 26px;
		font-weight: 800;
		letter-spacing: -0.02em;
		line-height: 1.15;
	}
	.corp-code {
		margin-top: 4px;
		font-family: var(--font-mono);
		font-size: 12px;
		color: var(--color-dl-text-dim);
		letter-spacing: 0.05em;
	}
	.industry-pill {
		display: inline-flex;
		align-items: center;
		gap: 6px;
		margin-top: 12px;
		padding: 4px 10px;
		border-radius: 999px;
		background: color-mix(in srgb, var(--ind-color) 15%, transparent);
		border: 1px solid color-mix(in srgb, var(--ind-color) 35%, transparent);
		font-size: 11px;
		font-weight: 600;
		color: var(--ind-color);
	}
	.pill-dot {
		width: 6px;
		height: 6px;
		border-radius: 50%;
		background: currentColor;
	}

	.key-stats {
		display: flex;
		flex-direction: column;
		gap: 0;
		border-top: 1px solid var(--color-dl-border);
		border-bottom: 1px solid var(--color-dl-border);
		padding: 4px 0;
	}
	.stat {
		display: flex;
		justify-content: space-between;
		align-items: baseline;
		padding: 8px 0;
		border-bottom: 1px dashed rgba(30, 36, 51, 0.5);
	}
	.stat:last-child {
		border-bottom: none;
	}
	.stat-label {
		font-size: 11px;
		color: var(--color-dl-text-dim);
		font-family: var(--font-mono);
		letter-spacing: 0.04em;
		text-transform: uppercase;
	}
	.stat-value {
		font-family: var(--font-mono);
		font-size: 14px;
		font-weight: 700;
		color: var(--color-dl-text);
	}
	.stat-value.positive { color: var(--color-dl-success); }
	.stat-value.negative { color: var(--color-dl-danger); }

	.section-nav {
		display: flex;
		flex-direction: column;
		gap: 2px;
	}
	.nav-item {
		display: flex;
		align-items: center;
		gap: 12px;
		padding: 8px 10px;
		color: var(--color-dl-text-muted);
		text-decoration: none;
		font-size: 13px;
		border-radius: 6px;
		transition: all 150ms ease;
	}
	.nav-item:hover {
		color: var(--color-dl-text);
		background: rgba(255, 255, 255, 0.04);
	}
	.nav-index {
		font-family: var(--font-mono);
		font-size: 10px;
		color: var(--color-dl-text-dim);
		letter-spacing: 0.05em;
	}

	.sidebar-footer {
		margin-top: auto;
		padding-top: 16px;
		border-top: 1px solid var(--color-dl-border);
		font-size: 11px;
		color: var(--color-dl-text-dim);
	}
	.footer-link {
		color: var(--color-dl-text-dim);
		text-decoration: none;
	}
	.footer-link:hover {
		color: var(--color-dl-primary-light);
	}

	/* ── 메인 ── */
	.main {
		padding: 48px 56px;
		max-width: 1100px;
	}

	.hero {
		margin-bottom: 56px;
		padding-bottom: 32px;
		border-bottom: 1px solid var(--color-dl-border);
	}
	.kicker {
		font-family: var(--font-mono);
		font-size: 11px;
		letter-spacing: 0.18em;
		color: var(--color-dl-primary);
		font-weight: 700;
		margin-bottom: 14px;
	}
	.hero h2 {
		margin: 0;
		font-size: 38px;
		font-weight: 800;
		letter-spacing: -0.02em;
		line-height: 1.15;
	}
	.hero-sub {
		margin-top: 14px;
		font-size: 14px;
		line-height: 1.7;
		color: var(--color-dl-text-muted);
		max-width: 680px;
	}
	.hero-sub a {
		color: var(--color-dl-primary-light);
		text-decoration: none;
		font-weight: 500;
	}

	.dash-section {
		margin-bottom: 64px;
		scroll-margin-top: 24px;
	}
	.sec-header {
		display: grid;
		grid-template-columns: auto 1fr;
		align-items: baseline;
		gap: 16px;
		margin-bottom: 20px;
		padding-bottom: 16px;
		border-bottom: 1px solid var(--color-dl-border);
	}
	.sec-index {
		font-family: var(--font-mono);
		font-size: 13px;
		font-weight: 700;
		color: var(--color-dl-primary);
		letter-spacing: 0.05em;
	}
	.sec-header h3 {
		margin: 0;
		grid-column: 2;
		font-size: 22px;
		font-weight: 700;
		letter-spacing: -0.01em;
	}
	.sec-subtitle {
		grid-column: 2;
		margin: 6px 0 0;
		font-size: 13px;
		color: var(--color-dl-text-dim);
		font-style: italic;
	}
	.sec-helper {
		margin: 0 0 16px 0;
		padding: 12px 14px;
		background: rgba(255, 255, 255, 0.02);
		border-left: 2px solid var(--color-dl-border);
		font-size: 13px;
		color: var(--color-dl-text-muted);
		line-height: 1.6;
	}
	.sec-summary {
		margin: 0 0 20px 0;
		padding: 16px 18px;
		background: rgba(234, 70, 71, 0.04);
		border-left: 3px solid var(--color-dl-primary);
		color: var(--color-dl-text);
		font-size: 14px;
		line-height: 1.7;
	}
	.sec-blocks {
		display: flex;
		flex-direction: column;
		gap: 16px;
	}

	.block {
		padding: 16px 18px;
		background: rgba(255, 255, 255, 0.02);
		border: 1px solid rgba(255, 255, 255, 0.04);
		border-radius: 8px;
	}
	.block-title {
		margin: 0 0 10px 0;
		font-size: 14px;
		font-weight: 700;
		color: var(--color-dl-text);
	}
	.block-text {
		margin: 0;
		color: var(--color-dl-text-muted);
		font-size: 14px;
		line-height: 1.7;
	}
	.block-table {
		width: 100%;
		border-collapse: collapse;
		font-size: 13px;
	}
	.block-table td {
		padding: 6px 10px;
		border-bottom: 1px dashed rgba(30, 36, 51, 0.5);
		color: var(--color-dl-text-muted);
	}
	.block-table td:first-child {
		color: var(--color-dl-text-dim);
		font-family: var(--font-mono);
		font-size: 11px;
	}

	.metric-row {
		display: flex;
		justify-content: space-between;
	}
	.metric-label {
		color: var(--color-dl-text-dim);
		font-size: 12px;
	}
	.metric-value {
		font-family: var(--font-mono);
		font-weight: 700;
	}

	.sec-empty {
		padding: 24px;
		text-align: center;
		color: var(--color-dl-text-dim);
		font-size: 13px;
		background: rgba(255, 255, 255, 0.02);
		border-radius: 8px;
	}
	.sec-empty a {
		color: var(--color-dl-primary-light);
		text-decoration: none;
	}

	.sec-ai {
		margin-top: 18px;
		padding: 14px 16px;
		background: rgba(96, 165, 250, 0.04);
		border-left: 2px solid var(--color-dl-blue, #60a5fa);
		border-radius: 0 8px 8px 0;
	}
	.ai-label {
		display: block;
		font-size: 10px;
		letter-spacing: 0.12em;
		text-transform: uppercase;
		color: var(--color-dl-blue, #60a5fa);
		font-weight: 700;
		margin-bottom: 6px;
	}
	.sec-ai p {
		margin: 0;
		font-size: 13px;
		line-height: 1.6;
		color: var(--color-dl-text-muted);
	}

	.disclaimer {
		margin-top: 80px;
		padding-top: 24px;
		border-top: 1px solid var(--color-dl-border);
		font-size: 11px;
		color: var(--color-dl-text-dim);
		line-height: 1.8;
	}

	@media (max-width: 900px) {
		.dashboard-page {
			grid-template-columns: 1fr;
		}
		.sidebar {
			position: static;
			height: auto;
			border-right: none;
			border-bottom: 1px solid var(--color-dl-border);
		}
		.main {
			padding: 32px 20px;
		}
	}
</style>
