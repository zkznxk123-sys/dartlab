<script>
	// @ts-nocheck
	/** @type {{ data: { periods: string[], is: any, cf: any, bs: any } }} */
	let { data } = $props();

	const periods = $derived(data?.periods ?? []);
	const sales = $derived(data?.is?.sales ?? []);
	const op = $derived(data?.is?.op ?? []);
	const ocf = $derived(data?.cf?.ocf ?? []);
	const totalAsset = $derived(data?.bs?.totalAsset ?? []);

	const W = 720;
	const H = 240;
	const padL = 50;
	const padR = 16;
	const padT = 18;
	const padB = 36;
	const w = W - padL - padR;
	const h = H - padT - padB;

	function _safeMax(arr) {
		const v = arr.filter((x) => typeof x === 'number' && Number.isFinite(x));
		return v.length ? Math.max(...v) : 0;
	}
	function _safeMin(arr) {
		const v = arr.filter((x) => typeof x === 'number' && Number.isFinite(x));
		return v.length ? Math.min(...v) : 0;
	}

	const allPos = $derived([...sales, ...op, ...ocf].filter((x) => typeof x === 'number'));
	const yMax = $derived(_safeMax(allPos) * 1.1 || 1);
	const yMin = $derived(Math.min(0, _safeMin(allPos) * 1.1));
	const yRange = $derived(yMax - yMin || 1);

	const n = $derived(periods.length || 1);
	const xStep = $derived(w / Math.max(1, n - 1));

	function pathOf(arr) {
		const pts = [];
		for (let i = 0; i < arr.length; i++) {
			const v = arr[i];
			if (typeof v !== 'number' || !Number.isFinite(v)) continue;
			const x = padL + i * xStep;
			const y = padT + h - ((v - yMin) / yRange) * h;
			pts.push(`${pts.length === 0 ? 'M' : 'L'} ${x.toFixed(1)} ${y.toFixed(1)}`);
		}
		return pts.join(' ');
	}

	function _cagr(arr) {
		const v = arr.filter((x) => typeof x === 'number');
		if (v.length < 8) return null;
		const start = v.slice(0, 4).reduce((a, b) => a + b, 0); // 첫 1년 합
		const end = v.slice(-4).reduce((a, b) => a + b, 0); // 마지막 1년 합
		if (start <= 0 || end <= 0) return null;
		const years = Math.max(1, (v.length - 4) / 4);
		return (Math.pow(end / start, 1 / years) - 1) * 100;
	}
	const cagrSales = $derived(_cagr(sales));
	const cagrOp = $derived(_cagr(op));
	const cagrOcf = $derived(_cagr(ocf));

	const yTicks = $derived([0, 0.25, 0.5, 0.75, 1].map((p) => yMin + yRange * p));
</script>

{#if periods.length}
	<section class="container q-section">
		<div class="card q-card">
			<div class="head">
				<div>
					<div class="card-title">QUARTERLY · 20분기 시계열</div>
					<h3>5년 분기별 매출·영업이익·영업현금흐름</h3>
					<div class="sub">DART 정기보고서 분기 standalone 값. 단위 조원.</div>
				</div>
				<div class="cagr-row">
					<div class="cagr-pill">
						<span class="cl c-sales"></span>
						매출 CAGR
						<span class="mono cv">{cagrSales != null ? `${cagrSales >= 0 ? '+' : ''}${cagrSales.toFixed(1)}%` : '—'}</span>
					</div>
					<div class="cagr-pill">
						<span class="cl c-op"></span>
						영업이익 CAGR
						<span class="mono cv">{cagrOp != null ? `${cagrOp >= 0 ? '+' : ''}${cagrOp.toFixed(1)}%` : '—'}</span>
					</div>
					<div class="cagr-pill">
						<span class="cl c-ocf"></span>
						OCF CAGR
						<span class="mono cv">{cagrOcf != null ? `${cagrOcf >= 0 ? '+' : ''}${cagrOcf.toFixed(1)}%` : '—'}</span>
					</div>
				</div>
			</div>

			<svg viewBox="0 0 {W} {H}" width="100%" style="display:block">
				<defs>
					<linearGradient id="qSalesG" x1="0" x2="0" y1="0" y2="1">
						<stop offset="0%" stop-color="#ea4647" stop-opacity="0.3" />
						<stop offset="100%" stop-color="#ea4647" stop-opacity="0" />
					</linearGradient>
				</defs>

				<!-- y grid -->
				{#each yTicks as t}
					{@const y = padT + h - ((t - yMin) / yRange) * h}
					<line x1={padL} x2={W - padR} y1={y} y2={y} stroke="rgba(255,255,255,0.05)" />
					<text x={padL - 6} y={y + 3} font-size="9" fill="#6b7280" text-anchor="end" font-family="var(--font-mono)">{t.toFixed(0)}</text>
				{/each}

				<!-- sales 라인 -->
				<path d={pathOf(sales)} stroke="#ea4647" stroke-width="2" fill="none" stroke-linecap="round" />
				<!-- op 라인 -->
				<path d={pathOf(op)} stroke="#fb923c" stroke-width="2" fill="none" stroke-linecap="round" />
				<!-- ocf 라인 -->
				<path d={pathOf(ocf)} stroke="#34d399" stroke-width="2" fill="none" stroke-linecap="round" stroke-dasharray="4 3" />

				<!-- x labels (분기 4개마다) -->
				{#each periods as p, i}
					{#if i % 4 === 0}
						<text x={padL + i * xStep} y={H - 16} font-size="10" fill="#6b7280" text-anchor="middle" font-family="var(--font-mono)">{p}</text>
					{/if}
				{/each}

				<!-- 0 라인 -->
				{#if yMin < 0}
					{@const y0 = padT + h - ((0 - yMin) / yRange) * h}
					<line x1={padL} x2={W - padR} y1={y0} y2={y0} stroke="rgba(255,255,255,0.15)" stroke-dasharray="2 3" />
				{/if}
			</svg>

			<div class="legend">
				<span class="leg"><span class="sw c-sales"></span>매출 (Sales)</span>
				<span class="leg"><span class="sw c-op"></span>영업이익 (OP)</span>
				<span class="leg"><span class="sw c-ocf dash"></span>영업현금흐름 (OCF)</span>
			</div>
		</div>
	</section>
{/if}

<style>
	.q-section {
		margin: 24px auto;
	}
	.q-card {
		padding: 24px;
	}
	.head {
		display: flex;
		justify-content: space-between;
		align-items: flex-end;
		flex-wrap: wrap;
		gap: 16px;
		margin-bottom: 14px;
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
	.cagr-row {
		display: flex;
		gap: 8px;
		flex-wrap: wrap;
	}
	.cagr-pill {
		display: inline-flex;
		align-items: center;
		gap: 6px;
		padding: 5px 11px;
		border-radius: 999px;
		font-size: 11px;
		background: rgba(255, 255, 255, 0.04);
		border: 1px solid var(--border);
		color: var(--text-mid);
	}
	.cl {
		width: 10px;
		height: 3px;
		border-radius: 2px;
	}
	.cl.c-sales {
		background: #ea4647;
	}
	.cl.c-op {
		background: #fb923c;
	}
	.cl.c-ocf {
		background: #34d399;
	}
	.cv {
		color: var(--text);
		font-weight: 600;
	}
	.legend {
		display: flex;
		gap: 18px;
		justify-content: center;
		flex-wrap: wrap;
		padding-top: 12px;
		border-top: 1px solid var(--border);
		margin-top: 12px;
	}
	.leg {
		display: flex;
		align-items: center;
		gap: 6px;
		font-size: 11px;
		color: var(--text-mid);
	}
	.sw {
		display: inline-block;
		width: 16px;
		height: 3px;
		border-radius: 2px;
	}
	.sw.c-sales {
		background: #ea4647;
	}
	.sw.c-op {
		background: #fb923c;
	}
	.sw.c-ocf {
		background: #34d399;
	}
	.sw.dash {
		background: transparent;
		border-top: 2px dashed #34d399;
		height: 0;
	}
</style>
