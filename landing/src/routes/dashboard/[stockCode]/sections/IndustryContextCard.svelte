<script>
	// @ts-nocheck
	import { base } from '$app/paths';

	let { data } = $props();

	const ctx = $derived(data ?? null);

	// stage 분포 donut
	const SIZE = 120;
	const cx = SIZE / 2;
	const cy = SIZE / 2;
	const R = 48;
	const r = 28;

	const stages = $derived(ctx?.stagesSummary ?? []);
	const totalCount = $derived(stages.reduce((s, x) => s + (x.count ?? 0), 0) || 1);

	const palette = ['#ea4647', '#fb923c', '#fbbf24', '#34d399', '#3b82f6', '#a78bfa', '#ec4899', '#06b6d4'];

	function arcPath(startFrac, endFrac, outer, inner) {
		if (endFrac - startFrac < 0.0001) return '';
		const a0 = startFrac * 2 * Math.PI - Math.PI / 2;
		const a1 = endFrac * 2 * Math.PI - Math.PI / 2;
		const x0 = cx + outer * Math.cos(a0);
		const y0 = cy + outer * Math.sin(a0);
		const x1 = cx + outer * Math.cos(a1);
		const y1 = cy + outer * Math.sin(a1);
		const x2 = cx + inner * Math.cos(a1);
		const y2 = cy + inner * Math.sin(a1);
		const x3 = cx + inner * Math.cos(a0);
		const y3 = cy + inner * Math.sin(a0);
		const large = endFrac - startFrac > 0.5 ? 1 : 0;
		return `M ${x0} ${y0} A ${outer} ${outer} 0 ${large} 1 ${x1} ${y1} L ${x2} ${y2} A ${inner} ${inner} 0 ${large} 0 ${x3} ${y3} Z`;
	}

	// donut segments
	const segments = $derived.by(() => {
		let acc = 0;
		return stages.map((s, i) => {
			const frac = (s.count ?? 0) / totalCount;
			const start = acc;
			acc += frac;
			return {
				...s,
				color: palette[i % palette.length],
				isMyStage: s.key === ctx?.myStage,
				startFrac: start,
				endFrac: acc,
				pct: frac * 100
			};
		});
	});

	function fmtKrw(v) {
		if (v == null || !Number.isFinite(v)) return '—';
		const x = Number(v);
		if (x >= 10000) return `${(x / 10000).toFixed(1)}조`;
		if (x >= 1) return `${Math.round(x).toLocaleString()}억`;
		return '—';
	}

	const rankPct = $derived.by(() => {
		if (!ctx?.myRank || !ctx?.totalInIndustry) return null;
		return (1 - (ctx.myRank - 1) / ctx.totalInIndustry) * 100;
	});
</script>

{#if ctx}
	<section class="container ic-section">
		<div class="card ic-card">
			<div class="head">
				<div>
					<div class="card-title">INDUSTRY · 업종 위치</div>
					<h3>{ctx.name ?? ctx.industryId}</h3>
					<div class="sub">
						{ctx.nodeCount?.toLocaleString?.() ?? ctx.totalInIndustry} 사 · 총 매출 {fmtKrw(ctx.totalRevenue)}
						· 내부 공급망 {ctx.edgesCount ?? 0} edges
					</div>
				</div>
				<a class="btn-ghost" href="{base}/map?industry={ctx.industryId}">
					📊 업종 지도에서 보기 →
				</a>
			</div>

			<div class="grid">
				<!-- 좌: stage 분포 donut -->
				<div class="col-donut">
					<svg viewBox="0 0 {SIZE} {SIZE}" width="120" height="120">
						{#each segments as seg}
							<path d={arcPath(seg.startFrac, seg.endFrac, R, r)} fill={seg.color} opacity={seg.isMyStage ? 1 : 0.55} />
						{/each}
						<text x={cx} y={cy - 3} text-anchor="middle" font-size="10" fill="var(--text-dim)">단계</text>
						<text x={cx} y={cy + 10} text-anchor="middle" font-size="14" fill="var(--text)" font-weight="700">
							{stages.length}
						</text>
					</svg>
					<div class="stage-legend">
						{#each segments as seg}
							<div class="leg" class:self={seg.isMyStage}>
								<span class="leg-dot" style:background={seg.color}></span>
								<span class="leg-name">{seg.name}</span>
								<span class="leg-pct mono">{seg.pct.toFixed(0)}%</span>
								<span class="leg-count mono">({seg.count})</span>
							</div>
						{/each}
					</div>
				</div>

				<!-- 우: 회사 위치 -->
				<div class="col-rank">
					<div class="rank-block">
						<div class="rank-label">이 회사의 단계</div>
						<div class="rank-value">
							{ctx.myStageName ?? '—'}
							{#if ctx.myStage}
								<span class="rank-badge mono">{ctx.myStage}</span>
							{/if}
						</div>
					</div>

					<div class="rank-block">
						<div class="rank-label">업종 내 순위 (매출 기준)</div>
						{#if ctx.myRank}
							<div class="rank-value">
								<span class="rank-big mono">{ctx.myRank}</span>
								<span class="rank-slash">/</span>
								<span class="rank-total mono">{ctx.totalInIndustry}</span>
							</div>
							{#if rankPct != null}
								<div class="rank-bar">
									<div class="rank-fill" style:width={`${Math.max(2, rankPct)}%`}></div>
								</div>
								<div class="rank-pct mono">상위 {(100 - rankPct).toFixed(1)}%ile 이상</div>
							{/if}
						{:else}
							<div class="rank-value dim">데이터 없음</div>
						{/if}
					</div>
				</div>
			</div>
		</div>
	</section>
{/if}

<style>
	.ic-section {
		margin: 24px auto;
	}
	.ic-card {
		padding: 24px;
	}
	.head {
		display: flex;
		justify-content: space-between;
		align-items: flex-start;
		flex-wrap: wrap;
		gap: 12px;
		margin-bottom: 16px;
	}
	h3 {
		font-size: 22px;
		font-weight: 700;
		letter-spacing: -0.01em;
		margin: 6px 0 4px;
		color: var(--text);
	}
	.sub {
		color: var(--text-mid);
		font-size: 13px;
	}
	.btn-ghost {
		padding: 6px 12px;
		border: 1px solid var(--border);
		border-radius: 8px;
		font-size: 12px;
		color: var(--text-mid);
		text-decoration: none;
		transition: all 0.15s;
	}
	.btn-ghost:hover {
		border-color: var(--border-accent);
		color: var(--orange);
	}

	.grid {
		display: grid;
		grid-template-columns: auto 1fr;
		gap: 32px;
		align-items: center;
	}
	@media (max-width: 760px) {
		.grid {
			grid-template-columns: 1fr;
			gap: 20px;
		}
	}

	.col-donut {
		display: flex;
		gap: 20px;
		align-items: center;
	}
	.stage-legend {
		display: flex;
		flex-direction: column;
		gap: 4px;
	}
	.leg {
		display: grid;
		grid-template-columns: 12px 1fr auto auto;
		gap: 8px;
		align-items: center;
		font-size: 11px;
		color: var(--text-mid);
	}
	.leg.self {
		color: var(--text);
		font-weight: 600;
	}
	.leg-dot {
		width: 10px;
		height: 10px;
		border-radius: 2px;
	}
	.leg-pct {
		color: var(--text);
	}
	.leg-count {
		color: var(--text-faint);
		font-size: 10px;
	}

	.col-rank {
		display: flex;
		flex-direction: column;
		gap: 16px;
	}
	.rank-block {
		padding: 12px 14px;
		border: 1px solid var(--border);
		border-radius: var(--r-md);
		background: rgba(255, 255, 255, 0.02);
	}
	.rank-label {
		font-size: 10px;
		font-weight: 700;
		letter-spacing: 0.1em;
		text-transform: uppercase;
		color: var(--text-dim);
		margin-bottom: 6px;
	}
	.rank-value {
		font-size: 16px;
		color: var(--text);
		font-weight: 600;
		display: flex;
		align-items: baseline;
		gap: 8px;
	}
	.rank-value.dim {
		color: var(--text-faint);
	}
	.rank-badge {
		font-size: 10px;
		padding: 2px 6px;
		border-radius: 4px;
		background: rgba(255, 255, 255, 0.04);
		border: 1px solid var(--border);
		color: var(--text-mid);
	}
	.rank-big {
		font-size: 28px;
		font-weight: 800;
		color: var(--orange);
		letter-spacing: -0.02em;
	}
	.rank-slash {
		color: var(--text-dim);
		font-size: 18px;
	}
	.rank-total {
		font-size: 14px;
		color: var(--text-mid);
	}
	.rank-bar {
		margin-top: 8px;
		height: 6px;
		background: rgba(255, 255, 255, 0.04);
		border-radius: 3px;
		overflow: hidden;
	}
	.rank-fill {
		height: 100%;
		background: var(--grad-heat);
		border-radius: 3px;
	}
	.rank-pct {
		margin-top: 6px;
		font-size: 11px;
		color: var(--text-mid);
	}
</style>
