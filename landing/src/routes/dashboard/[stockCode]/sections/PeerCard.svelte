<script>
	// @ts-nocheck
	import { base } from '$app/paths';

	let { data } = $props();

	const peersData = $derived(data ?? null);
	const rows = $derived(peersData?.rows ?? []);
	const stageName = $derived(peersData?.stageName ?? null);
	const fallback = $derived(peersData?.stageFallback === true);

	// 4 metric axes + 각 축별 min/max 계산 (자동 정규화)
	const axes = [
		{ key: 'roe', label: 'ROE', suffix: '%', color: '#ea4647', higherBetter: true },
		{ key: 'opMargin', label: '영업이익률', suffix: '%', color: '#fb923c', higherBetter: true },
		{ key: 'revCagr', label: '매출 CAGR', suffix: '%', color: '#34d399', higherBetter: true },
		{ key: 'debtRatio', label: '부채비율', suffix: '%', color: '#fbbf24', higherBetter: false }
	];

	function stats(key) {
		const vals = rows.map((r) => r?.[key]).filter((v) => Number.isFinite(Number(v)));
		if (!vals.length) return { min: 0, max: 0 };
		return { min: Math.min(...vals), max: Math.max(...vals) };
	}

	const axisStats = $derived(Object.fromEntries(axes.map((a) => [a.key, stats(a.key)])));

	function barWidth(val, key) {
		if (!Number.isFinite(Number(val))) return 0;
		const s = axisStats[key];
		const range = s.max - s.min || 1;
		// 값을 0~100% 로 매핑. 음수 가능 (ROE, CAGR)
		return Math.max(3, Math.min(100, ((val - s.min) / range) * 100));
	}

	function fmt(v, suffix) {
		if (v == null || !Number.isFinite(Number(v))) return '—';
		return `${Number(v).toFixed(1)}${suffix}`;
	}

	function fmtKrw(v) {
		if (v == null || !Number.isFinite(Number(v))) return '—';
		const x = Number(v);
		if (x >= 10000) return `${(x / 10000).toFixed(1)}조`;
		if (x >= 1) return `${Math.round(x).toLocaleString()}억`;
		return '—';
	}
</script>

{#if rows.length >= 2}
	<section class="container pc-section">
		<div class="card pc-card">
			<div class="head">
				<div>
					<div class="card-title">PEERS · 동업종 비교</div>
					<h3>
						{#if stageName && !fallback}
							같은 단계({stageName}) 상위 {rows.length}사
						{:else}
							업종 내 상위 {rows.length}사
						{/if}
					</h3>
					<div class="sub">
						매출·ROE·영업이익률·CAGR·부채비율. 본인은 빨강 하이라이트.
					</div>
				</div>
			</div>

			<div class="table-wrap">
				<table class="peer-table">
					<thead>
						<tr>
							<th class="col-name">회사</th>
							<th class="col-rev">매출</th>
							{#each axes as a}
								<th class="col-metric">{a.label}</th>
							{/each}
						</tr>
					</thead>
					<tbody>
						{#each rows as r}
							<tr class:self={r.isSelf}>
								<td class="col-name">
									{#if r.isSelf}
										<span class="self-mark">●</span>
										<span class="corp mono">{r.corpName ?? r.stockCode}</span>
									{:else}
										<a class="corp-link" href="{base}/dashboard/{r.stockCode}">
											{r.corpName ?? r.stockCode}
										</a>
									{/if}
								</td>
								<td class="col-rev mono">{fmtKrw(r.revenue)}</td>
								{#each axes as a}
									{@const val = r[a.key]}
									<td class="col-metric">
										<div class="metric-row">
											<span class="metric-val mono">{fmt(val, a.suffix)}</span>
											<div class="metric-bar">
												<div
													class="metric-fill"
													class:self-fill={r.isSelf}
													style:width={`${barWidth(val, a.key)}%`}
													style:background={r.isSelf ? undefined : a.color}
													style:opacity={r.isSelf ? 1 : 0.4}
												></div>
											</div>
										</div>
									</td>
								{/each}
							</tr>
						{/each}
					</tbody>
				</table>
			</div>
		</div>
	</section>
{/if}

<style>
	.pc-section {
		margin: 24px auto;
	}
	.pc-card {
		padding: 24px;
	}
	.head {
		margin-bottom: 16px;
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
		font-size: 12px;
	}

	.table-wrap {
		overflow-x: auto;
	}
	.peer-table {
		width: 100%;
		border-collapse: collapse;
		font-size: 12px;
	}
	.peer-table th {
		text-align: left;
		padding: 8px 10px;
		color: var(--text-dim);
		font-size: 10px;
		font-weight: 600;
		letter-spacing: 0.06em;
		text-transform: uppercase;
		border-bottom: 1px solid var(--border);
		white-space: nowrap;
	}
	.peer-table td {
		padding: 10px;
		border-bottom: 1px solid var(--border);
		color: var(--text-mid);
	}
	.peer-table tr.self td {
		background: linear-gradient(90deg, rgba(234, 70, 71, 0.06), transparent);
	}
	.peer-table tr.self .corp {
		color: var(--text);
		font-weight: 700;
	}
	.peer-table tr:hover:not(.self) td {
		background: rgba(255, 255, 255, 0.02);
	}

	.col-name {
		min-width: 140px;
	}
	.col-rev {
		text-align: right;
		color: var(--text);
		min-width: 70px;
	}
	.col-metric {
		min-width: 150px;
	}
	th.col-rev,
	th.col-metric {
		text-align: right;
	}

	.self-mark {
		color: var(--red);
		margin-right: 4px;
		font-size: 10px;
	}
	.corp-link {
		color: var(--text-mid);
		text-decoration: none;
	}
	.corp-link:hover {
		color: var(--text);
		text-decoration: underline;
	}

	.metric-row {
		display: flex;
		align-items: center;
		gap: 8px;
	}
	.metric-val {
		flex-shrink: 0;
		min-width: 44px;
		text-align: right;
		font-size: 11px;
		color: var(--text);
	}
	.metric-bar {
		flex: 1;
		height: 5px;
		background: rgba(255, 255, 255, 0.04);
		border-radius: 2.5px;
		overflow: hidden;
		min-width: 50px;
	}
	.metric-fill {
		height: 100%;
		border-radius: 2.5px;
	}
	.metric-fill.self-fill {
		background: var(--grad-heat) !important;
	}
</style>
