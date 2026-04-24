<script lang="ts">
	import { base } from '$app/paths';
	import Section from '$lib/components/ui/Section.svelte';
	import Card from '$lib/components/ui/Card.svelte';
	import Eyebrow from '$lib/components/ui/Eyebrow.svelte';
	import MonoNumber from '$lib/components/ui/MonoNumber.svelte';
	import Tag from '$lib/components/ui/Tag.svelte';
	import Bar from '$lib/components/ui/Bar.svelte';
	import Button from '$lib/components/ui/Button.svelte';
	import ToggleGroup from '$lib/components/ui/ToggleGroup.svelte';
	import { fmtKrwFromEok } from '$lib/format/krw';
	import { fmtPct } from '$lib/format/pct';
	import type { PageData } from './$types';

	let { data }: { data: PageData } = $props();

	const allNodes = $derived(((data.ecosystem as any)?.nodes ?? []) as any[]);
	const industries = $derived(((data.ecosystem as any)?.industries ?? []) as any[]);

	// ── 필터 ──
	let industryFilter = $state<string>('all');
	let sizeFilter = $state<'all' | 'large' | 'mid' | 'small'>('all');
	let profitFilter = $state<'all' | 'profitable' | 'loss'>('all');
	let growthFilter = $state<'all' | 'growth' | 'decline'>('all');
	let textQ = $state('');

	const filtered = $derived.by(() => {
		const q = textQ.trim().toLowerCase();
		return allNodes.filter((n) => {
			if (industryFilter !== 'all' && n.industry !== industryFilter) return false;
			if (sizeFilter === 'large' && (n.revenue ?? 0) < 50000) return false;
			if (sizeFilter === 'mid' && ((n.revenue ?? 0) < 5000 || (n.revenue ?? 0) >= 50000)) return false;
			if (sizeFilter === 'small' && (n.revenue ?? 0) >= 5000) return false;
			if (profitFilter === 'profitable' && (n.opMargin ?? -999) <= 0) return false;
			if (profitFilter === 'loss' && (n.opMargin ?? 999) > 0) return false;
			if (growthFilter === 'growth' && (n.revCagr ?? -999) <= 0) return false;
			if (growthFilter === 'decline' && (n.revCagr ?? 999) > 0) return false;
			if (q) {
				const blob = `${n.id} ${n.label} ${n.industryName ?? ''}`.toLowerCase();
				if (!blob.includes(q)) return false;
			}
			return true;
		});
	});

	// ── 정렬 ──
	type SortKey = 'revenue' | 'roe' | 'opMargin' | 'revCagr' | 'debtRatio' | 'label';
	let sortKey: SortKey = $state('revenue');
	let sortDir: 'desc' | 'asc' = $state('desc');

	const sorted = $derived.by(() => {
		const arr = [...filtered];
		arr.sort((a, b) => {
			const sign = sortDir === 'desc' ? -1 : 1;
			const va = a[sortKey] ?? (sortKey === 'label' ? '' : -Infinity);
			const vb = b[sortKey] ?? (sortKey === 'label' ? '' : -Infinity);
			if (typeof va === 'string') return sign * String(va).localeCompare(String(vb));
			return sign * ((va as number) - (vb as number));
		});
		return arr;
	});

	function clickSort(k: SortKey) {
		if (sortKey === k) sortDir = sortDir === 'desc' ? 'asc' : 'desc';
		else { sortKey = k; sortDir = k === 'label' ? 'asc' : 'desc'; }
	}

	const visibleRows = $derived(sorted.slice(0, 50));
	const maxRev = $derived(visibleRows.length ? (visibleRows[0].revenue ?? 1) : 1);

	function resetFilters() {
		industryFilter = 'all';
		sizeFilter = 'all';
		profitFilter = 'all';
		growthFilter = 'all';
		textQ = '';
	}
</script>

<svelte:head>
	<title>Screener · /lab</title>
	<meta name="robots" content="noindex" />
</svelte:head>

<header class="lab-nav">
	<div class="nav-inner">
		<a href="/lab" class="brand">
			<span class="brand-mark">dartlab</span>
			<span class="brand-slash">/</span>
			<span class="brand-ctx">lab · screener</span>
		</a>
		<div class="nav-actions">
			<Button variant="ghost" size="sm" href="{base}/lab/map">/map</Button>
			<Button variant="ghost" size="sm" href="{base}/lab/compare">/compare</Button>
			<Button variant="ghost" size="sm" href="{base}/lab/dashboard/005930">/dashboard</Button>
		</div>
	</div>
</header>

<section class="hero">
	<div class="hero-inner">
		<Eyebrow text="EXPLORE · 종목 스크리너" />
		<h1 class="hero-h1">
			<MonoNumber value={filtered.length.toLocaleString()} size="xl" tone="ink" align="left" />
			<span class="hero-sub-num">사 (전체 {allNodes.length.toLocaleString()} 중)</span>
		</h1>
		<p class="hero-sub">필터 4축 (업종 · 규모 · 수익성 · 성장) + 정렬 5축. 클릭 시 대시보드 이동.</p>
	</div>
</section>

<!-- 필터 -->
<Section eyebrow="FILTER" title="조건" container="max">
	<Card padded>
		<div class="filter-grid">
			<div class="f-cell">
				<span class="dl-label">업종</span>
				<select class="f-select" bind:value={industryFilter}>
					<option value="all">전체</option>
					{#each industries as ind}
						<option value={ind.id}>{ind.name} ({ind.count}사)</option>
					{/each}
				</select>
			</div>

			<div class="f-cell">
				<span class="dl-label">규모 (매출)</span>
				<ToggleGroup
					value={sizeFilter}
					onChange={(v) => (sizeFilter = v as any)}
					options={[
						{ value: 'all', label: '전체' },
						{ value: 'large', label: '대형 (5조+)' },
						{ value: 'mid', label: '중형' },
						{ value: 'small', label: '소형 (5천억-)' }
					]}
					size="sm"
				/>
			</div>

			<div class="f-cell">
				<span class="dl-label">수익성</span>
				<ToggleGroup
					value={profitFilter}
					onChange={(v) => (profitFilter = v as any)}
					options={[
						{ value: 'all', label: '전체' },
						{ value: 'profitable', label: '흑자' },
						{ value: 'loss', label: '적자' }
					]}
					size="sm"
				/>
			</div>

			<div class="f-cell">
				<span class="dl-label">성장</span>
				<ToggleGroup
					value={growthFilter}
					onChange={(v) => (growthFilter = v as any)}
					options={[
						{ value: 'all', label: '전체' },
						{ value: 'growth', label: '성장' },
						{ value: 'decline', label: '역성장' }
					]}
					size="sm"
				/>
			</div>

			<div class="f-cell wide">
				<span class="dl-label">검색</span>
				<input
					type="text"
					placeholder="회사명 · 종목코드"
					bind:value={textQ}
					class="f-text"
				/>
			</div>

			<div class="f-cell" style="display: flex; align-items: flex-end;">
				<Button variant="ghost" size="sm" onclick={resetFilters}>초기화</Button>
			</div>
		</div>
	</Card>
</Section>

<!-- 결과 표 -->
<Section eyebrow="RESULT · 매출 정렬 · 상위 50" title="결과" container="max">
	<Card padded>
		<table class="screener-table">
			<thead>
				<tr>
					<th class="dl-label">#</th>
					<th class="dl-label sort-h" onclick={() => clickSort('label')} class:active={sortKey === 'label'}>
						회사 {#if sortKey === 'label'}<span class="sort-arrow">{sortDir === 'desc' ? '↓' : '↑'}</span>{/if}
					</th>
					<th class="dl-label">업종</th>
					<th class="dl-label sort-h right" onclick={() => clickSort('revenue')} class:active={sortKey === 'revenue'}>
						매출 {#if sortKey === 'revenue'}<span class="sort-arrow">{sortDir === 'desc' ? '↓' : '↑'}</span>{/if}
					</th>
					<th class="dl-label sort-h right" onclick={() => clickSort('roe')} class:active={sortKey === 'roe'}>
						ROE {#if sortKey === 'roe'}<span class="sort-arrow">{sortDir === 'desc' ? '↓' : '↑'}</span>{/if}
					</th>
					<th class="dl-label sort-h right" onclick={() => clickSort('opMargin')} class:active={sortKey === 'opMargin'}>
						OpM {#if sortKey === 'opMargin'}<span class="sort-arrow">{sortDir === 'desc' ? '↓' : '↑'}</span>{/if}
					</th>
					<th class="dl-label sort-h right" onclick={() => clickSort('revCagr')} class:active={sortKey === 'revCagr'}>
						CAGR {#if sortKey === 'revCagr'}<span class="sort-arrow">{sortDir === 'desc' ? '↓' : '↑'}</span>{/if}
					</th>
					<th class="dl-label sort-h right" onclick={() => clickSort('debtRatio')} class:active={sortKey === 'debtRatio'}>
						부채 {#if sortKey === 'debtRatio'}<span class="sort-arrow">{sortDir === 'desc' ? '↓' : '↑'}</span>{/if}
					</th>
					<th class="dl-label">상대</th>
					<th></th>
				</tr>
			</thead>
			<tbody>
				{#each visibleRows as n, i}
					<tr>
						<td><span class="dl-mono dim">{(i + 1).toString().padStart(2, '0')}</span></td>
						<td>
							<a href="{base}/lab/dashboard/{n.id}" class="row-name">
								<span class="dl-mono row-code">{n.id}</span>
								<span class="row-label">{n.label}</span>
							</a>
						</td>
						<td><Tag>{n.industryName ?? '—'}</Tag></td>
						<td style="text-align: right"><MonoNumber value={fmtKrwFromEok(n.revenue)} size="sm" tone="ink" align="right" /></td>
						<td style="text-align: right"><MonoNumber value={fmtPct(n.roe)} size="sm" tone={(n.roe ?? 0) >= 10 ? 'good' : (n.roe ?? 0) >= 0 ? 'flat' : 'bad'} align="right" /></td>
						<td style="text-align: right"><MonoNumber value={fmtPct(n.opMargin)} size="sm" tone={(n.opMargin ?? 0) >= 8 ? 'good' : (n.opMargin ?? 0) >= 0 ? 'flat' : 'bad'} align="right" /></td>
						<td style="text-align: right"><MonoNumber value={fmtPct(n.revCagr)} size="sm" tone={(n.revCagr ?? 0) >= 5 ? 'good' : (n.revCagr ?? 0) >= 0 ? 'flat' : 'bad'} align="right" /></td>
						<td style="text-align: right"><MonoNumber value={fmtPct(n.debtRatio, { digits: 0 })} size="sm" tone={(n.debtRatio ?? 0) <= 100 ? 'good' : (n.debtRatio ?? 0) <= 200 ? 'flat' : 'bad'} align="right" /></td>
						<td style="min-width: 80px"><Bar value={n.revenue ?? 0} max={maxRev} tone="brand" height={4} /></td>
						<td><a href="{base}/lab/dashboard/{n.id}" class="row-arrow" aria-label="이동">→</a></td>
					</tr>
				{/each}
			</tbody>
		</table>

		{#if sorted.length > 50}
			<div class="more">+ {sorted.length - 50} 사 (필터 더 좁히세요)</div>
		{/if}
		{#if filtered.length === 0}
			<div class="empty"><span class="dl-eyebrow">결과 없음 — 필터 조정</span></div>
		{/if}
	</Card>
</Section>

<footer class="lab-foot">
	<Eyebrow text="END · /lab/screener — Phase 3 EXPLORE prototype" />
</footer>

<style>
	.lab-nav {
		position: sticky; top: 0; z-index: 30;
		border-bottom: 1px solid var(--dl-line);
		background: rgba(15, 15, 16, 0.85);
		backdrop-filter: blur(14px);
	}
	.nav-inner {
		max-width: var(--dl-w-max); margin-inline: auto;
		padding: var(--dl-s-3) var(--dl-s-6);
		display: flex; justify-content: space-between; align-items: center;
	}
	.brand { display: inline-flex; align-items: baseline; gap: var(--dl-s-2); text-decoration: none; color: var(--dl-ink); }
	.brand-mark { font-family: var(--dl-font-head); font-weight: 700; font-size: 18px; letter-spacing: -0.02em; }
	.brand-slash { color: var(--dl-ink-faint); font-weight: 300; }
	.brand-ctx { font-family: var(--dl-font-mono); font-size: 11px; text-transform: uppercase; letter-spacing: 0.16em; color: var(--dl-orange); }
	.nav-actions { display: flex; gap: var(--dl-s-1); }

	.hero { padding: var(--dl-s-7) var(--dl-s-6) var(--dl-s-5); }
	.hero-inner { max-width: var(--dl-w-max); margin-inline: auto; }
	.hero-h1 { display: flex; align-items: baseline; gap: var(--dl-s-3); flex-wrap: wrap; font-family: var(--dl-font-ui); font-size: clamp(28px, 4vw, 44px); font-weight: 800; letter-spacing: -0.025em; line-height: 1.1; color: var(--dl-ink-print); margin: var(--dl-s-3) 0 var(--dl-s-3); }
	.hero-sub-num { font-size: 0.6em; font-weight: 500; color: var(--dl-ink-mute); }
	.hero-sub { font-size: 14px; color: var(--dl-ink-mute); line-height: 1.6; max-width: var(--dl-w-article); margin: 0; }

	/* filter */
	.filter-grid { display: grid; grid-template-columns: 1.4fr 1.4fr 1fr 1fr 1.4fr auto; gap: var(--dl-s-4); align-items: end; }
	.f-cell { display: flex; flex-direction: column; gap: var(--dl-s-2); min-width: 0; }
	.f-cell.wide { grid-column: span 1; }
	.f-select, .f-text {
		padding: 8px 12px;
		background: var(--dl-bg-base);
		border: 1px solid var(--dl-line);
		border-radius: var(--dl-r-md);
		color: var(--dl-ink);
		font-family: var(--dl-font-ui);
		font-size: 13px;
	}
	.f-select:focus, .f-text:focus { outline: none; border-color: var(--dl-orange); }

	/* table */
	.screener-table { width: 100%; border-collapse: collapse; font-size: 13px; }
	.screener-table th { text-align: left; padding: var(--dl-s-2) var(--dl-s-3); border-bottom: 1px solid var(--dl-line); font-size: 10px; white-space: nowrap; }
	.screener-table th.right { text-align: right; }
	.screener-table th.sort-h { cursor: pointer; user-select: none; transition: color var(--dl-dur-hover) var(--dl-ease); }
	.screener-table th.sort-h:hover { color: var(--dl-orange); }
	.screener-table th.sort-h.active { color: var(--dl-orange); }
	.sort-arrow { font-size: 10px; margin-left: 2px; }

	.screener-table td { padding: var(--dl-s-2) var(--dl-s-3); border-bottom: 1px solid var(--dl-line); color: var(--dl-ink); }
	.screener-table tr:last-child td { border-bottom: none; }
	.screener-table tr:hover td { background: rgba(255, 255, 255, 0.02); }
	.dim { color: var(--dl-ink-faint); }

	.row-name { display: flex; flex-direction: column; gap: 2px; text-decoration: none; color: inherit; }
	.row-code { font-size: 10px; color: var(--dl-ink-dim); }
	.row-label { font-weight: 500; color: var(--dl-ink-print); }
	.row-arrow { display: inline-flex; align-items: center; justify-content: center; width: 24px; height: 24px; border-radius: var(--dl-r-sm); color: var(--dl-orange); text-decoration: none; transition: background var(--dl-dur-hover) var(--dl-ease); }
	.row-arrow:hover { background: var(--dl-bg-overlay); }

	.more { padding: var(--dl-s-3); text-align: center; font-size: 11px; color: var(--dl-ink-faint); border-top: 1px solid var(--dl-line); margin-top: var(--dl-s-2); }
	.empty { padding: var(--dl-s-6); text-align: center; }

	@media (max-width: 900px) {
		.filter-grid { grid-template-columns: 1fr 1fr; }
	}
	@media (max-width: 560px) {
		.filter-grid { grid-template-columns: 1fr; }
	}
</style>
