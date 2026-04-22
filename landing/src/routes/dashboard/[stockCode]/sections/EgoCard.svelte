<script>
	// @ts-nocheck
	/**
	 * EgoCard — companies/{stockCode}.json 의 풍부한 prebuild 데이터를 한 카드로.
	 *
	 * data shape (from assembleCompany egoData):
	 *   { ego, aiInsight, blogPosts, financials5y, supplyInsights, peers, suppliersTop10, customersTop10, neighborsCount, edgesCount, hop2Count }
	 */
	import { base } from '$app/paths';

	let { data } = $props();

	const ego = $derived(data?.ego ?? null);
	const ai = $derived(data?.aiInsight ?? null);
	const blogs = $derived(data?.blogPosts ?? []);
	const fin5y = $derived(data?.financials5y ?? []);
	const supply = $derived(data?.supplyInsights ?? null);
	const peers = $derived(data?.peers ?? []);
	const suppliers = $derived(data?.suppliersTop10 ?? []);
	const customers = $derived(data?.customersTop10 ?? []);
	const counts = $derived({
		neighbors: data?.neighborsCount ?? 0,
		edges: data?.edgesCount ?? 0,
		hop2: data?.hop2Count ?? 0
	});

	const strengths = $derived(Array.isArray(ai?.strengths) ? ai.strengths.slice(0, 4) : []);
	const weaknesses = $derived(Array.isArray(ai?.weaknesses) ? ai.weaknesses.slice(0, 4) : []);
	const narrative = $derived(typeof ai?.narrative === 'string' ? ai.narrative : '');

	// 5Y 사업 sparkline
	const SP_W = 100;
	const SP_H = 32;
	function sparkPath(arr, key) {
		const vals = (arr ?? []).map((d) => Number(d?.[key])).filter((v) => Number.isFinite(v));
		if (vals.length < 2) return '';
		const lo = Math.min(...vals);
		const hi = Math.max(...vals);
		const span = hi - lo || 1;
		return vals
			.map((v, i) => {
				const x = (i / (vals.length - 1)) * SP_W;
				const y = SP_H - ((v - lo) / span) * SP_H;
				return `${i === 0 ? 'M' : 'L'} ${x.toFixed(1)} ${y.toFixed(1)}`;
			})
			.join(' ');
	}
	function lastVal(arr, key) {
		const vals = (arr ?? []).map((d) => Number(d?.[key])).filter((v) => Number.isFinite(v));
		return vals.length ? vals[vals.length - 1] : null;
	}
	function pctChange(arr, key) {
		const vals = (arr ?? []).map((d) => Number(d?.[key])).filter((v) => Number.isFinite(v) && v > 0);
		if (vals.length < 2) return null;
		const start = vals[0];
		const end = vals[vals.length - 1];
		const years = Math.max(1, vals.length - 1);
		return (Math.pow(end / start, 1 / years) - 1) * 100;
	}

	function fmtRev(v) {
		if (v == null || !Number.isFinite(v)) return '—';
		const x = Number(v);
		if (x >= 1e8) return `${(x / 1e8).toFixed(1)}B`;
		if (x >= 1e6) return `${(x / 1e6).toFixed(1)}M`;
		if (x >= 1e3) return `${(x / 1e3).toFixed(1)}K`;
		return x.toFixed(0);
	}
	// financials5y 의 sales 단위 — DART scan 기준 백만원 가능. 안전 변환.
	function fmtKrw(v) {
		if (v == null || !Number.isFinite(v)) return '—';
		const x = Number(v);
		// 큰 단위는 조원
		if (x >= 1e12) return `${(x / 1e12).toFixed(1)}조`;
		if (x >= 1e8) return `${(x / 1e8).toFixed(0)}억`;
		if (x >= 1e4) return `${(x / 1e4).toFixed(0)}만`;
		return x.toFixed(0);
	}

	const seriesDefs = [
		{ key: 'sales', label: '매출', color: '#ea4647' },
		{ key: 'operating_profit', label: '영업이익', color: '#fb923c' },
		{ key: 'net_profit', label: '순이익', color: '#fbbf24' },
		{ key: 'total_assets', label: '자산', color: '#34d399' }
	];

	// HHI 컬러
	const hhiColor = $derived.by(() => {
		const h = supply?.hhi ?? 0;
		if (h >= 2500) return '#ea4647';
		if (h >= 1500) return '#fb923c';
		return '#34d399';
	});

	// peers max revenue (bar 정규화)
	const peerMaxRev = $derived(
		Math.max(0, ...peers.map((p) => Number(p?.revenue) || 0))
	);
	const myRev = $derived(Number(ego?.revenue) || 0);
</script>

{#if ego}
	<section class="container ego-section">
		<div class="card ego-card">
			<div class="head">
				<div>
					<div class="card-title">EGO · 회사 종합 인사이트</div>
					<h3>{ego.corpName} — AI 분석 + 5년 사업 + 공급망 + 동업종</h3>
					<div class="sub">
						{ego.industry ?? '—'} · {ego.stage ?? '—'} · 매출 {fmtKrw(ego.revenue)}
						· 1홉 {counts.neighbors} · 2홉 {counts.hop2}
					</div>
				</div>
			</div>

			<div class="grid">
				<!-- 좌: AI Insight -->
				<div class="col col-ai">
					<div class="ai-head">
						<span class="kicker">AI INSIGHT</span>
						{#if ai?.sector}<span class="pill">{ai.sector}</span>{/if}
					</div>
					{#if narrative}
						<p class="narrative">{narrative}</p>
					{:else}
						<p class="narrative dim">AI 분석 데이터 준비 중.</p>
					{/if}
					{#if strengths.length}
						<div class="tag-row">
							<span class="tag-label good">Strengths</span>
							<div class="tags">
								{#each strengths as s}<span class="tag tag-good">{s}</span>{/each}
							</div>
						</div>
					{/if}
					{#if weaknesses.length}
						<div class="tag-row">
							<span class="tag-label warn">Weaknesses</span>
							<div class="tags">
								{#each weaknesses as w}<span class="tag tag-warn">{w}</span>{/each}
							</div>
						</div>
					{/if}
					{#if blogs.length}
						<a class="blog-link" href="{base}/blog/{blogs[0].slug}">
							<span class="blog-eyebrow">📖 심층분석</span>
							<span class="blog-title">{blogs[0].title}</span>
							<span class="blog-arrow">→</span>
						</a>
					{/if}
				</div>

				<!-- 우: 5Y sparklines + Supply HHI + Peers -->
				<div class="col col-data">
					<!-- 5Y sparklines -->
					<div class="sub-block">
						<div class="kicker">5Y 사업 추이</div>
						<div class="spark-grid">
							{#each seriesDefs as s}
								{@const last = lastVal(fin5y, s.key)}
								{@const cagr = pctChange(fin5y, s.key)}
								<div class="spark-cell">
									<div class="spark-head">
										<span class="spark-label">{s.label}</span>
										{#if cagr != null}
											<span class="spark-cagr mono" style:color={cagr >= 0 ? '#34d399' : '#ea4647'}>
												{cagr >= 0 ? '+' : ''}{cagr.toFixed(1)}%
											</span>
										{/if}
									</div>
									<svg viewBox="0 0 {SP_W} {SP_H}" width="100%" height="32">
										<path d={sparkPath(fin5y, s.key)} stroke={s.color} stroke-width="1.6" fill="none" />
									</svg>
									<div class="spark-last mono">{fmtKrw(last)}</div>
								</div>
							{/each}
						</div>
					</div>

					<!-- Supply HHI -->
					{#if supply}
						<div class="sub-block">
							<div class="kicker">공급망 집중도</div>
							<div class="hhi-row">
								<div class="hhi-gauge">
									<div class="hhi-val mono" style:color={hhiColor}>{Math.round(supply.hhi ?? 0)}</div>
									<div class="hhi-label">HHI · {supply.hhiRisk ?? '—'}</div>
								</div>
								<div class="hhi-stats">
									<div class="hhi-stat">
										<span class="hs-label">공급사</span>
										<span class="hs-val mono">{supply.supplierCount ?? 0}</span>
									</div>
									<div class="hhi-stat">
										<span class="hs-label">고객사</span>
										<span class="hs-val mono">{supply.customerCount ?? 0}</span>
									</div>
									<div class="hhi-stat">
										<span class="hs-label">Top1 비중</span>
										<span class="hs-val mono">
											{supply.top1Ratio != null ? `${Number(supply.top1Ratio).toFixed(1)}%` : '—'}
										</span>
									</div>
									<div class="hhi-stat">
										<span class="hs-label">Top3 비중</span>
										<span class="hs-val mono">
											{supply.top3Ratio != null ? `${Number(supply.top3Ratio).toFixed(1)}%` : '—'}
										</span>
									</div>
								</div>
							</div>
						</div>
					{/if}

					<!-- Peers -->
					{#if peers.length}
						<div class="sub-block">
							<div class="kicker">동업종 비교</div>
							<div class="peer-list">
								<!-- 본인 -->
								<div class="peer-row peer-self">
									<a class="peer-name" href="#">{ego.corpName}</a>
									<div class="peer-bar">
										<div
											class="peer-fill peer-fill-self"
											style:width={peerMaxRev > 0 ? `${(myRev / peerMaxRev) * 100}%` : '0%'}
										></div>
									</div>
									<span class="peer-rev mono">{fmtKrw(myRev)}</span>
								</div>
								{#each peers as p}
									<div class="peer-row">
										<a class="peer-name" href="{base}/dashboard/{p.stockCode}">{p.corpName}</a>
										<div class="peer-bar">
											<div
												class="peer-fill"
												style:width={peerMaxRev > 0
													? `${(Number(p.revenue) / peerMaxRev) * 100}%`
													: '0%'}
											></div>
										</div>
										<span class="peer-rev mono">{fmtKrw(p.revenue)}</span>
									</div>
								{/each}
							</div>
						</div>
					{/if}
				</div>
			</div>
		</div>
	</section>
{/if}

<style>
	.ego-section {
		margin: 24px auto;
	}
	.ego-card {
		padding: 24px;
	}
	.head {
		margin-bottom: 18px;
	}
	h3 {
		font-size: 20px;
		font-weight: 700;
		letter-spacing: -0.01em;
		margin: 6px 0 4px;
		color: var(--text);
	}
	.sub {
		color: var(--text-mid);
		font-size: 13px;
	}

	.grid {
		display: grid;
		grid-template-columns: 1fr 1.4fr;
		gap: 28px;
	}
	@media (max-width: 880px) {
		.grid {
			grid-template-columns: 1fr;
			gap: 20px;
		}
	}

	.kicker {
		font-size: 10px;
		font-weight: 700;
		letter-spacing: 0.14em;
		text-transform: uppercase;
		color: var(--text-dim);
	}

	/* AI Insight */
	.ai-head {
		display: flex;
		align-items: center;
		gap: 10px;
		margin-bottom: 10px;
	}
	.narrative {
		margin: 0 0 14px;
		font-size: 14px;
		line-height: 1.6;
		color: var(--text);
	}
	.narrative.dim {
		color: var(--text-mid);
		font-style: italic;
	}
	.tag-row {
		margin-bottom: 10px;
	}
	.tag-label {
		display: inline-block;
		font-size: 10px;
		letter-spacing: 0.1em;
		font-weight: 700;
		margin-bottom: 6px;
	}
	.tag-label.good {
		color: var(--green);
	}
	.tag-label.warn {
		color: var(--yellow);
	}
	.tags {
		display: flex;
		flex-wrap: wrap;
		gap: 6px;
	}
	.tag {
		display: inline-flex;
		padding: 4px 10px;
		border-radius: 999px;
		font-size: 11px;
		font-weight: 500;
		border: 1px solid var(--border);
		background: rgba(255, 255, 255, 0.03);
		color: var(--text-mid);
	}
	.tag-good {
		color: #bbf7d0;
		background: rgba(52, 211, 153, 0.08);
		border-color: rgba(52, 211, 153, 0.25);
	}
	.tag-warn {
		color: #fde68a;
		background: rgba(251, 191, 36, 0.08);
		border-color: rgba(251, 191, 36, 0.25);
	}
	.blog-link {
		display: flex;
		align-items: center;
		gap: 10px;
		margin-top: 14px;
		padding: 12px 14px;
		border: 1px solid var(--border);
		border-radius: var(--r-md);
		background: linear-gradient(90deg, rgba(234, 70, 71, 0.06), transparent);
		text-decoration: none;
		color: var(--text);
		transition: all 0.15s;
	}
	.blog-link:hover {
		border-color: var(--border-accent);
	}
	.blog-eyebrow {
		font-size: 11px;
		color: var(--orange);
		font-weight: 600;
	}
	.blog-title {
		flex: 1;
		font-size: 13px;
		overflow: hidden;
		white-space: nowrap;
		text-overflow: ellipsis;
	}
	.blog-arrow {
		color: var(--orange);
	}

	/* Sub-blocks */
	.col-data {
		display: flex;
		flex-direction: column;
		gap: 18px;
	}
	.sub-block {
		display: flex;
		flex-direction: column;
		gap: 10px;
	}

	/* Sparklines */
	.spark-grid {
		display: grid;
		grid-template-columns: repeat(2, 1fr);
		gap: 10px;
	}
	.spark-cell {
		padding: 10px 12px;
		border: 1px solid var(--border);
		border-radius: var(--r-md);
		background: rgba(255, 255, 255, 0.02);
	}
	.spark-head {
		display: flex;
		justify-content: space-between;
		align-items: baseline;
	}
	.spark-label {
		font-size: 11px;
		color: var(--text-mid);
	}
	.spark-cagr {
		font-size: 11px;
		font-weight: 700;
	}
	.spark-last {
		text-align: right;
		font-size: 12px;
		color: var(--text);
		font-weight: 600;
	}

	/* HHI */
	.hhi-row {
		display: grid;
		grid-template-columns: auto 1fr;
		gap: 16px;
		align-items: center;
		padding: 12px 14px;
		border: 1px solid var(--border);
		border-radius: var(--r-md);
		background: rgba(255, 255, 255, 0.02);
	}
	.hhi-gauge {
		text-align: center;
		padding: 8px 14px;
	}
	.hhi-val {
		font-size: 28px;
		font-weight: 800;
		letter-spacing: -0.02em;
	}
	.hhi-label {
		font-size: 10px;
		color: var(--text-dim);
		text-transform: uppercase;
		letter-spacing: 0.08em;
		margin-top: 2px;
	}
	.hhi-stats {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 6px 12px;
	}
	.hhi-stat {
		display: flex;
		justify-content: space-between;
		font-size: 11px;
	}
	.hs-label {
		color: var(--text-dim);
	}
	.hs-val {
		color: var(--text);
		font-weight: 600;
	}

	/* Peers */
	.peer-list {
		display: flex;
		flex-direction: column;
		gap: 4px;
	}
	.peer-row {
		display: grid;
		grid-template-columns: 110px 1fr 64px;
		align-items: center;
		gap: 10px;
		font-size: 12px;
	}
	.peer-name {
		color: var(--text-mid);
		text-decoration: none;
		overflow: hidden;
		white-space: nowrap;
		text-overflow: ellipsis;
	}
	.peer-name:hover {
		color: var(--text);
		text-decoration: underline;
	}
	.peer-row.peer-self .peer-name {
		color: var(--text);
		font-weight: 700;
	}
	.peer-bar {
		height: 6px;
		background: rgba(255, 255, 255, 0.04);
		border-radius: 3px;
		overflow: hidden;
	}
	.peer-fill {
		height: 100%;
		background: rgba(255, 255, 255, 0.18);
		border-radius: 3px;
	}
	.peer-fill-self {
		background: var(--grad-heat);
	}
	.peer-rev {
		text-align: right;
		font-size: 11px;
		color: var(--text);
	}
</style>
