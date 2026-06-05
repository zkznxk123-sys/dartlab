<script lang="ts">
	// Overview 미니 재무 3차트 (IS·BS·CF) — Detail.svelte 의 차트 로직을 회사 워크스페이스 격자용으로 추출.
	// 입력 = loadCompanyFinanceLitePeriods 의 CompanyFinancePeriodRow[] (분기/연 혼합 최근 N).
	// 단위 억원. 신규 파일(Detail 무손상). 후속: Detail 도 본 컴포넌트로 통일해 중복 제거.
	import type { CompanyFinancePeriodRow } from '$lib/scan/financeLiteRuntime';

	let { periods = [] }: { periods?: CompanyFinancePeriodRow[] } = $props();

	type Point = { label: string; [key: string]: number | string | null };

	function eok(period: CompanyFinancePeriodRow, id: string): number | null {
		const v = period.values[id];
		return typeof v === 'number' && Number.isFinite(v) ? v / 1e8 : null;
	}
	function sumNullable(...vals: Array<number | null>): number | null {
		const nums = vals.filter((v): v is number => typeof v === 'number' && Number.isFinite(v));
		return nums.length ? nums.reduce((s, v) => s + v, 0) : null;
	}
	function remainder(total: number | null, part: number | null): number | null {
		return total == null ? null : Math.max(0, total - (part ?? 0));
	}

	let isData = $derived<Point[]>(
		periods.map((p) => ({ label: p.label, sales: eok(p, 'sales'), op: eok(p, 'operating_profit'), net: eok(p, 'net_income') }))
	);
	let bsData = $derived<Point[]>(
		periods.map((p) => {
			const totalLiab = sumNullable(eok(p, 'current_liabilities'), eok(p, 'noncurrent_liabilities'));
			const opLiab = eok(p, 'trade_payables');
			const equity = eok(p, 'total_stockholders_equity');
			const retained = eok(p, 'retained_earnings');
			return {
				label: p.label,
				operatingLiabilities: opLiab,
				nonOperatingLiabilities: remainder(totalLiab, opLiab),
				retainedEarnings: retained,
				otherEquity: remainder(equity, retained)
			};
		})
	);
	let cfData = $derived<Point[]>(
		periods.map((p) => ({ label: p.label, ocf: eok(p, 'operating_cashflow'), icf: eok(p, 'investing_cashflow'), fcf: eok(p, 'financing_cashflow') }))
	);

	let hasFinance = $derived([...isData, ...bsData, ...cfData].some((row) => Object.entries(row).some(([k, v]) => k !== 'label' && typeof v === 'number')));

	const W = 360, H = 150;
	const PAD = { top: 16, right: 26, bottom: 22, left: 26 };
	const plotW = W - PAD.left - PAD.right;
	const plotH = H - PAD.top - PAD.bottom;

	function vals(data: Point[], keys: string[]): number[] {
		return data.flatMap((d) => keys.map((k) => d[k]).filter((v): v is number => typeof v === 'number' && Number.isFinite(v)));
	}
	function maxAbs(data: Point[], keys: string[]): number {
		const v = vals(data, keys).map(Math.abs);
		return v.length ? Math.max(Math.max(...v), 1) : 1;
	}
	function maxStack(data: Point[], keys: string[]): number {
		const v = data.map((d) => keys.reduce((s, k) => s + Math.max(0, Number(d[k]) || 0), 0));
		return v.length ? Math.max(Math.max(...v), 1) : 1;
	}
	function x(i: number, count: number): number {
		return PAD.left + (i + 0.5) * (plotW / Math.max(count, 1));
	}
	function bw(count: number, maxW: number): number {
		return Math.max(5, Math.min(maxW, (plotW / Math.max(count, 1)) * 0.56));
	}
	function ySigned(v: number, max: number): number {
		return PAD.top + plotH / 2 - (v / max) * (plotH / 2);
	}
	function linePath(data: Point[], key: string, max: number): string {
		const pts = data
			.map((d, i) => {
				const v = d[key];
				return typeof v === 'number' && Number.isFinite(v) ? `${x(i, data.length)},${ySigned(v, max)}` : '';
			})
			.filter(Boolean);
		return pts.length >= 2 ? `M${pts.join('L')}` : '';
	}

	let isMax = $derived(maxAbs(isData, ['sales']));
	let profitMax = $derived(maxAbs(isData, ['op', 'net']));
	let bsMax = $derived(maxStack(bsData, ['operatingLiabilities', 'nonOperatingLiabilities', 'retainedEarnings', 'otherEquity']));
	let cfMax = $derived(maxAbs(cfData, ['ocf', 'icf', 'fcf']));
</script>

{#if hasFinance}
	<div class="charts">
		<section class="mini">
			<div class="mtitle">IS <span>매출·이익</span></div>
			<svg viewBox="0 0 {W} {H}" preserveAspectRatio="xMidYMid meet">
				<line x1={PAD.left} x2={W - PAD.right} y1={PAD.top + plotH} y2={PAD.top + plotH} stroke="#334155" />
				{#each isData as d, i}
					{@const sales = typeof d.sales === 'number' ? Math.max(0, d.sales) : 0}
					{@const barH = (sales / isMax) * plotH}
					{@const w = bw(isData.length, 26)}
					<rect x={x(i, isData.length) - w / 2} y={PAD.top + plotH - barH} width={w} height={barH} rx="2" fill="#2563eb" opacity="0.7" />
					<text x={x(i, isData.length)} y={H - 5} text-anchor="middle" fill="#64748b" font-size="8">{d.label}</text>
				{/each}
				{#if linePath(isData, 'op', profitMax)}<path d={linePath(isData, 'op', profitMax)} fill="none" stroke="#22c55e" stroke-width="2" />{/if}
				{#if linePath(isData, 'net', profitMax)}<path d={linePath(isData, 'net', profitMax)} fill="none" stroke="#fb923c" stroke-width="1.8" stroke-dasharray="4 3" />{/if}
			</svg>
			<div class="legend"><span class="b"></span>매출 <span class="g"></span>영업이익 <span class="o"></span>순이익</div>
		</section>

		<section class="mini">
			<div class="mtitle">BS <span>자본구조</span></div>
			<svg viewBox="0 0 {W} {H}" preserveAspectRatio="xMidYMid meet">
				{#each bsData as d, i}
					{@const w = bw(bsData.length, 24)}
					{@const a = typeof d.operatingLiabilities === 'number' ? Math.max(0, d.operatingLiabilities) : 0}
					{@const b = typeof d.nonOperatingLiabilities === 'number' ? Math.max(0, d.nonOperatingLiabilities) : 0}
					{@const c = typeof d.retainedEarnings === 'number' ? Math.max(0, d.retainedEarnings) : 0}
					{@const e = typeof d.otherEquity === 'number' ? Math.max(0, d.otherEquity) : 0}
					{@const h1 = (a / bsMax) * plotH}
					{@const h2 = (b / bsMax) * plotH}
					{@const h3 = (c / bsMax) * plotH}
					{@const h4 = (e / bsMax) * plotH}
					<rect x={x(i, bsData.length) - w / 2} y={PAD.top + plotH - h1} width={w} height={h1} fill="#ef4444" opacity="0.74" />
					<rect x={x(i, bsData.length) - w / 2} y={PAD.top + plotH - h1 - h2} width={w} height={h2} fill="#f97316" opacity="0.72" />
					<rect x={x(i, bsData.length) - w / 2} y={PAD.top + plotH - h1 - h2 - h3} width={w} height={h3} fill="#22c55e" opacity="0.74" />
					<rect x={x(i, bsData.length) - w / 2} y={PAD.top + plotH - h1 - h2 - h3 - h4} width={w} height={h4} fill="#14b8a6" opacity="0.74" />
					<text x={x(i, bsData.length)} y={H - 5} text-anchor="middle" fill="#64748b" font-size="8">{d.label}</text>
				{/each}
			</svg>
			<div class="legend"><span class="r"></span>영업부채 <span class="o"></span>비영업 <span class="g"></span>이익잉여 <span class="t"></span>기타자본</div>
		</section>

		<section class="mini">
			<div class="mtitle">CF <span>현금흐름</span></div>
			<svg viewBox="0 0 {W} {H}" preserveAspectRatio="xMidYMid meet">
				<line x1={PAD.left} x2={W - PAD.right} y1={PAD.top + plotH / 2} y2={PAD.top + plotH / 2} stroke="#334155" />
				{#if linePath(cfData, 'ocf', cfMax)}<path d={linePath(cfData, 'ocf', cfMax)} fill="none" stroke="#22c55e" stroke-width="2" />{/if}
				{#if linePath(cfData, 'icf', cfMax)}<path d={linePath(cfData, 'icf', cfMax)} fill="none" stroke="#3b82f6" stroke-width="1.8" stroke-dasharray="4 3" />{/if}
				{#if linePath(cfData, 'fcf', cfMax)}<path d={linePath(cfData, 'fcf', cfMax)} fill="none" stroke="#a78bfa" stroke-width="1.8" stroke-dasharray="2 3" />{/if}
				{#each cfData as d, i}
					<text x={x(i, cfData.length)} y={H - 5} text-anchor="middle" fill="#64748b" font-size="8">{d.label}</text>
				{/each}
			</svg>
			<div class="legend"><span class="g"></span>영업 <span class="b2"></span>투자 <span class="p"></span>재무</div>
		</section>
	</div>
{:else}
	<div class="empty">재무 데이터 없음</div>
{/if}

<style>
	.charts {
		display: grid;
		grid-template-columns: repeat(3, minmax(0, 1fr));
		gap: 8px;
	}
	.mini {
		min-width: 0;
		background: #070b14;
		border: 1px solid #1e2433;
		border-radius: 6px;
		padding: 7px 8px;
		display: flex;
		flex-direction: column;
	}
	.mtitle {
		color: #cbd5e1;
		font-size: 11px;
		font-weight: 700;
	}
	.mtitle span {
		color: #64748b;
		font-size: 9px;
		font-weight: 500;
		margin-left: 4px;
	}
	svg {
		width: 100%;
		height: auto;
		display: block;
		margin-top: 2px;
	}
	.legend {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 4px;
		color: #94a3b8;
		font-size: 8.5px;
		flex-wrap: wrap;
		margin-top: 2px;
	}
	.legend span {
		width: 6px;
		height: 6px;
		border-radius: 2px;
		flex-shrink: 0;
	}
	.b { background: #2563eb; }
	.b2 { background: #3b82f6; }
	.g { background: #22c55e; }
	.o { background: #f97316; }
	.r { background: #ef4444; }
	.p { background: #a78bfa; }
	.t { background: #14b8a6; }
	.empty {
		padding: 24px;
		text-align: center;
		color: #475569;
		font-size: 12px;
		border: 1px dashed #1e2433;
		border-radius: 6px;
	}
</style>
