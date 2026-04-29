<script lang="ts">
	import { base } from '$app/paths';
	import { fmtPct } from '$lib/format/pct';
	import { loadHfCompanyChanges, type CompanyChange } from '$lib/data/changesRuntime';
	import { loadCompanyRegularFilings, type RegularFiling } from '$lib/data/companyFilingsRuntime';
	import type { DartDb } from '$lib/data/duckdb';
	import { FINANCE_COMPLETED_YEARS, financeMetricKey } from './financeAccounts';
	import { gradeTone, toneColor } from './grade';
	import type { ScanNode } from './types';

	interface Props {
		node: ScanNode;
		db: DartDb | null;
		financeLoading?: boolean;
		onClose: () => void;
	}

	type Point = { year: string; [key: string]: number | string | null };

	let { node, db: _db, financeLoading = false, onClose }: Props = $props();
	let changes = $state<CompanyChange[]>([]);
	let filings = $state<RegularFiling[]>([]);
	let changesLoading = $state(false);
	let filingsLoading = $state(false);

	$effect(() => {
		const code = node.id;
		changesLoading = true;
		void loadHfCompanyChanges(code, 3)
			.then((c) => {
				if (node.id === code) changes = c;
			})
			.catch(() => {
				if (node.id === code) changes = [];
			})
			.finally(() => {
				if (node.id === code) changesLoading = false;
			});
		filingsLoading = true;
		void loadCompanyRegularFilings(code, 5)
			.then((rows) => {
				if (node.id === code) filings = rows;
			})
			.catch(() => {
				if (node.id === code) filings = [];
			})
			.finally(() => {
				if (node.id === code) filingsLoading = false;
			});
	});

	function valueAt(accountId: string, year: string): number | null {
		const value = (node as Record<string, unknown>)[financeMetricKey(accountId, year)];
		return typeof value === 'number' && Number.isFinite(value) ? value : null;
	}

	function wonToT(value: number | null): number | null {
		return value == null ? null : value / 1e12;
	}

	let isData = $derived.by<Point[]>(() =>
		FINANCE_COMPLETED_YEARS.map((year) => ({
			year,
			sales: wonToT(valueAt('sales', year)),
			op: wonToT(valueAt('operating_profit', year)),
			net: wonToT(valueAt('net_income', year))
		}))
	);
	let bsData = $derived.by<Point[]>(() =>
		FINANCE_COMPLETED_YEARS.map((year) => ({
			year,
			currentAssets: wonToT(valueAt('current_assets', year)),
			noncurrentAssets: wonToT(valueAt('noncurrent_assets', year)),
			currentLiabilities: wonToT(valueAt('current_liabilities', year)),
			noncurrentLiabilities: wonToT(valueAt('noncurrent_liabilities', year)),
			equity: wonToT(valueAt('total_stockholders_equity', year))
		}))
	);
	let cfData = $derived.by<Point[]>(() =>
		FINANCE_COMPLETED_YEARS.map((year) => ({
			year,
			ocf: wonToT(valueAt('operating_cashflow', year)),
			icf: wonToT(valueAt('investing_cashflow', year)),
			fcf: wonToT(valueAt('financing_cashflow', year))
		}))
	);

	let hasFinance = $derived([...isData, ...bsData, ...cfData].some((row) => hasNumber(row)));
	let isMax = $derived(maxAbs(isData, ['sales', 'op', 'net']));
	let profitMax = $derived(maxAbs(isData, ['op', 'net']));
	let isOpPath = $derived(linePath(isData, 'op', profitMax));
	let isNetPath = $derived(linePath(isData, 'net', profitMax));
	let bsMax = $derived(maxStack(bsData, ['currentLiabilities', 'noncurrentLiabilities', 'equity']));
	let cfMax = $derived(maxAbs(cfData, ['ocf', 'icf', 'fcf']));
	let latestIs = $derived(isData[isData.length - 1]);
	let latestBs = $derived(bsData[bsData.length - 1]);
	let latestCf = $derived(cfData[cfData.length - 1]);

	const GRADE_COLS = [
		{ key: 'profGrade', label: '수익성' },
		{ key: 'debtGrade', label: '부채' },
		{ key: 'qualGrade', label: '이익질' },
		{ key: 'liqGrade', label: '유동성' },
		{ key: 'govGrade', label: '거버넌스' },
		{ key: 'auditRisk', label: '감사' }
	];

	function hasNumber(row: Record<string, unknown>): boolean {
		return Object.entries(row).some(([key, value]) => key !== 'year' && typeof value === 'number' && Number.isFinite(value));
	}

	function formatDate(value: string): string {
		if (!/^\d{8}$/.test(value)) return value || '—';
		return `${value.slice(0, 4)}.${value.slice(4, 6)}.${value.slice(6, 8)}`;
	}

	function fmtChange(c: CompanyChange): string {
		const types: Record<string, string> = {
			numeric: '재무 정정',
			structural: '구조 변경',
			wording: '문구 수정',
			appeared: '신설',
			disappeared: '삭제'
		};
		return types[c.changeType] || c.changeType;
	}

	function handleKey(e: KeyboardEvent) {
		if (e.key === 'Escape') onClose();
	}

	const W = 360;
	const H = 126;
	const PAD = { top: 10, right: 14, bottom: 22, left: 38 };
	const plotW = W - PAD.left - PAD.right;
	const plotH = H - PAD.top - PAD.bottom;

	function chartValues(data: Point[], keys: string[]): number[] {
		return data.flatMap((d) =>
			keys.map((k) => d[k]).filter((v): v is number => typeof v === 'number' && Number.isFinite(v))
		);
	}
	function maxAbs(data: Point[], keys: string[]): number {
		return Math.max(1, ...chartValues(data, keys).map((v) => Math.abs(v)));
	}
	function maxStack(data: Point[], keys: string[]): number {
		return Math.max(
			1,
			...data.map((d) => keys.reduce((sum, k) => sum + Math.max(0, Number(d[k]) || 0), 0))
		);
	}
	function x(i: number, count: number): number {
		return PAD.left + (i + 0.5) * (plotW / Math.max(count, 1));
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
	function fmtT(v: number | null): string {
		if (v == null) return '—';
		return `${v.toLocaleString('ko-KR', { maximumFractionDigits: 1 })}조`;
	}
	function numAt(row: Point, key: string): number | null {
		const v = row?.[key];
		return typeof v === 'number' && Number.isFinite(v) ? v : null;
	}
</script>

<svelte:window onkeydown={handleKey} />

<aside class="detail" aria-label="회사 디테일">
	<header class="d-head">
		<div class="d-head-left">
			<span class="d-ind-dot" style:background={(node.color as string) || '#475569'}></span>
			<span class="d-label">{node.label}</span>
			<span class="d-id">{node.id}</span>
			<span class="d-ind">{node.industryName}</span>
		</div>
		<div class="d-head-right">
			<a href="{base}/company/{node.id}" class="d-cta">Company 보기</a>
			<button type="button" class="d-close" onclick={onClose} aria-label="닫기 (Esc)">X</button>
		</div>
	</header>

	<div class="d-body">
		<section class="d-section charts">
			<div class="sec-title">재무 그래프</div>
			{#if financeLoading && !hasFinance}
				<div class="loading">로드 중...</div>
			{:else}
				<div class="chart-grid">
					<div class="mini-chart">
						<div class="mini-title">IS</div>
						<svg viewBox="0 0 {W} {H}">
							<line x1={PAD.left} x2={W - PAD.right} y1={PAD.top + plotH} y2={PAD.top + plotH} stroke="#334155" />
							{#each isData as d, i}
								{@const sales = typeof d.sales === 'number' ? d.sales : 0}
								{@const barH = (Math.max(0, sales) / isMax) * plotH}
								<rect x={x(i, isData.length) - 16} y={PAD.top + plotH - barH} width="32" height={barH} rx="2" fill="#2563eb" opacity="0.72" />
								<text x={x(i, isData.length)} y={H - 5} text-anchor="middle" fill="#64748b" font-size="10">{d.year.slice(2)}</text>
							{/each}
							{#if isOpPath}<path d={isOpPath} fill="none" stroke="#22c55e" stroke-width="2" />{/if}
							{#if isNetPath}<path d={isNetPath} fill="none" stroke="#fb923c" stroke-width="2" />{/if}
							<text x="6" y="14" fill="#64748b" font-size="10">매출 {fmtT(isMax)}</text>
							<text x={W - 6} y="14" text-anchor="end" fill="#64748b" font-size="10">이익 {fmtT(profitMax)}</text>
						</svg>
						<div class="legend"><span class="b"></span>매출액 <span class="g"></span>영업이익 <span class="o"></span>당기순이익</div>
						<div class="amount-row">
							<span>매출 {fmtT(numAt(latestIs, 'sales'))}</span>
							<span>영업 {fmtT(numAt(latestIs, 'op'))}</span>
							<span>순익 {fmtT(numAt(latestIs, 'net'))}</span>
						</div>
					</div>
					<div class="mini-chart">
						<div class="mini-title">BS</div>
						<svg viewBox="0 0 {W} {H}">
							{#each bsData as d, i}
								{@const ca = typeof d.currentLiabilities === 'number' ? Math.max(0, d.currentLiabilities) : 0}
								{@const na = typeof d.noncurrentLiabilities === 'number' ? Math.max(0, d.noncurrentLiabilities) : 0}
								{@const eq = typeof d.equity === 'number' ? Math.max(0, d.equity) : 0}
								{@const h1 = (ca / bsMax) * plotH}
								{@const h2 = (na / bsMax) * plotH}
								{@const h3 = (eq / bsMax) * plotH}
								<rect x={x(i, bsData.length) - 18} y={PAD.top + plotH - h1} width="36" height={h1} fill="#ef4444" opacity="0.72" />
								<rect x={x(i, bsData.length) - 18} y={PAD.top + plotH - h1 - h2} width="36" height={h2} fill="#f97316" opacity="0.72" />
								<rect x={x(i, bsData.length) - 18} y={PAD.top + plotH - h1 - h2 - h3} width="36" height={h3} fill="#22c55e" opacity="0.72" />
								<text x={x(i, bsData.length)} y={H - 5} text-anchor="middle" fill="#64748b" font-size="10">{d.year.slice(2)}</text>
							{/each}
							<text x="6" y="14" fill="#64748b" font-size="10">{fmtT(bsMax)}</text>
						</svg>
						<div class="legend"><span class="r"></span>유동부채 <span class="o"></span>비유동부채 <span class="g"></span>자본</div>
						<div class="amount-row">
							<span>유동부채 {fmtT(numAt(latestBs, 'currentLiabilities'))}</span>
							<span>비유동 {fmtT(numAt(latestBs, 'noncurrentLiabilities'))}</span>
							<span>자본 {fmtT(numAt(latestBs, 'equity'))}</span>
						</div>
					</div>
					<div class="mini-chart">
						<div class="mini-title">CF</div>
						<svg viewBox="0 0 {W} {H}">
							<line x1={PAD.left} x2={W - PAD.right} y1={PAD.top + plotH / 2} y2={PAD.top + plotH / 2} stroke="#334155" />
							{#each cfData as d, i}
								{#each ['ocf', 'icf', 'fcf'] as key, j}
									{@const raw = d[key]}
									{@const v = typeof raw === 'number' ? raw : 0}
									{@const h = Math.abs(v / cfMax) * (plotH / 2)}
									<rect x={x(i, cfData.length) - 18 + j * 12} y={v >= 0 ? PAD.top + plotH / 2 - h : PAD.top + plotH / 2} width="10" height={h} rx="1" fill={j === 0 ? '#22c55e' : j === 1 ? '#3b82f6' : '#a78bfa'} opacity="0.78" />
								{/each}
								<text x={x(i, cfData.length)} y={H - 5} text-anchor="middle" fill="#64748b" font-size="10">{d.year.slice(2)}</text>
							{/each}
							<text x="6" y="14" fill="#64748b" font-size="10">{fmtT(cfMax)}</text>
						</svg>
						<div class="legend"><span class="g"></span>영업CF <span class="b"></span>투자CF <span class="p"></span>재무CF</div>
						<div class="amount-row">
							<span>영업 {fmtT(numAt(latestCf, 'ocf'))}</span>
							<span>투자 {fmtT(numAt(latestCf, 'icf'))}</span>
							<span>재무 {fmtT(numAt(latestCf, 'fcf'))}</span>
						</div>
					</div>
				</div>
			{/if}
		</section>

		<section class="d-section grades">
			<div class="sec-title">scan 등급</div>
			<div class="grade-grid">
				{#each GRADE_COLS as g (g.key)}
					{@const v = (node as Record<string, unknown>)[g.key]}
					{@const tone = gradeTone(g.key, v)}
					<div class="grade-cell">
						<span>{g.label}</span>
						{#if v && v !== ''}
							<span class="g-chip" style:color={toneColor(tone)} style:border-color={toneColor(tone)}>{v}</span>
						{:else}
							<span class="g-chip dim">—</span>
						{/if}
					</div>
				{/each}
			</div>
			<div class="delta-row">
				<span>ROE 변화 {typeof node.roeDelta === 'number' ? fmtPct(node.roeDelta, { withSign: true, suffix: '%p' }) : '—'}</span>
				<span>OPM 변화 {typeof node.opMarginDelta === 'number' ? fmtPct(node.opMarginDelta, { withSign: true, suffix: '%p' }) : '—'}</span>
			</div>
		</section>

		<section class="d-section filings">
			<div class="sec-title">최근 정기공시</div>
			{#if filingsLoading}
				<div class="loading">로드 중...</div>
			{:else if filings.length === 0}
				<div class="empty">정기공시 없음</div>
			{:else}
				<div class="filing-list">
					{#each filings as filing (filing.rceptNo)}
						<a class="filing-row" href={filing.url} target="_blank" rel="noreferrer">
							<span class="filing-type">{filing.reportType}</span>
							<span class="filing-date">{formatDate(filing.rceptDate)}</span>
						</a>
					{/each}
				</div>
			{/if}
			{#if !changesLoading && changes.length > 0}
				<div class="change-strip">
					{#each changes.slice(0, 3) as c, i (i)}
						<span>{fmtChange(c)} · {c.sectionTitle}</span>
					{/each}
				</div>
			{/if}
		</section>
	</div>
</aside>

<style>
	.detail {
		flex-shrink: 0;
		background: #0a0e18;
		border: 1px solid #1e2433;
		border-radius: 6px;
		overflow: hidden;
		display: flex;
		flex-direction: column;
		height: 294px;
		max-height: 32vh;
		min-height: 294px;
	}
	.d-head {
		display: flex;
		justify-content: space-between;
		align-items: center;
		gap: 12px;
		padding: 8px 12px;
		background: #0f172a;
		border-bottom: 1px solid #1e2433;
		flex-shrink: 0;
	}
	.d-head-left, .d-head-right {
		display: flex;
		align-items: center;
		gap: 8px;
		min-width: 0;
	}
	.d-ind-dot {
		width: 7px;
		height: 7px;
		border-radius: 50%;
		flex-shrink: 0;
	}
	.d-label {
		font-size: 13px;
		font-weight: 700;
		color: #f1f5f9;
	}
	.d-id, .d-ind {
		font-size: 11px;
		color: #64748b;
	}
	.d-cta {
		padding: 4px 9px;
		font-size: 11px;
		color: #fb923c;
		border: 1px solid rgba(251, 146, 60, 0.3);
		border-radius: 4px;
		text-decoration: none;
	}
	.d-close {
		background: transparent;
		border: none;
		color: #64748b;
		cursor: pointer;
		font-size: 12px;
	}
	.d-body {
		flex: 1;
		min-height: 0;
		display: grid;
		grid-template-columns: minmax(0, 1.8fr) minmax(210px, 0.72fr) minmax(300px, 0.9fr);
		gap: 8px;
		padding: 8px;
		overflow: hidden;
	}
	.d-section {
		min-width: 0;
		min-height: 0;
		background: #050811;
		border: 1px solid #1e2433;
		border-radius: 5px;
		padding: 8px;
		overflow: hidden;
	}
	.sec-title {
		font-size: 10px;
		color: #64748b;
		text-transform: uppercase;
		letter-spacing: 0.05em;
		margin-bottom: 6px;
	}
	.chart-grid {
		display: grid;
		grid-template-columns: repeat(3, minmax(0, 1fr));
		gap: 6px;
	}
	.mini-chart {
		min-width: 0;
		border: 1px solid #1e2433;
		border-radius: 4px;
		padding: 5px;
		background: #070b14;
	}
	.mini-title {
		color: #cbd5e1;
		font-size: 10px;
		font-weight: 700;
		margin-bottom: 2px;
	}
	svg {
		width: 100%;
		height: 132px;
		display: block;
	}
	.legend {
		display: flex;
		align-items: center;
		gap: 4px;
		color: #94a3b8;
		font-size: 9px;
		white-space: nowrap;
		overflow: hidden;
	}
	.legend span {
		width: 6px;
		height: 6px;
		border-radius: 2px;
		flex-shrink: 0;
	}
	.b { background: #2563eb; }
	.g { background: #22c55e; }
	.o { background: #fb923c; }
	.r { background: #ef4444; }
	.p { background: #a78bfa; }
	.amount-row {
		display: grid;
		grid-template-columns: repeat(3, minmax(0, 1fr));
		gap: 4px;
		margin-top: 5px;
		color: #cbd5e1;
		font-size: 9px;
		font-family: 'JetBrains Mono', 'Fira Code', monospace;
		font-variant-numeric: tabular-nums;
	}
	.amount-row span {
		min-width: 0;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	.grade-grid {
		display: grid;
		grid-template-columns: 1fr;
		gap: 4px;
	}
	.grade-cell, .delta-row {
		display: flex;
		justify-content: space-between;
		align-items: center;
		gap: 6px;
		color: #94a3b8;
		font-size: 11px;
		min-width: 0;
	}
	.delta-row {
		margin-top: 8px;
		flex-direction: column;
	}
	.g-chip {
		padding: 1px 6px;
		font-size: 10px;
		font-weight: 700;
		border: 1px solid currentColor;
		border-radius: 3px;
		white-space: nowrap;
		flex-shrink: 0;
	}
	.g-chip.dim {
		color: #475569;
		border-color: #1e2433;
	}
	.filing-list {
		display: flex;
		flex-direction: column;
		gap: 4px;
		min-height: 0;
	}
	.filing-row {
		min-width: 0;
		display: grid;
		grid-template-columns: minmax(0, 1fr) 70px;
		align-items: center;
		gap: 8px;
		padding: 5px 7px;
		background: #0f172a;
		border: 1px solid #1e2433;
		border-radius: 4px;
		text-decoration: none;
	}
	.filing-row:hover {
		border-color: #fb923c;
	}
	.filing-type {
		color: #f1f5f9;
		font-size: 10px;
		font-weight: 700;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	.filing-date {
		color: #64748b;
		font-size: 9px;
		font-family: monospace;
		text-align: right;
	}
	.change-strip {
		margin-top: 7px;
		display: flex;
		flex-direction: column;
		gap: 3px;
		color: #64748b;
		font-size: 9px;
		overflow: hidden;
	}
	.change-strip span {
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	.loading, .empty {
		padding: 20px 8px;
		text-align: center;
		color: #475569;
		font-size: 11px;
	}
	@media (max-width: 1180px) {
		.d-body {
			grid-template-columns: 1fr;
			overflow-y: auto;
		}
		.detail {
			height: 42vh;
			min-height: 294px;
			max-height: 42vh;
		}
		.chart-grid {
			grid-template-columns: 1fr;
		}
	}
</style>
