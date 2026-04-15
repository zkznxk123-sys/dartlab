<script lang="ts">
	import { base } from '$app/paths';
	import { brand } from '$lib/brand';
	import Sparkline from './Sparkline.svelte';

	interface Props {
		// ecosystem.json 노드 (기본 정보 + scan 지표 4종)
		node: any;
		// companies/{code}.json (있으면 풍부한 데이터, 없으면 null)
		detail: any | null;
		loading?: boolean;
		// 비교에 추가 콜백
		onAddCompare?: (stockCode: string) => void;
		// 닫기
		onClose?: () => void;
		compareDisabled?: boolean;
	}

	let { node, detail, loading = false, onAddCompare, onClose, compareDisabled = false }: Props = $props();

	let aiExpanded = $state(false);

	function fmtKor(v: number | null | undefined, suffix = '원'): string {
		if (v === null || v === undefined || isNaN(v)) return '-';
		const abs = Math.abs(v);
		if (abs >= 1e12) return `${(v / 1e12).toFixed(1)}조${suffix}`;
		if (abs >= 1e8) return `${Math.round(v / 1e8).toLocaleString()}억${suffix}`;
		return `${v.toLocaleString()}${suffix}`;
	}

	function pct(v: number | null | undefined, digits = 1): string {
		if (v === null || v === undefined || isNaN(v)) return '-';
		return `${v.toFixed(digits)}%`;
	}

	// 5년 시계열 (있으면)
	let financials = $derived(detail?.financials5y || []);
	let years = $derived(financials.map((f: any) => String(f.year ?? '').slice(-2)));
	let salesSeries = $derived(financials.map((f: any) => f.sales ?? null));
	let opSeries = $derived(financials.map((f: any) => f.operating_profit ?? null));
	let netSeries = $derived(financials.map((f: any) => f.net_profit ?? null));
	let latest = $derived(financials.length ? financials[financials.length - 1] : null);

	// peer 분위 (industryRank 가 있으면 → percentile)
	let peerPct = $derived.by(() => {
		if (!node?.industryRank || !node?.industryPeerCount) return null;
		const rank = node.industryRank;
		const peer = node.industryPeerCount;
		// rank 1 = top → percentile 100, rank N = bottom → 0
		return Math.round(((peer - rank) / (peer - 1 || 1)) * 100);
	});

	let supplyInsights = $derived(detail?.supplyInsights || {});
	let aiInsight = $derived(detail?.aiInsight || null);
	let blogPosts = $derived(detail?.blogPosts || []);

	// 정밀 거래 Top 5 (amount 큰 순)
	let topPreciseEdges = $derived.by(() => {
		const all: any[] = [];
		for (const s of detail?.suppliers || []) {
			if (s.amount && s.amount > 0) all.push({ ...s, kind: '공급' });
		}
		for (const c of detail?.customers || []) {
			if (c.amount && c.amount > 0) all.push({ ...c, kind: '고객' });
		}
		all.sort((a, b) => (b.amount || 0) - (a.amount || 0));
		return all.slice(0, 5);
	});

	function colorByMetric(value: number | null, kind: 'roe' | 'op' | 'debt' | 'cagr'): string {
		if (value === null || value === undefined) return '#64748b';
		if (kind === 'debt') {
			if (value >= 200) return '#ef4444';
			if (value >= 100) return '#f59e0b';
			return '#10b981';
		}
		// roe/op/cagr: positive = good
		const thresholds = { roe: [0, 10, 20], op: [0, 10, 20], cagr: [0, 10, 20] }[kind];
		if (value >= thresholds[2]) return '#10b981';
		if (value >= thresholds[1]) return '#84cc16';
		if (value >= thresholds[0]) return '#f59e0b';
		return '#ef4444';
	}

	function hhiBucket(hhi: number | null | undefined): { label: string; color: string; pct: number } {
		if (hhi === null || hhi === undefined) return { label: '-', color: '#64748b', pct: 0 };
		// HHI 0~10000. 1500 미만 분산, 2500+ 집중
		if (hhi >= 2500) return { label: '집중', color: '#ef4444', pct: Math.min(100, hhi / 100) };
		if (hhi >= 1500) return { label: '주의', color: '#f59e0b', pct: hhi / 100 };
		return { label: '분산', color: '#10b981', pct: hhi / 100 };
	}

	let hhiInfo = $derived(hhiBucket(supplyInsights?.hhi));

	function issueUrl(): string {
		const title = encodeURIComponent(`[map] ${node?.label || ''} (${node?.id || ''}) 분류 신고`);
		const body = encodeURIComponent(
			`회사: ${node?.label || ''}\n종목코드: ${node?.id || ''}\n현재 분류: ${node?.industryName || ''} / ${node?.stageName || node?.stage || ''}\n\n문제:\n\n근거:\n`
		);
		return `${brand.repo}/issues/new?title=${title}&body=${body}&labels=industry-map`;
	}
</script>

<div class="card">
	<button class="close" onclick={() => onClose?.()} aria-label="닫기">✕</button>

	<!-- 1. Header -->
	<div class="head">
		<h2>{node.label}</h2>
		<p class="code">{node.id}</p>
		<div class="badges">
			<span class="badge industry" style:background="{node.color}20" style:color={node.color}>
				{node.industryName}
			</span>
			{#if node.stageName || node.stage}
				<span class="badge stage">{node.stageName || node.stage}</span>
			{/if}
			{#if node.role}<span class="badge role">{node.role}</span>{/if}
			{#if node.stream}<span class="badge stream">{node.stream}</span>{/if}
		</div>
	</div>

	{#if loading}
		<div class="loading">상세 데이터 로드 중…</div>
	{/if}

	<!-- 2. 재무 한눈에 -->
	{#if latest}
		<div class="section">
			<h3>재무 한눈에 <span class="year">{latest.year}년</span></h3>
			<div class="fin-grid">
				<div class="fin-cell">
					<div class="fin-k">매출</div>
					<div class="fin-v">{fmtKor(latest.sales)}</div>
				</div>
				<div class="fin-cell">
					<div class="fin-k">영업이익</div>
					<div class="fin-v" style:color={latest.operating_profit < 0 ? '#ef4444' : '#10b981'}>
						{fmtKor(latest.operating_profit)}
					</div>
				</div>
				<div class="fin-cell">
					<div class="fin-k">순이익</div>
					<div class="fin-v" style:color={latest.net_profit < 0 ? '#ef4444' : '#10b981'}>
						{fmtKor(latest.net_profit)}
					</div>
				</div>
				<div class="fin-cell">
					<div class="fin-k">총자산</div>
					<div class="fin-v">{fmtKor(latest.total_assets)}</div>
				</div>
			</div>
		</div>

		<!-- 3. 5년 sparkline -->
		<div class="section">
			<h3>5년 추이</h3>
			<Sparkline
				labels={years}
				series={[
					{ label: '매출', color: '#60a5fa', values: salesSeries },
					{ label: '영업이익', color: '#34d399', values: opSeries },
					{ label: '순이익', color: '#fbbf24', values: netSeries }
				]}
			/>
		</div>
	{:else if !loading}
		<!-- enriched JSON 없는 회사 (top500 외) — 노드 정보만 표시 -->
		{#if node.revenue}
			<div class="section">
				<h3>매출</h3>
				<div class="fin-cell">
					<div class="fin-v">{fmtKor(node.revenue)}</div>
				</div>
			</div>
		{/if}
	{/if}

	<!-- 4. scan 스코어 + peer 분위 -->
	{#if node.roe !== null || node.opMargin !== null || node.debtRatio !== null || node.revCagr !== null}
		<div class="section">
			<h3>
				재무 스코어
				{#if peerPct !== null}
					<span class="peer">산업 분위 {peerPct}%</span>
				{/if}
			</h3>
			<div class="scan-grid">
				{#if node.roe !== null && node.roe !== undefined}
					<div class="scan-row">
						<span class="scan-k">ROE</span>
						<span class="scan-v" style:color={colorByMetric(node.roe, 'roe')}>
							{pct(node.roe)}
						</span>
						{#if node.profGrade}<span class="scan-grade">{node.profGrade}</span>{/if}
					</div>
				{/if}
				{#if node.opMargin !== null && node.opMargin !== undefined}
					<div class="scan-row">
						<span class="scan-k">영업이익률</span>
						<span class="scan-v" style:color={colorByMetric(node.opMargin, 'op')}>
							{pct(node.opMargin)}
						</span>
					</div>
				{/if}
				{#if node.debtRatio !== null && node.debtRatio !== undefined}
					<div class="scan-row">
						<span class="scan-k">부채비율</span>
						<span class="scan-v" style:color={colorByMetric(node.debtRatio, 'debt')}>
							{pct(node.debtRatio, 0)}
						</span>
						{#if node.debtGrade}<span class="scan-grade">{node.debtGrade}</span>{/if}
					</div>
				{/if}
				{#if node.revCagr !== null && node.revCagr !== undefined}
					<div class="scan-row">
						<span class="scan-k">매출 CAGR</span>
						<span class="scan-v" style:color={colorByMetric(node.revCagr, 'cagr')}>
							{pct(node.revCagr)}
						</span>
						{#if node.growthGrade}<span class="scan-grade">{node.growthGrade}</span>{/if}
					</div>
				{/if}
			</div>
			{#if node.industryRank}
				<div class="rank-line">
					{node.industryName} 매출 순위 <strong>{node.industryRank}위</strong>
					/ {node.industryPeerCount}사
					{#if node.marketShare}· 점유율 {node.marketShare.toFixed(1)}%{/if}
				</div>
			{/if}
		</div>
	{/if}

	<!-- 5. 공급망 분석 -->
	{#if detail && supplyInsights && (supplyInsights.hhi !== undefined || supplyInsights.supplierCount)}
		<div class="section">
			<h3>공급망 구조</h3>

			<div class="hhi-card">
				<div class="hhi-head">
					<span class="hhi-label">공급 집중도</span>
					<span class="hhi-bucket" style:color={hhiInfo.color}>
						{hhiInfo.label}
						{#if supplyInsights.hhi !== null && supplyInsights.hhi !== undefined}
							· HHI {Math.round(supplyInsights.hhi)}
						{/if}
					</span>
				</div>
				<div class="gauge">
					<div class="gauge-fill" style:width="{Math.min(100, hhiInfo.pct)}%" style:background={hhiInfo.color}></div>
				</div>
				<div class="hhi-note">
					Top1 의존 <strong>{pct(supplyInsights.top1Ratio)}</strong> · Top3 <strong>{pct(supplyInsights.top3Ratio)}</strong>
				</div>
			</div>

			<div class="sup-grid">
				<div class="sup-cell">
					<div class="sup-k">공급사</div>
					<div class="sup-v">{supplyInsights.supplierCount ?? '-'}사</div>
				</div>
				<div class="sup-cell">
					<div class="sup-k">고객사</div>
					<div class="sup-v">{supplyInsights.customerCount ?? '-'}사</div>
				</div>
				<div class="sup-cell">
					<div class="sup-k">정밀 엣지</div>
					<div class="sup-v">{supplyInsights.preciseEdgeCount ?? '-'}</div>
				</div>
				<div class="sup-cell">
					<div class="sup-k">산업 다양성</div>
					<div class="sup-v">{supplyInsights.industryDiversity ?? '-'}</div>
				</div>
			</div>

			{#if supplyInsights.topSupplyIndustries?.length}
				<div class="bar-list">
					<div class="bar-title">상위 공급 산업</div>
					{#each supplyInsights.topSupplyIndustries.slice(0, 5) as item}
						{@const max = supplyInsights.topSupplyIndustries[0]?.amount || 1}
						<div class="bar-row">
							<span class="bar-name">{item.name || item.industry}</span>
							<div class="bar-track">
								<div class="bar-fill" style:width="{(item.amount / max) * 100}%"></div>
							</div>
							<span class="bar-val">{fmtKor((item.amount || 0) * 1e8, '')}</span>
						</div>
					{/each}
				</div>
			{/if}
		</div>
	{/if}

	<!-- 핵심 거래 Top 5 -->
	{#if topPreciseEdges.length > 0}
		<div class="section">
			<h3>핵심 거래 (정밀 Top 5)</h3>
			<ul class="edge-list">
				{#each topPreciseEdges as e}
					<li>
						<div class="edge-row">
							<span class="edge-kind {e.kind === '공급' ? 'sup' : 'cus'}">{e.kind}</span>
							<strong>{e.corpName || e.partner?.label || '-'}</strong>
							{#if e.product}<span class="edge-prod">· {e.product}</span>{/if}
						</div>
						<div class="edge-amt">
							{Math.round(e.amount).toLocaleString()}억원
							{#if e.ratio}<span class="edge-ratio">({e.ratio}%)</span>{/if}
						</div>
					</li>
				{/each}
			</ul>
		</div>
	{/if}

	<!-- 6. AI 인사이트 + 블로그 -->
	{#if aiInsight}
		<div class="section">
			<h3>AI 분석</h3>
			{#if aiInsight.strengths?.length}
				<div class="chips">
					{#each aiInsight.strengths.slice(0, 4) as s}
						<span class="chip strength">✓ {s}</span>
					{/each}
				</div>
			{/if}
			{#if aiInsight.weaknesses?.length}
				<div class="chips">
					{#each aiInsight.weaknesses.slice(0, 4) as w}
						<span class="chip weak">⚠ {w}</span>
					{/each}
				</div>
			{/if}
			{#if aiInsight.narrative}
				<div class="narrative" class:expanded={aiExpanded}>
					{aiInsight.narrative}
				</div>
				{#if aiInsight.narrative.length > 200}
					<button class="more" onclick={() => (aiExpanded = !aiExpanded)}>
						{aiExpanded ? '▲ 접기' : '▼ 더보기'}
					</button>
				{/if}
			{/if}
		</div>
	{/if}

	{#if blogPosts.length > 0}
		<div class="section">
			<h3>심층 분석 글</h3>
			{#each blogPosts as post}
				<a class="blog-card" href="{base}/blog/{post.slug}" target="_blank" rel="noopener">
					<div class="blog-title">{post.title}</div>
					{#if post.verdict}
						<div class="blog-verdict">{post.verdict}</div>
					{/if}
					<div class="blog-meta">
						{#if post.direction}<span class="blog-tag">{post.direction}</span>{/if}
						{#if post.archetype}<span class="blog-tag">{post.archetype}</span>{/if}
					</div>
				</a>
			{/each}
		</div>
	{/if}

	<!-- 액션 버튼 -->
	<div class="actions">
		<button class="action primary" disabled={compareDisabled} onclick={() => onAddCompare?.(node.id)}>
			+ 비교에 추가
		</button>
		<a class="action ghost" href={issueUrl()} target="_blank" rel="noopener">
			🐛 분류 신고
		</a>
	</div>
</div>

<style>
	.card {
		display: flex;
		flex-direction: column;
		gap: 0;
		padding: 16px 16px 80px;
		color: #f1f5f9;
		position: relative;
	}
	.close {
		position: absolute;
		top: 12px;
		right: 12px;
		background: none;
		border: none;
		font-size: 18px;
		cursor: pointer;
		color: #64748b;
		z-index: 2;
	}
	.close:hover {
		color: #f1f5f9;
	}

	.head h2 {
		margin: 0;
		font-size: 20px;
		color: #f1f5f9;
	}
	.code {
		margin: 2px 0 8px;
		font-family: monospace;
		color: #64748b;
		font-size: 12px;
	}
	.badges {
		display: flex;
		gap: 6px;
		flex-wrap: wrap;
		margin-bottom: 8px;
	}
	.badge {
		font-size: 11px;
		padding: 2px 8px;
		border-radius: 4px;
		font-weight: 500;
	}
	.badge.stage {
		background: rgba(52, 211, 153, 0.15);
		color: #34d399;
	}
	.badge.role {
		background: rgba(251, 146, 60, 0.12);
		color: #fb923c;
	}
	.badge.stream {
		background: rgba(167, 139, 250, 0.15);
		color: #a78bfa;
	}

	.loading {
		padding: 12px;
		color: #64748b;
		font-size: 12px;
		text-align: center;
	}

	.section {
		margin-top: 16px;
		padding-top: 16px;
		border-top: 1px solid #1e2433;
	}
	.section:first-of-type {
		border-top: none;
	}
	.section h3 {
		font-size: 11px;
		font-weight: 600;
		color: #94a3b8;
		text-transform: uppercase;
		letter-spacing: 0.05em;
		margin: 0 0 8px;
		display: flex;
		justify-content: space-between;
		align-items: center;
	}
	.section h3 .year,
	.section h3 .peer {
		font-weight: 400;
		color: #64748b;
		text-transform: none;
	}

	.fin-grid,
	.sup-grid {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 6px;
	}
	.fin-cell,
	.sup-cell {
		background: #050811;
		border: 1px solid #1e2433;
		border-radius: 6px;
		padding: 8px 10px;
	}
	.fin-k,
	.sup-k {
		font-size: 10px;
		color: #94a3b8;
		margin-bottom: 2px;
	}
	.fin-v {
		font-size: 14px;
		font-weight: 600;
		color: #f1f5f9;
		font-family: monospace;
	}
	.sup-v {
		font-size: 13px;
		font-weight: 600;
		color: #f1f5f9;
	}

	.scan-grid {
		display: flex;
		flex-direction: column;
		gap: 4px;
	}
	.scan-row {
		display: grid;
		grid-template-columns: 90px 70px 1fr;
		align-items: center;
		padding: 5px 8px;
		background: #050811;
		border: 1px solid #1e2433;
		border-radius: 4px;
		font-size: 12px;
	}
	.scan-k {
		color: #94a3b8;
	}
	.scan-v {
		font-weight: 600;
		font-family: monospace;
	}
	.scan-grade {
		color: #64748b;
		font-size: 11px;
	}
	.rank-line {
		margin-top: 8px;
		font-size: 11px;
		color: #94a3b8;
	}
	.rank-line strong {
		color: #f1f5f9;
	}

	.hhi-card {
		background: #050811;
		border: 1px solid #1e2433;
		border-radius: 8px;
		padding: 10px 12px;
		margin-bottom: 8px;
	}
	.hhi-head {
		display: flex;
		justify-content: space-between;
		align-items: baseline;
		margin-bottom: 6px;
	}
	.hhi-label {
		font-size: 11px;
		color: #94a3b8;
	}
	.hhi-bucket {
		font-size: 13px;
		font-weight: 600;
	}
	.gauge {
		height: 6px;
		background: #1e2433;
		border-radius: 3px;
		overflow: hidden;
	}
	.gauge-fill {
		height: 100%;
		transition: width 0.3s;
	}
	.hhi-note {
		margin-top: 6px;
		font-size: 11px;
		color: #94a3b8;
	}
	.hhi-note strong {
		color: #f1f5f9;
	}

	.bar-list {
		margin-top: 10px;
	}
	.bar-title {
		font-size: 10px;
		color: #94a3b8;
		text-transform: uppercase;
		margin-bottom: 4px;
	}
	.bar-row {
		display: grid;
		grid-template-columns: 80px 1fr 60px;
		align-items: center;
		gap: 6px;
		padding: 3px 0;
		font-size: 11px;
	}
	.bar-name {
		color: #cbd5e1;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	.bar-track {
		height: 6px;
		background: #1e2433;
		border-radius: 3px;
		overflow: hidden;
	}
	.bar-fill {
		height: 100%;
		background: #60a5fa;
	}
	.bar-val {
		text-align: right;
		color: #f1f5f9;
		font-family: monospace;
		font-size: 10px;
	}

	.edge-list {
		list-style: none;
		padding: 0;
		margin: 0;
	}
	.edge-list li {
		padding: 6px 0;
		border-bottom: 1px solid #1e2433;
	}
	.edge-list li:last-child {
		border-bottom: none;
	}
	.edge-row {
		display: flex;
		gap: 6px;
		align-items: baseline;
		font-size: 12px;
		color: #cbd5e1;
	}
	.edge-row strong {
		color: #f1f5f9;
	}
	.edge-kind {
		font-size: 10px;
		padding: 1px 5px;
		border-radius: 3px;
		font-weight: 600;
	}
	.edge-kind.sup {
		background: rgba(251, 146, 60, 0.15);
		color: #fb923c;
	}
	.edge-kind.cus {
		background: rgba(96, 165, 250, 0.15);
		color: #60a5fa;
	}
	.edge-prod {
		color: #94a3b8;
		font-size: 11px;
	}
	.edge-amt {
		font-size: 12px;
		color: #fbbf24;
		margin-top: 2px;
		font-family: monospace;
	}
	.edge-ratio {
		color: #64748b;
		font-size: 10px;
		margin-left: 4px;
	}

	.chips {
		display: flex;
		flex-wrap: wrap;
		gap: 4px;
		margin-bottom: 6px;
	}
	.chip {
		font-size: 11px;
		padding: 3px 7px;
		border-radius: 4px;
	}
	.chip.strength {
		background: rgba(52, 211, 153, 0.12);
		color: #34d399;
	}
	.chip.weak {
		background: rgba(239, 68, 68, 0.12);
		color: #f87171;
	}
	.narrative {
		font-size: 12px;
		color: #cbd5e1;
		line-height: 1.6;
		max-height: 80px;
		overflow: hidden;
		position: relative;
	}
	.narrative:not(.expanded)::after {
		content: '';
		position: absolute;
		bottom: 0;
		left: 0;
		right: 0;
		height: 20px;
		background: linear-gradient(transparent, #0f1219);
	}
	.narrative.expanded {
		max-height: none;
	}
	.more {
		background: none;
		border: none;
		color: #60a5fa;
		font-size: 11px;
		cursor: pointer;
		padding: 4px 0;
	}

	.blog-card {
		display: block;
		text-decoration: none;
		background: #050811;
		border: 1px solid #1e2433;
		border-radius: 6px;
		padding: 10px 12px;
		margin-bottom: 6px;
		transition: border-color 0.15s;
	}
	.blog-card:hover {
		border-color: #60a5fa;
	}
	.blog-title {
		font-size: 13px;
		color: #f1f5f9;
		font-weight: 600;
	}
	.blog-verdict {
		margin-top: 4px;
		font-size: 11px;
		color: #cbd5e1;
		line-height: 1.4;
	}
	.blog-meta {
		display: flex;
		gap: 4px;
		margin-top: 6px;
	}
	.blog-tag {
		font-size: 10px;
		padding: 1px 6px;
		background: rgba(96, 165, 250, 0.12);
		color: #60a5fa;
		border-radius: 3px;
	}

	.actions {
		position: sticky;
		bottom: 0;
		left: 0;
		right: 0;
		background: linear-gradient(transparent, #0f1219 30%);
		padding-top: 24px;
		margin-top: 16px;
		display: flex;
		gap: 8px;
	}
	.action {
		flex: 1;
		padding: 8px 12px;
		border-radius: 6px;
		font-size: 12px;
		font-weight: 600;
		cursor: pointer;
		text-align: center;
		text-decoration: none;
		display: inline-flex;
		align-items: center;
		justify-content: center;
		border: 1px solid transparent;
	}
	.action.primary {
		background: #60a5fa;
		color: #050811;
		border-color: #60a5fa;
	}
	.action.primary:hover:not(:disabled) {
		background: #93c5fd;
	}
	.action.primary:disabled {
		background: #1e2433;
		color: #475569;
		cursor: not-allowed;
		border-color: #1e2433;
	}
	.action.ghost {
		background: transparent;
		color: #94a3b8;
		border-color: #1e2433;
	}
	.action.ghost:hover {
		color: #f1f5f9;
		border-color: #334155;
	}
</style>
