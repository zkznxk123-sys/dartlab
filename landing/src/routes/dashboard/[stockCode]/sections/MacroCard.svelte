<script>
	// @ts-nocheck
	let { data } = $props();

	const asOf = $derived(data?.asOf ?? '');
	const kr = $derived(data?.kr ?? null);
	const us = $derived(data?.us ?? null);
	const tw = $derived(data?.sectorTailwind ?? null);
	const industry = $derived(data?.industry ?? '');

	const phaseColor = {
		expansion: '#34d399',
		recovery: '#3b82f6',
		slowdown: '#fbbf24',
		contraction: '#ea4647'
	};

	function _fmt(v) {
		if (v == null) return '—';
		if (Math.abs(v) < 0.05) return '중립';
		const sign = v > 0 ? '+' : '';
		return `${sign}${v.toFixed(2)}`;
	}

	function _twColor(v) {
		if (v == null) return 'var(--text-mid)';
		if (v >= 0.3) return '#34d399';
		if (v >= 0.05) return '#86efac';
		if (v <= -0.3) return '#ea4647';
		if (v <= -0.05) return '#fb923c';
		return 'var(--text-mid)';
	}

	function _twLabel(v) {
		if (v == null) return '데이터 없음';
		if (v >= 0.3) return '강한 순풍';
		if (v >= 0.05) return '순풍';
		if (v <= -0.3) return '강한 역풍';
		if (v <= -0.05) return '역풍';
		return '중립';
	}
</script>

{#if kr || us}
	<section class="container macro-section">
		<div class="card macro-card">
			<div class="head">
				<div>
					<div class="card-title">MACRO · 거시경제 사이클</div>
					<h3>현재 국면 + 섹터 순풍/역풍</h3>
					<div class="sub">{asOf} 기준 · KR/US 시장 분류</div>
				</div>
			</div>

			<div class="grid">
				<!-- KR 국면 -->
				{#if kr}
					<div class="phase-card" style:border-color={`${phaseColor[kr.phase] || '#888'}66`}>
						<div class="ph-flag">🇰🇷 KR</div>
						<div class="ph-name" style:color={phaseColor[kr.phase] || '#fff'}>{kr.phaseLabel || kr.phase}</div>
						<div class="ph-conf">신뢰도 · {kr.confidence}</div>
						{#if kr.signals && kr.signals.length}
							<ul class="ph-signals">
								{#each kr.signals.slice(0, 3) as s}
									<li>{s}</li>
								{/each}
							</ul>
						{/if}
						{#if kr.sectorStrategy}
							<p class="ph-strategy">{kr.sectorStrategy}</p>
						{/if}
					</div>
				{/if}

				<!-- US 국면 -->
				{#if us}
					<div class="phase-card" style:border-color={`${phaseColor[us.phase] || '#888'}66`}>
						<div class="ph-flag">🇺🇸 US</div>
						<div class="ph-name" style:color={phaseColor[us.phase] || '#fff'}>{us.phaseLabel || us.phase}</div>
						<div class="ph-conf">신뢰도 · {us.confidence}</div>
						{#if us.signals && us.signals.length}
							<ul class="ph-signals">
								{#each us.signals.slice(0, 3) as s}
									<li>{s}</li>
								{/each}
							</ul>
						{/if}
						{#if us.sectorStrategy}
							<p class="ph-strategy">{us.sectorStrategy}</p>
						{/if}
					</div>
				{/if}
			</div>

			<!-- 이 회사가 속한 섹터 가중 -->
			{#if tw}
				<div class="sector-tw">
					<div class="stw-head">
						<span class="stw-label">이 회사 섹터</span>
						<span class="stw-industry">{industry}</span>
					</div>
					<div class="stw-grid">
						<div class="stw-cell">
							<span class="stw-mkt">KR</span>
							<span class="stw-val mono" style:color={_twColor(tw.kr)}>{_fmt(tw.kr)}</span>
							<span class="stw-tag" style:color={_twColor(tw.kr)}>{_twLabel(tw.kr)}</span>
						</div>
						<div class="stw-cell">
							<span class="stw-mkt">US</span>
							<span class="stw-val mono" style:color={_twColor(tw.us)}>{_fmt(tw.us)}</span>
							<span class="stw-tag" style:color={_twColor(tw.us)}>{_twLabel(tw.us)}</span>
						</div>
						<div class="stw-cell">
							<span class="stw-mkt">Blended</span>
							<span class="stw-val mono" style:color={_twColor(tw.blended)}>{_fmt(tw.blended)}</span>
							<span class="stw-tag" style:color={_twColor(tw.blended)}>{_twLabel(tw.blended)}</span>
						</div>
					</div>
				</div>
			{/if}
		</div>
	</section>
{/if}

<style>
	.macro-section {
		margin: 24px auto;
	}
	.macro-card {
		padding: 24px;
	}
	.head {
		margin-bottom: 18px;
	}
	h3 {
		font-size: 20px;
		font-weight: 700;
		letter-spacing: -0.01em;
		margin: 6px 0 2px;
		color: var(--text);
	}
	.sub {
		color: var(--text-mid);
		font-size: 13px;
	}

	.grid {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 16px;
	}
	@media (max-width: 760px) {
		.grid {
			grid-template-columns: 1fr;
		}
	}

	.phase-card {
		padding: 18px;
		border: 1px solid var(--border);
		border-radius: var(--r-lg);
		background: rgba(255, 255, 255, 0.02);
	}
	.ph-flag {
		font-size: 12px;
		font-weight: 700;
		letter-spacing: 0.08em;
		color: var(--text-dim);
		margin-bottom: 6px;
	}
	.ph-name {
		font-size: 28px;
		font-weight: 800;
		letter-spacing: -0.02em;
		line-height: 1.1;
		margin-bottom: 4px;
	}
	.ph-conf {
		font-size: 11px;
		color: var(--text-mid);
		margin-bottom: 12px;
	}
	.ph-signals {
		margin: 10px 0;
		padding: 0 0 0 16px;
		font-size: 12px;
		color: var(--text-mid);
		display: flex;
		flex-direction: column;
		gap: 3px;
	}
	.ph-strategy {
		margin: 12px 0 0;
		padding: 10px 12px;
		font-size: 12px;
		color: var(--text);
		background: rgba(255, 255, 255, 0.03);
		border-radius: var(--r-sm);
		border-left: 3px solid var(--orange);
		line-height: 1.5;
	}

	.sector-tw {
		margin-top: 20px;
		padding: 16px 18px;
		background: linear-gradient(135deg, rgba(234, 70, 71, 0.04), rgba(251, 146, 60, 0.02));
		border: 1px solid var(--border);
		border-radius: var(--r-lg);
	}
	.stw-head {
		display: flex;
		justify-content: space-between;
		align-items: baseline;
		margin-bottom: 12px;
	}
	.stw-label {
		font-size: 11px;
		font-weight: 700;
		letter-spacing: 0.12em;
		text-transform: uppercase;
		color: var(--text-dim);
	}
	.stw-industry {
		font-size: 13px;
		font-weight: 600;
		color: var(--text);
	}
	.stw-grid {
		display: grid;
		grid-template-columns: repeat(3, 1fr);
		gap: 10px;
	}
	.stw-cell {
		display: flex;
		flex-direction: column;
		gap: 4px;
		padding: 10px 12px;
		background: var(--card);
		border: 1px solid var(--border);
		border-radius: var(--r-md);
		text-align: center;
	}
	.stw-mkt {
		font-size: 10px;
		letter-spacing: 0.12em;
		color: var(--text-dim);
		font-weight: 600;
	}
	.stw-val {
		font-size: 18px;
		font-weight: 700;
	}
	.stw-tag {
		font-size: 11px;
		font-weight: 600;
	}
</style>
