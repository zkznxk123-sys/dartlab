<script lang="ts">
	// 새 단일-회사 워크스페이스 본체. 기존 routes/dashboard/[code]/sections UI는 사용하지 않는다.
	// 입구만 공유: scan ?company= 모달과 /dashboard/[code]가 같은 새 본체를 연다.
	import { base } from '$app/paths';
	import { LayoutDashboard, FileText, BarChart3, TrendingUp, ExternalLink, X } from 'lucide-svelte';
	import KpiRibbon from '$lib/components/company/KpiRibbon.svelte';
	import OverviewFinanceCharts from './OverviewFinanceCharts.svelte';
	import CompanyFinancePane from './CompanyFinancePane.svelte';
	import CompanyViewerPane from './CompanyViewerPane.svelte';
	import FinanceSignalBoard from './FinanceSignalBoard.svelte';
	import PriceDisclosureTimeline from './PriceDisclosureTimeline.svelte';
	import { loadLiveCompany, type LiveCompanyBundle } from '$lib/browser/companyLive';
	import { loadCompanyFinanceLitePeriods, type CompanyFinancePeriodRow } from '$lib/scan/financeLiteRuntime';
	import { loadCompanyRegularFilings, type RegularFiling } from '$lib/data/companyFilingsRuntime';
	import { fmtKrw, fmtPrice } from '$lib/format/krw';
	import { fmtPct, fmtMul } from '$lib/format/pct';

	let {
		code,
		embedded = false,
		onClose
	}: {
		code: string;
		embedded?: boolean;
		onClose?: () => void;
	} = $props();

	type Tone = 'good' | 'bad' | 'neutral' | 'watch' | 'missing';
	type DashboardMetric = {
		id: string;
		label: string;
		value: string;
		raw: number | null;
		unit: string;
		delta: string;
		deltaTone: Tone;
		tone: Tone;
		period: string | null;
		series: Array<number | null>;
		note?: string;
	};
	type View = 'overview' | 'viewer' | 'finance' | 'price';
	let activeView = $state<View>('overview');
	let bundle = $state<LiveCompanyBundle | null>(null);
	let periods = $state.raw<CompanyFinancePeriodRow[]>([]);
	let filings = $state.raw<RegularFiling[]>([]);
	let loading = $state(true);
	let errorMsg = $state<string | null>(null);

	// code 바뀌면 재로드 (모달 입구 대비). loadLiveCompany 는 로컬 map/companies/{code}.json 경량.
	$effect(() => {
		const c = code;
		loading = true;
		errorMsg = null;
		bundle = null;
		periods = [];
		filings = [];
		void loadLiveCompany(c)
			.then((b) => {
				if (code === c) bundle = b;
			})
			.catch((e) => {
				if (code === c) errorMsg = e instanceof Error ? e.message : String(e);
			})
			.finally(() => {
				if (code === c) loading = false;
			});
		void loadCompanyFinanceLitePeriods(c, fetch, 12).then((r) => {
			if (code === c) periods = r;
		}).catch(() => {});
		void loadCompanyRegularFilings(c, 30).then((r) => {
			if (code === c) filings = r;
		}).catch(() => {});
	});

	const corpName = $derived(bundle?.companyMeta?.name ?? bundle?.companyMeta?.corpName ?? code);
	const industryName = $derived(bundle?.industryMeta?.name ?? bundle?.companyMeta?.ego?.industryName ?? '');

	// ── KPI 리본 (단위-확신 8종: 주가·시총·수익률·PER·PBR·배당·영업이익률·부채비율) ──
	function metric(id: string, label: string, value: string, tone: Tone, sub: string, deltaTone: Tone = 'neutral'): DashboardMetric {
		return { id, label, value, raw: null, unit: '', delta: sub, deltaTone, tone, period: sub, series: [], note: undefined };
	}
	let kpis = $derived.by<DashboardMetric[]>(() => {
		const p = bundle?.price;
		const s = bundle?.summary;
		const r1y = p?.return1y ?? null;
		const debt = s?.debtRatio ?? null;
		return [
			metric('price', '주가', fmtPrice(p?.currentPrice ?? null), p?.currentPrice ? 'neutral' : 'missing', p?.snapshotAt ?? '시세'),
			metric('cashflow', '시가총액', fmtKrw(p?.marketCap ?? null), p?.marketCap ? 'neutral' : 'missing', '시총'),
			metric('net', '1년 수익률', fmtPct(r1y, { withSign: true }), r1y == null ? 'missing' : r1y >= 0 ? 'good' : 'bad', '1Y', r1y == null ? 'neutral' : r1y >= 0 ? 'good' : 'bad'),
			metric('per', 'PER', fmtMul(p?.per ?? null), p?.per ? 'neutral' : 'missing', '주가/순이익'),
			metric('pbr', 'PBR', fmtMul(p?.pbr ?? null), p?.pbr ? 'neutral' : 'missing', '주가/순자산'),
			metric('roe', '배당수익률', fmtPct(p?.dividendYield ?? null), p?.dividendYield ? 'good' : 'missing', '연 배당'),
			metric('opMargin', '영업이익률', fmtPct(s?.opMargin ?? null), s?.opMargin == null ? 'missing' : s.opMargin >= 0 ? 'good' : 'bad', s?.year ? `${s.year}` : '최근'),
			metric('debtRatio', '부채비율', fmtPct(debt), debt == null ? 'missing' : debt > 200 ? 'bad' : debt > 100 ? 'watch' : 'good', s?.year ? `${s.year}` : '최근')
		];
	});

	const NAV: Array<{ id: View; label: string; icon: typeof LayoutDashboard }> = [
		{ id: 'overview', label: '개요', icon: LayoutDashboard },
		{ id: 'viewer', label: '공시뷰어', icon: FileText },
		{ id: 'finance', label: '재무제표', icon: BarChart3 },
		{ id: 'price', label: '주가·밸류', icon: TrendingUp }
	];

	function onNav(id: View) {
		activeView = id;
	}

	function formatDate(value: string): string {
		if (!/^\d{8}$/.test(value)) return value || '—';
		return `${value.slice(0, 4)}.${value.slice(4, 6)}.${value.slice(6, 8)}`;
	}
	function diagTone(tone: string): string {
		if (tone === 'good') return '#34d399';
		if (tone === 'bad') return '#f87171';
		return '#94a3b8';
	}
</script>

<div class="dash" class:embedded>
	<header class="dhead">
		<div class="dhead-left">
			<h1 class="corp">{corpName}</h1>
			<span class="code">{code}</span>
			{#if industryName}<span class="ind">{industryName}</span>{/if}
		</div>
		<div class="dhead-right">
			<a class="hbtn" href={`${base}/viewer/company/${code}`} target="_blank" rel="noreferrer" title="공시뷰어 전체 화면으로 열기">
				<ExternalLink size={13} /> 전체 공시뷰어
			</a>
			{#if embedded && onClose}
				<button type="button" class="hbtn" onclick={onClose} title="닫기">
					<X size={13} /> 닫기
				</button>
			{/if}
		</div>
	</header>

	<div class="body">
		<nav class="rail" aria-label="대시보드 뷰">
			{#each NAV as item (item.id)}
				<button
					type="button"
					class="rail-btn"
					class:active={item.id === activeView}
					onclick={() => onNav(item.id)}
					title={item.label}
				>
					<item.icon size={18} />
					<span>{item.label}</span>
				</button>
			{/each}
		</nav>

		<section class="view">
			{#if loading}
				<div class="state"><div class="spinner"></div><p>{corpName} 데이터 여는 중</p></div>
			{:else if errorMsg}
				<div class="state"><p>로드 실패: {errorMsg}</p></div>
			{:else if bundle}
				{#if activeView === 'overview'}
					<div class="overview">
						<div class="kpi-wrap"><KpiRibbon metrics={kpis} /></div>

						<FinanceSignalBoard {periods} />

						<div class="panel">
							<div class="panel-head"><span>재무 추세</span><small>단위 억원 · 최근 {periods.length}기</small></div>
							<OverviewFinanceCharts {periods} />
						</div>

						<div class="grid2">
							<div class="panel">
								<div class="panel-head"><span>진단</span></div>
								{#if bundle.diagnosis.length}
									<ul class="diag">
										{#each bundle.diagnosis as d (d.key)}
											<li>
												<span class="diag-label">{d.label}</span>
												<span class="diag-val" style:color={diagTone(d.tone)}>{d.value}</span>
											</li>
										{/each}
									</ul>
								{:else}
									<div class="empty">진단 데이터 없음</div>
								{/if}
							</div>

							<div class="panel">
								<div class="panel-head">
									<span>최근 정기공시</span>
									<a class="mini-link" href={`${base}/viewer/company/${code}`}>공시뷰어 ↗</a>
								</div>
								{#if filings.length}
									<div class="filings">
										{#each filings.slice(0, 8) as f (f.rceptNo)}
											<a class="filing" href={f.url} target="_blank" rel="noreferrer">
												<span class="ftitle">{f.reportType}</span>
												<span class="fdate">{formatDate(f.rceptDate)}</span>
											</a>
										{/each}
									</div>
								{:else}
									<div class="empty">정기공시 없음</div>
								{/if}
							</div>
						</div>
					</div>
				{:else if activeView === 'viewer'}
					<CompanyViewerPane {code} {corpName} />
				{:else if activeView === 'finance'}
					<CompanyFinancePane {code} {corpName} />
				{:else if activeView === 'price'}
					<PriceDisclosureTimeline {code} {corpName} {filings} />
				{/if}
			{/if}
		</section>
	</div>
</div>

<style>
	.dash {
		height: 100vh;
		overflow: hidden;
		display: flex;
		flex-direction: column;
		background: #050811;
		color: #f1f5f9;
		padding: 56px 0 0;
	}
	.dash.embedded {
		height: 100%;
		padding: 0;
	}
	.dhead {
		flex-shrink: 0;
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 16px;
		padding: 8px 14px;
		border-bottom: 1px solid #1e2433;
	}
	.dhead-left {
		display: flex;
		align-items: baseline;
		gap: 9px;
		min-width: 0;
	}
	.corp {
		margin: 0;
		font-size: 19px;
		font-weight: 800;
		letter-spacing: -0.02em;
		white-space: nowrap;
	}
	.code {
		font-size: 11px;
		color: #64748b;
		font-family: monospace;
	}
	.ind {
		font-size: 11px;
		color: #94a3b8;
	}
	.hbtn {
		display: inline-flex;
		align-items: center;
		gap: 5px;
		height: 30px;
		padding: 0 10px;
		border: 1px solid #1e2433;
		border-radius: 5px;
		background: #050811;
		color: #94a3b8;
		font-size: 11px;
		text-decoration: none;
		white-space: nowrap;
		cursor: pointer;
	}
	.hbtn:hover {
		border-color: #fb923c;
		color: #fb923c;
	}

	.body {
		flex: 1 1 auto;
		min-height: 0;
		display: grid;
		grid-template-columns: 84px 1fr;
	}
	.rail {
		min-height: 0;
		display: flex;
		flex-direction: column;
		gap: 4px;
		padding: 10px 8px;
		border-right: 1px solid #1e2433;
		overflow-y: auto;
	}
	.rail-btn {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 4px;
		padding: 9px 4px;
		border: 1px solid transparent;
		border-radius: 7px;
		background: transparent;
		color: #64748b;
		font: inherit;
		font-size: 10px;
		cursor: pointer;
	}
	.rail-btn:hover {
		color: #cbd5e1;
		background: #0a0e18;
	}
	.rail-btn.active {
		color: #fb923c;
		border-color: rgba(251, 146, 60, 0.4);
		background: rgba(251, 146, 60, 0.1);
	}

	.view {
		min-width: 0;
		min-height: 0;
		overflow-y: auto;
		padding: 12px 14px;
	}
	.overview {
		display: flex;
		flex-direction: column;
		gap: 12px;
		max-width: 1320px;
		margin: 0 auto;
	}
	.kpi-wrap {
		--company-shell-width: 1320px;
	}
	.panel {
		border: 1px solid #1e2433;
		border-radius: 8px;
		background: rgba(8, 13, 23, 0.7);
		padding: 11px 13px;
	}
	.panel-head {
		display: flex;
		align-items: baseline;
		justify-content: space-between;
		gap: 8px;
		margin-bottom: 9px;
	}
	.panel-head span {
		font-size: 12px;
		font-weight: 700;
		color: #e2e8f0;
	}
	.panel-head small {
		font-size: 10px;
		color: #64748b;
	}
	.mini-link {
		font-size: 10px;
		color: #fb923c;
		text-decoration: none;
		white-space: nowrap;
	}
	.mini-link:hover {
		text-decoration: underline;
	}
	.grid2 {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 12px;
	}
	.diag {
		list-style: none;
		margin: 0;
		padding: 0;
		display: flex;
		flex-direction: column;
		gap: 4px;
	}
	.diag li {
		display: flex;
		justify-content: space-between;
		gap: 8px;
		padding: 4px 0;
		border-bottom: 1px solid rgba(30, 36, 51, 0.5);
		font-size: 12px;
	}
	.diag-label {
		color: #94a3b8;
	}
	.diag-val {
		font-weight: 600;
		font-variant-numeric: tabular-nums;
	}
	.filings {
		display: flex;
		flex-direction: column;
	}
	.filing {
		display: grid;
		grid-template-columns: 1fr 80px;
		gap: 8px;
		align-items: center;
		padding: 5px 2px;
		border-bottom: 1px solid #1e2433;
		text-decoration: none;
	}
	.filing:hover {
		background: rgba(251, 146, 60, 0.06);
	}
	.ftitle {
		color: #f1f5f9;
		font-size: 12px;
		font-weight: 600;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	.fdate {
		color: #64748b;
		font-size: 10px;
		font-family: monospace;
		text-align: right;
	}
	.empty {
		padding: 16px;
		text-align: center;
		color: #475569;
		font-size: 11px;
	}
	.state {
		height: 100%;
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		gap: 12px;
		color: #94a3b8;
		text-align: center;
	}
	.spinner {
		width: 26px;
		height: 26px;
		border: 2px solid #1e2433;
		border-top-color: #fb923c;
		border-radius: 50%;
		animation: spin 0.8s linear infinite;
	}
	@keyframes spin {
		to {
			transform: rotate(360deg);
		}
	}
	@media (max-width: 760px) {
		.grid2 {
			grid-template-columns: 1fr;
		}
		.body {
			grid-template-columns: 64px 1fr;
		}
	}
</style>
