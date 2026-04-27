<script lang="ts">
	/**
	 * 회사 디테일 패널 — 행 click 시 펼침.
	 *
	 *   - 5Y 연간 재무 line chart (5 계정: 매출·영업이익·순이익·자산·부채)
	 *   - 등급 변화 (현재 등급 + roeDelta/opMarginDelta/debtRatioDelta)
	 *   - 최근 공시 3건 (changes.parquet WHERE stockCode=?)
	 *   - "전체 대시보드 보기" CTA
	 */
	import { base } from '$app/paths';
	import LineChart from '$lib/components/blog/LineChart.svelte';
	import { fmtPct } from '$lib/format/pct';
	import {
		loadFinanceTimeseries,
		loadCompanyChanges,
		type FinanceYear,
		type CompanyChange
	} from './duckSql';
	import type { DartDb } from '$lib/data/duckdb';
	import { gradeTone, toneColor } from './grade';
	import type { ScanNode } from './types';

	interface Props {
		node: ScanNode;
		db: DartDb | null;
		onClose: () => void;
	}

	let { node, db, onClose }: Props = $props();

	let finance = $state<FinanceYear[]>([]);
	let changes = $state<CompanyChange[]>([]);
	let loading = $state(false);

	$effect(() => {
		const code = node.id;
		if (!db) {
			finance = [];
			changes = [];
			return;
		}
		loading = true;
		void Promise.all([loadFinanceTimeseries(db, code), loadCompanyChanges(db, code, 3)]).then(
			([f, c]) => {
				finance = f;
				changes = c;
				loading = false;
			}
		);
	});

	// LineChart 입력 형식 (year + 5 계정, 억 단위로 변환)
	let chartData = $derived(
		finance.map((y) => ({
			year: String(y.year),
			'매출': y.revenue != null ? y.revenue / 1e8 : null,
			'영업이익': y.opProfit != null ? y.opProfit / 1e8 : null,
			'순이익': y.netIncome != null ? y.netIncome / 1e8 : null,
			'자산': y.assets != null ? y.assets / 1e8 : null,
			'부채': y.liabilities != null ? y.liabilities / 1e8 : null
		}))
	);

	const GRADE_COLS = [
		{ key: 'profGrade', label: '수익성' },
		{ key: 'debtGrade', label: '부채' },
		{ key: 'qualGrade', label: '이익질' },
		{ key: 'liqGrade', label: '유동성' },
		{ key: 'govGrade', label: '거버넌스' },
		{ key: 'auditRisk', label: '감사' }
	];

	const DELTA_COLS = [
		{ key: 'roeDelta', label: 'ROE Δ', good: 'pos' },
		{ key: 'opMarginDelta', label: '영업이익률 Δ', good: 'pos' },
		{ key: 'debtRatioDelta', label: '부채비율 Δ', good: 'neg' }
	];

	function deltaTone(value: unknown, goodSign: 'pos' | 'neg'): 'good' | 'warn' | 'bad' | 'neutral' {
		if (typeof value !== 'number' || !Number.isFinite(value)) return 'neutral';
		if (Math.abs(value) < 0.1) return 'neutral';
		const isPos = value > 0;
		const isGood = goodSign === 'pos' ? isPos : !isPos;
		return isGood ? 'good' : 'bad';
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
</script>

<svelte:window onkeydown={handleKey} />

<aside class="detail" aria-label="회사 디테일">
	<header class="d-head">
		<div class="d-head-left">
			<span class="d-ind-dot" style:background={(node.color as string) || '#475569'}></span>
			<span class="d-label">{node.label}</span>
			<span class="d-id">{node.id}</span>
			<span class="d-ind">{node.industryName}</span>
			{#if node.role}<span class="d-role">· {node.role}</span>{/if}
		</div>
		<div class="d-head-right">
			<a href="{base}/dashboard/{node.id}" class="d-cta">전체 대시보드 보기 →</a>
			<button type="button" class="d-close" onclick={onClose} aria-label="닫기 (Esc)">✕</button>
		</div>
	</header>

	<div class="d-body">
		<!-- 5Y 재무 line chart -->
		<section class="d-section d-finance">
			<div class="sec-title">5Y 연간 재무 (억원)</div>
			{#if loading}
				<div class="loading">로드 중…</div>
			{:else if chartData.length === 0}
				<div class="empty">재무 시계열 데이터 없음 — DuckDB 비활성 또는 finance-lite parquet 미적재</div>
			{:else}
				<div class="chart-wrap">
					<LineChart
						data={chartData}
						unit="억원"
						keys={['매출', '영업이익', '순이익', '자산', '부채']}
						colors={['#3b82f6', '#22c55e', '#fb923c', '#a78bfa', '#ef4444']}
						height={220}
					/>
				</div>
			{/if}
		</section>

		<!-- 등급 + 변화 -->
		<section class="d-section d-grades">
			<div class="sec-title">scan 등급</div>
			<div class="grade-grid">
				{#each GRADE_COLS as g (g.key)}
					{@const v = (node as Record<string, unknown>)[g.key]}
					{@const tone = gradeTone(g.key, v)}
					<div class="grade-cell">
						<span class="g-label">{g.label}</span>
						{#if v && v !== ''}
							<span class="g-chip" style:color={toneColor(tone)} style:border-color={toneColor(tone)}
								>{v}</span
							>
						{:else}
							<span class="g-chip dim">—</span>
						{/if}
					</div>
				{/each}
			</div>

			<div class="sec-title delta-title">전기 대비 변화</div>
			<div class="delta-grid">
				{#each DELTA_COLS as d (d.key)}
					{@const v = (node as Record<string, unknown>)[d.key] as number | undefined | null}
					{@const tone = deltaTone(v, d.good as 'pos' | 'neg')}
					<div class="delta-cell">
						<span class="g-label">{d.label}</span>
						<span class="d-val" style:color={toneColor(tone)}>
							{typeof v === 'number' && Number.isFinite(v)
								? fmtPct(v, { withSign: true, suffix: '%p' })
								: '—'}
						</span>
					</div>
				{/each}
			</div>
		</section>

		<!-- 최근 공시 변경 -->
		<section class="d-section d-changes">
			<div class="sec-title">최근 공시 변경</div>
			{#if loading}
				<div class="loading">로드 중…</div>
			{:else if changes.length === 0}
				<div class="empty">최근 공시 변경 없음</div>
			{:else}
				<ul class="change-list">
					{#each changes as c, i (i)}
						<li class="change-item">
							<div class="ch-period">{c.fromPeriod} → {c.toPeriod}</div>
							<div class="ch-section">{c.sectionTitle}</div>
							<div class="ch-type">{fmtChange(c)}</div>
						</li>
					{/each}
				</ul>
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
		max-height: 360px;
	}
	.d-head {
		display: flex;
		justify-content: space-between;
		align-items: center;
		gap: 12px;
		padding: 10px 14px;
		background: #0f172a;
		border-bottom: 1px solid #1e2433;
		flex-shrink: 0;
	}
	.d-head-left {
		display: flex;
		align-items: baseline;
		gap: 10px;
		flex-wrap: wrap;
	}
	.d-head-right {
		display: flex;
		align-items: center;
		gap: 8px;
		flex-shrink: 0;
	}
	.d-ind-dot {
		width: 8px;
		height: 8px;
		border-radius: 50%;
		display: inline-block;
		align-self: center;
	}
	.d-label {
		font-size: 14px;
		font-weight: 600;
		color: #f1f5f9;
	}
	.d-id {
		font-size: 11px;
		font-family: monospace;
		color: #64748b;
	}
	.d-ind {
		font-size: 11px;
		color: #94a3b8;
	}
	.d-role {
		font-size: 10px;
		color: #64748b;
	}
	.d-cta {
		padding: 5px 10px;
		font-size: 11px;
		color: #fb923c;
		background: rgba(251, 146, 60, 0.08);
		border: 1px solid rgba(251, 146, 60, 0.3);
		border-radius: 4px;
		text-decoration: none;
		font-weight: 500;
	}
	.d-cta:hover {
		background: rgba(251, 146, 60, 0.16);
		color: #f1f5f9;
	}
	.d-close {
		background: transparent;
		border: none;
		color: #64748b;
		cursor: pointer;
		font-size: 14px;
		padding: 4px 6px;
	}
	.d-close:hover {
		color: #fb923c;
	}

	.d-body {
		flex: 1;
		min-height: 0;
		overflow-y: auto;
		display: grid;
		grid-template-columns: 1.6fr 1fr 1fr;
		gap: 10px;
		padding: 12px;
	}
	@media (max-width: 1024px) {
		.d-body {
			grid-template-columns: 1fr;
		}
	}

	.d-section {
		background: #050811;
		border: 1px solid #1e2433;
		border-radius: 5px;
		padding: 10px 12px;
	}
	.sec-title {
		font-size: 10px;
		color: #64748b;
		text-transform: uppercase;
		letter-spacing: 0.05em;
		margin-bottom: 8px;
	}
	.delta-title {
		margin-top: 12px;
	}
	.loading,
	.empty {
		padding: 24px 8px;
		text-align: center;
		color: #475569;
		font-size: 11px;
	}
	.chart-wrap {
		font-size: 10px;
	}

	.grade-grid {
		display: grid;
		grid-template-columns: repeat(2, 1fr);
		gap: 6px 12px;
	}
	.delta-grid {
		display: grid;
		grid-template-columns: 1fr;
		gap: 4px;
	}
	.grade-cell,
	.delta-cell {
		display: flex;
		justify-content: space-between;
		align-items: center;
		font-size: 11px;
	}
	.g-label {
		color: #94a3b8;
	}
	.g-chip {
		display: inline-block;
		padding: 1px 7px;
		font-size: 10px;
		font-weight: 600;
		border: 1px solid currentColor;
		border-radius: 3px;
		letter-spacing: -0.01em;
	}
	.g-chip.dim {
		color: #475569;
		border-color: #1e2433;
	}
	.d-val {
		font-family: monospace;
		font-size: 11px;
		font-weight: 600;
		font-variant-numeric: tabular-nums;
	}

	.change-list {
		list-style: none;
		padding: 0;
		margin: 0;
		display: flex;
		flex-direction: column;
		gap: 8px;
	}
	.change-item {
		padding: 6px 8px;
		background: #0f172a;
		border-radius: 4px;
		display: flex;
		flex-direction: column;
		gap: 2px;
	}
	.ch-period {
		font-size: 10px;
		font-family: monospace;
		color: #64748b;
	}
	.ch-section {
		font-size: 11px;
		color: #cbd5e1;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	.ch-type {
		font-size: 9px;
		color: #fb923c;
		font-family: monospace;
	}
</style>
