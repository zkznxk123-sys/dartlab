<script lang="ts">
	import type {
		CompanyChange,
		CompanyRelations,
		FinMode,
		InvestmentTrendYear,
		InvestmentsView,
		LiveCompanyReportFact,
		NonRegularFiling,
		ProductIndexItem,
		RegularFiling,
		ShareholderReturnYear,
		StmtKind,
		TerminalFinanceBundle,
		WorkforceYear
	} from '@dartlab/ui-contracts';
	import { useDartLabRuntime } from '@dartlab/ui-runtime';
	import type { Company, Lang, Universe, UniversePercentile } from '../lib/types';
	import type { TerminalHosts } from '../lib/hosts';
	import { gradeTone } from '../lib/engine';
	import Panel from '../ui/Panel.svelte';
	import ViewerOverlay from './ViewerOverlay.svelte'; // 얇은 셸 — 본체(ViewerStudio)는 셸 주입 lazy 로더
	import { viewerEntry } from '../lib/viewerEntry.svelte'; // 중앙 "공시뷰어" 버튼 신호 구독
	import { disclosureFocus } from '../lib/disclosureFocus.svelte'; // 주가차트 공시 dot 클릭 → 그 날짜 행 스크롤+하이라이트
	// 정량재무제표 = 공시뷰어 FinanceDialog 그대로 (한몸두입구) — 셸 주입 lazy 로더, 터미널 청크 무증가
	import { tx, txc, chgClass, sign, toneClass, fmtNum } from '../ui/helpers';
	import { fmtKRW } from '../lib/engine';
	import type { ListedLookup } from '../lib/holdings'; // 피출자사명→상장 종목 해소 hook 타입

	interface Props {
		co: Company;
		lang: Lang;
		hosts: TerminalHosts;
		repoUrl: string; // 셸 brand repo URL — 공시뷰어 오버레이(임베드 이슈링크)로 관통.
		onPick: (code: string) => void;
		lookupListed: ListedLookup; // 피출자사명→상장 종목 해소(출자 다이얼로그 시가 환산·클릭 이동)
		percentileIn: (code: string, universe: Universe) => UniversePercentile | null; // 유니버스 교차 백분위(상세보기 다이얼로그)
	}
	let { co, lang, hosts, repoUrl, onPick, lookupListed, percentileIn }: Props = $props();
	const rt = useDartLabRuntime();
	const base = rt.env.basePath;
	let viewerOpen = $state(false); // 공시뷰어 인터미널 오버레이 (정기공시 패널 ⤢)
	let holdingsOpen = $state(false); // 출자 관계 분석 전체화면 (타법인 출자 패널 ⤢)
	let tablesOpen = $state(false); // 재무제표 원표 모달 (재무 패널 ⤢)
	let pctCrossOpen = $state(false); // 유니버스 교차 백분위 다이얼로그 (업종 내 백분위 패널 → 상세보기)
	// 중앙 "공시뷰어" 버튼 신호(viewerEntry.pulse) 구독 — pulse 변할 때만 오버레이를 연다. seenPulse 는
	// 비반응 plain let(추적 0)이라 viewerOpen 쓰기가 effect 를 재발화시키지 않음(루프 없음).
	let seenViewerPulse = viewerEntry.pulse;
	$effect(() => {
		const p = viewerEntry.pulse;
		if (p !== seenViewerPulse) {
			seenViewerPulse = p;
			viewerOpen = true;
		}
	});
	// 주가차트 공시 dot 클릭(disclosureFocus.pulse) → 그 날짜 행을 정기/비정기 공시목록에서 스크롤·하이라이트(원문 링크 아님).
	// seenFocusPulse = 비반응 plain let — flashDate 쓰기가 effect 를 재발화시키지 않음(viewerEntry 동일 패턴, 루프 없음).
	const fdate = (s: string) => s.replace(/\D/g, '').slice(0, 8); // YYYY-MM-DD → YYYYMMDD (행 data-fdate 와 비교 키)
	let filingWrap = $state<HTMLElement | null>(null); // 정기‖비정기 공시 2분할 컨테이너 — querySelector 범위 한정
	let flashDate = $state<string | null>(null);
	let seenFocusPulse = disclosureFocus.pulse;
	let flashTimer: ReturnType<typeof setTimeout> | null = null;
	$effect(() => {
		const p = disclosureFocus.pulse;
		if (p === seenFocusPulse) return;
		seenFocusPulse = p;
		const d = disclosureFocus.date;
		if (!d) return;
		if (flashTimer) clearTimeout(flashTimer);
		flashDate = null; // 같은 날짜 재클릭도 class off→on 으로 애니메이션 재생되도록 먼저 해제
		requestAnimationFrame(() => {
			flashDate = d;
			const row = filingWrap?.querySelector(`[data-fdate="${d}"]`) as HTMLElement | null;
			if (row) {
				// ① 내부 300px filingList 를 스크롤해 그 날짜 행을 박스 중앙에 보이게(즉시) — 패널 outer 위치는 안 변함.
				const list = row.closest('.filingList') as HTMLElement | null;
				if (list) {
					const lr = list.getBoundingClientRect();
					const rr = row.getBoundingClientRect();
					list.scrollTop += rr.top + rr.height / 2 - (lr.top + lr.height / 2);
				}
				// ② 우측 컬럼을 스크롤해 그 300px 박스(filingList)를 컬럼 뷰포트 세로 중앙에 둔다 — 정기/비정기 동일 Y라 위치 일관.
				const col = row.closest('.col') as HTMLElement | null;
				// 300px 박스 자체 = list (위 ①에서 이미 해소) — 컬럼 중앙 정렬에 재사용
				if (col && list) {
					const cr = col.getBoundingClientRect();
					const lr2 = list.getBoundingClientRect();
					col.scrollBy({ top: lr2.top + lr2.height / 2 - (cr.top + cr.height / 2), behavior: 'smooth' });
				}
			}
			flashTimer = setTimeout(() => (flashDate = null), 3600);
		});
	});
	const localViewerHref = $derived(rt.viewer.urlForCompany(co.code));
	const viewerHref = $derived(localViewerHref ?? `${base}/viewer/company/${co.code}`);
	const externalTarget = $derived(localViewerHref ? undefined : '_blank');
	const externalRel = $derived(localViewerHref ? undefined : 'noopener');
	const tcls = (t: string) => (({ up: 'tUp', good: 'tGood', neutral: 'tNeu', warn: 'tWarn', down: 'tDn' }) as Record<string, string>)[t] || 'tNeu';

	// DART 정기보고서 팩트 + 공시 변경 (DuckDB report parquet 재사용, 온디맨드)
	let reportFacts = $state<LiveCompanyReportFact[]>([]);
	let disclChanges = $state<CompanyChange[]>([]);
	let relations = $state<CompanyRelations | null>(null);
	let regFilings = $state<RegularFiling[]>([]);
	let nonRegFilings = $state<NonRegularFiling[]>([]);
	let nonRegState = $state<'loading' | 'ready' | 'empty'>('loading');
	let factsState = $state<'loading' | 'ready' | 'empty'>('loading');
	$effect(() => {
		const code = co.code;
		factsState = 'loading';
		reportFacts = [];
		disclChanges = [];
		relations = null;
		regFilings = [];
		nonRegFilings = [];
		nonRegState = 'loading';
		finBundle = null;
		wf = [];
		srs = [];
		inv = null;
		invTrend = [];
		let cancelled = false;
		rt.finance.bundle(code).then((b) => {
			if (!cancelled) finBundle = b;
		});
		// 정기보고서 3패널 — 독립 스트림-인 (가벼운 인력·배당 먼저, 무거운 출자 나중)
		rt.report.workforce(code).then((b) => {
			if (!cancelled) wf = b ?? [];
		});
		rt.report.shareholderReturn(code).then((b) => {
			if (!cancelled) srs = b ?? [];
		});
		rt.report.investments(code).then((b) => {
			if (cancelled) return;
			inv = b?.latest ?? null;
			invTrend = b?.trend ?? [];
		});
		rt.company.reportFacts(code).then((f) => {
			if (cancelled) return;
			reportFacts = f;
			factsState = f.length ? 'ready' : 'empty';
		});
		rt.scan.changes(code, 8).then((c) => {
			if (!cancelled) disclChanges = c;
		});
		rt.company.relations(code).then((r) => {
			if (!cancelled) relations = r;
		});
		rt.filing.regular(code, 500).then((f) => {
			if (!cancelled) regFilings = f;
		});
		rt.filing.nonRegular(code).then((f) => {
			if (cancelled) return;
			nonRegFilings = f;
			nonRegState = f.length ? 'ready' : 'empty';
		});
		return () => {
			cancelled = true;
		};
	});

	// 재무제표 — c.panel 전 기간(분기/연간 토글). 요약 탭 폐지, 손익·재무상태·현금흐름·비용·비율.
	let stmt = $state<StmtKind | 'RT'>('IS');
	let finMode = $state<FinMode>('quarter');
	let finBundle = $state<TerminalFinanceBundle | null>(null);
	const tabs = [{ k: 'IS', kr: '손익', en: 'IS' }, { k: 'BS', kr: '재무상태', en: 'BS' }, { k: 'CF', kr: '현금흐름', en: 'CF' }, { k: 'RT', kr: '비율', en: 'Ratios' }] as const;
	const finModeLabel: Record<FinMode, string> = { ttm: 'TTM', quarter: '분기', annual: '연간' };
	const finView = $derived(finBundle ? (finBundle.views[finMode] ?? finBundle.views[finBundle.defaultMode]) : null);
	const KEY_ROWS = ['operatingIncome', 'netIncome', 'assets', 'equity', 'liabilities', 'cfOperating'];
	// 최신 기간부터(역순) 표시 — 차트는 오름차순 유지, 표만 reverse.
	const dispPeriods = $derived(finView ? finView.periods.slice().reverse() : []);
	const stmtRows = $derived(finView ? (stmt === 'RT' ? finView.ratios : finView.statements[stmt as StmtKind]) : []);
	// 표 단위 자동 — 조 고정이면 중형사 행 대부분이 0.0~0.1 소수점 범벅. 최대 절대값 50조 미만이면
	// 억(콤마·정수, FnGuide 관례) 전환 — 초대형사만 조 유지 (비율 탭 제외).
	const finUnitEok = $derived.by(() => {
		if (!finView) return false;
		let m = 0;
		for (const k of ['IS', 'BS', 'CF'] as StmtKind[]) for (const r of finView.statements[k]) for (const v of r.values) if (v != null && Math.abs(v) > m) m = Math.abs(v);
		return m > 0 && m < 50;
	});
	const finUnit = $derived(finUnitEok ? '억' : '조');
	const finVal = (v: number | null): string => (v == null ? '—' : finUnitEok ? fmtNum(v * 1e4, 0) : fmtNum(v, 1));

	// 정기보고서 시계열 (인력·주주환원·타법인출자) — runtime ReportPort, 패널별 독립 로드.
	// 구역 규칙(Terminal.svelte): 우측 = 테이블·수치·정성만, 그래프 금지 — 시계열 그래프는 중앙 재무 전체화면 탭.
	let wf = $state<WorkforceYear[]>([]);
	let srs = $state<ShareholderReturnYear[]>([]);
	let inv = $state<InvestmentsView | null>(null);
	let invTrend = $state<InvestmentTrendYear[]>([]); // 출자 추이 — 다이얼로그 보조(자본 잠김 방향)
	const wfLast = $derived(wf.length ? wf[wf.length - 1] : null);
	// 연간 매출(조) ÷ 인원 = 1인당 매출(억) — finBundle annual 과 연도 매칭 (추가 fetch 없음)
	const revByYear = $derived.by<Map<string, number>>(() => {
		const out = new Map<string, number>();
		const av = finBundle?.views.annual;
		if (!av) return out;
		const row = av.statements.IS.find((r) => r.key === 'revenue');
		if (!row) return out;
		av.periods.forEach((p, i) => {
			const m = p.match(/^FY(\d{2})$/);
			const v = row.values[i];
			if (m && v != null) out.set('20' + m[1], v);
		});
		return out;
	});
	const revPerEmp = (w: { year: string; total: number | null }): number | null => {
		const rev = revByYear.get(w.year);
		return rev != null && w.total ? +((rev * 1e12) / w.total / 1e8).toFixed(1) : null; // 억
	};
	const srLast = $derived(srs.length ? srs[srs.length - 1] : null);
	const fmtShares = (v: number | null): string => (v == null ? '—' : v >= 1e8 ? (v / 1e8).toFixed(1) + '억주' : v >= 1e4 ? (v / 1e4).toFixed(0) + '만주' : v.toLocaleString() + '주');

	const risks = $derived(co.risks);
	const pc = $derived(co.percentile);
	const pcCol = (p: number) => (p >= 80 ? 'var(--up)' : p >= 55 ? 'var(--good)' : p >= 35 ? 'var(--warn)' : 'var(--dn)');
	const pcFmtV = (m: { unit: string; v: number | null }) =>
		m.v == null
			? '—'
			: m.unit === 'rev'
				? (m.v / 1e12).toFixed(1) + '조'
				: m.unit === '배'
					? m.v.toFixed(1) + '배'
					: m.unit === '일'
						? m.v.toFixed(0) + '일'
						: m.unit === ''
							? m.v.toFixed(2)
							: m.v.toFixed(1) + (m.unit === '%' ? '%' : '');

	const cr = $derived(co.credit);
	const ch = $derived(co.changes);
	const chMax = $derived(Math.max(...ch.map((c) => (c.v == null ? 0 : Math.abs(c.v))), 1));
	const peers = $derived(co.peers);
	const peerMax = $derived(Math.max(...peers.map((p) => p.revenue || 0), 1));
	const e = $derived(co.eco);
	const govCells = $derived([
		{ l: lang === 'en' ? 'GOV' : '거버넌스', v: e.govGrade || '—', t: gradeTone('gov', e.govGrade) },
		{ l: lang === 'en' ? 'STABILITY' : '경영안정', v: e.stability || '—', t: gradeTone('stab', e.stability) },
		{ l: lang === 'en' ? 'OWNER %' : '대주주', v: e.holderPct != null ? e.holderPct.toFixed(1) + '%' : '—', t: 'neutral' },
		{ l: lang === 'en' ? 'OWNER Δ' : '지분변화', v: e.holderChange != null ? sign(e.holderChange, 1) + '%p' : '—', t: 'neutral' },
		{ l: lang === 'en' ? 'AUDIT' : '감사위험', v: e.auditRisk || (lang === 'en' ? 'n/a' : '해당없음'), t: gradeTone('audit', e.auditRisk) },
		{ l: lang === 'en' ? 'QUALITY' : '이익질', v: e.qualGrade || '—', t: gradeTone('qual', e.qualGrade) },
		{ l: lang === 'en' ? 'LIQUID' : '유동성', v: e.liqGrade || '—', t: gradeTone('liq', e.liqGrade) }
	]);
	// 현금흐름 실수치 (조) — 패널 제목 '현금흐름' 충족(기존엔 패턴 라벨만). FCF = 영업+투자.
	const cf = $derived(co.financials.cf);
	const cfCells = $derived([
		{ l: lang === 'en' ? 'CFO' : '영업CF', v: cf.op, good: cf.op != null ? cf.op > 0 : null },
		{ l: lang === 'en' ? 'CFI' : '투자CF', v: cf.inv, good: null },
		{ l: lang === 'en' ? 'CFF' : '재무CF', v: cf.fin, good: null },
		{ l: 'FCF', v: cf.fcf, good: cf.fcf != null ? cf.fcf > 0 : null }
	]);
	// 전년 대비 모멘텀 델타 (방향 신호). inv=true → 낮을수록 양호(부채). null 은 사전 제거(타입 확정).
	const govDeltas = $derived(
		([
			{ l: lang === 'en' ? 'Rev YoY' : '매출 YoY', v: e.revenueYoyPct ?? null, u: '%', inv: false },
			{ l: 'ROE Δ', v: e.roeDelta ?? null, u: '%p', inv: false },
			{ l: lang === 'en' ? 'OPM Δ' : '영업益 Δ', v: e.opMarginDelta ?? null, u: '%p', inv: false },
			{ l: lang === 'en' ? 'Debt Δ' : '부채 Δ', v: e.debtRatioDelta ?? null, u: '%p', inv: true }
		] as { l: string; v: number | null; u: string; inv: boolean }[]).filter(
			(d): d is { l: string; v: number; u: string; inv: boolean } => d.v != null
		)
	);
	const s = $derived(co.story);
	const dartUrl = 'https://dart.fss.or.kr/dsab007/main.do';
	let corpMeta = $state<Record<string, ProductIndexItem> | null>(null);
	rt.company.productIndex().then((m) => (corpMeta = m));
	const homepage = $derived(corpMeta?.[co.code]?.homepage ?? null);
	const homepageHost = $derived(homepage ? homepage.replace(/^https?:\/\//, '').replace(/\/$/, '') : '');
	const lastYr = $derived(co.income.periods[0]);
	const firstYr = $derived(co.income.periods[co.income.periods.length - 1]);
	const conf = $derived(cr.healthScore >= 70 ? 'HIGH' : 'MEDIUM');
</script>

<!-- RISK FLAGS -->
<Panel {lang} className="eCredit" prov="real" title={{ kr: '리스크 경고등', en: 'RISK FLAGS' }} sub={{ kr: 'ecosystem', en: 'ecosystem' }}>
	{#snippet right()}<span><b class="tDn">{risks.filter((r) => r.lv === 'red').length}</b> <b class="tWarn">{risks.filter((r) => r.lv === 'yellow').length}</b></span>{/snippet}
	<div class="riskWrap">
		{#each risks as r, i (i)}
			<div class={'riskRow ' + r.lv}><span class={'riskDot ' + r.lv}></span><span class="riskName">{lang === 'en' ? r.en : r.kr}</span>{#if r.d}<span class="riskDetail">{r.d}</span>{/if}</div>
		{/each}
	</div>
</Panel>

<!-- PERCENTILE -->
{#if pc && pc.metrics.length}
	<Panel {lang} className="eQuant" prov="real" title={{ kr: '업종 내 백분위', en: 'INDUSTRY PERCENTILE' }} sub={{ kr: pc.industry + ' ' + pc.n + '사', en: pc.industry + ' n=' + pc.n }} flush>
		{#snippet right()}<button class="finFullBtn" onclick={() => (pctCrossOpen = true)} title={lang === 'en' ? 'cross-universe percentile (industry · market · all listed)' : '유니버스 교차 백분위 — 업종·시장·전체상장사'}>{lang === 'en' ? 'detail' : '상세보기'}</button>{/snippet}
		<div class="pctList">
			{#each pc.metrics.filter((m) => m.axis !== 'gov') as m (m.en)}
				<div class="pctRow">
					<span class="pctName">{txc(m, lang)}</span>
					<div class="pctTrack"><div class="pctFill" style={`width:${m.p}%;background:${pcCol(m.p)}`}></div><div class="pctMark" style="left:50%"></div></div>
					<span class="pctVal"><b style={`color:${pcCol(m.p)}`}>{lang === 'en' ? 'top ' + (100 - m.p + 1) + '%' : '상위 ' + (100 - m.p + 1) + '%'}</b> <span class="dim">{pcFmtV(m)}</span></span>
				</div>
			{/each}
		</div>
		<div class="pctNote">{lang === 'en' ? 'percentile across industry peers · ecosystem' : '동종업종 전 종목 대비 위치 · ecosystem'}</div>
	</Panel>
{/if}

<!-- 유니버스 교차 백분위 — 업종/시장/전체상장사 한 좌표(분포 사실만, 판정 0). lazy: 닫혀 있으면 청크 무증가 -->
{#if pctCrossOpen}
	{#await import('./PercentileCrossDialog.svelte') then { default: PercentileCrossDialog }}
		<PercentileCrossDialog {co} {lang} {percentileIn} onClose={() => (pctCrossOpen = false)} />
	{/await}
{/if}

<!-- FINANCIALS -->
<Panel {lang} className="eAnalysis" prov="real" title={{ kr: '재무제표', en: 'FINANCIAL STATEMENTS' }} sub={finView ? { kr: 'c.panel · ' + finModeLabel[finMode] + ' · ' + finView.periods.length + '기 · ' + finUnit, en: 'c.panel · ' + finMode + ' · ' + finView.periods.length + 'p' } : { kr: 'c.panel', en: 'c.panel' }} flush>
	{#snippet right()}
		{#if finBundle && finBundle.modes.length > 1}
			<span class="segGroup mini">{#each finBundle.modes as m (m)}<button class={finMode === m ? 'seg on' : 'seg'} onclick={() => (finMode = m)}>{lang === 'en' ? m.toUpperCase() : finModeLabel[m]}</button>{/each}</span>
		{/if}
		<button class="finFullBtn" onclick={() => (tablesOpen = true)} title={lang === 'en' ? 'quantitative statements (viewer dialog)' : '정량재무제표 — 공시뷰어와 동일 (IS/BS/CF/CIS/자본변동 · 연결/개별)'}>⤢</button>
	{/snippet}
	<div class="finTabs">{#each tabs as t (t.k)}<button class={'finTab ' + (stmt === t.k ? 'on' : '')} onclick={() => (stmt = t.k)}>{lang === 'en' ? t.en : t.kr}</button>{/each}</div>
	{#if finView}
		<div class="finScroll finScrollX"><table class="finTable">
			<thead><tr><th class="finAcct">{lang === 'en' ? 'ACCOUNT' : '계정'}</th>{#each dispPeriods as p (p)}<th class="r">{p}</th>{/each}</tr></thead>
			<tbody>
				{#each stmtRows as r (r.key)}
					<tr class={KEY_ROWS.includes(r.key) ? 'finKey' : ''}>
						<td class="finAcct">{lang === 'en' ? r.en : r.kr}{#if r.unit}<span class="finUnit">{r.unit}</span>{/if}</td>
						{#each r.values.slice().reverse() as val, i (i)}<td class={'r mono ' + (val != null && val < 0 ? 'tDn' : '')}>{val == null ? '—' : stmt === 'RT' ? fmtNum(val, 1) : finVal(val)}</td>{/each}
					</tr>
				{/each}
			</tbody>
		</table></div>
	{:else}
		<div class="chartLoad" style="height:90px">{lang === 'en' ? 'loading statements …' : '재무제표 불러오는 중 …'}</div>
	{/if}
	<div class="finNote">c.panel · {finView ? finView.periods.length + (lang === 'en' ? 'p' : '기') : '—'} · {finUnit} KRW</div>
</Panel>

<!-- DART 정기보고서 팩트 (배당·자사주·임원·감사·대주주·회사채 — report parquet) -->
<Panel {lang} className="eCredit" prov="real" title={{ kr: 'DART 정기보고서 팩트', en: 'DART REPORT FACTS' }} sub={{ kr: 'report · 공시원문', en: 'report · filings' }} flush>
	{#snippet right()}<span class="dim">{factsState === 'ready' ? reportFacts.length : ''}</span>{/snippet}
	{#if factsState === 'ready'}
		<div class="factGrid">
			{#each reportFacts as f (f.key)}
				<div class="factRow">
					<span class="factL">{f.label}</span>
					<span class="factV mono">{f.value}</span>
					{#if f.detail}<span class="factD">{f.detail}</span>{/if}
				</div>
			{/each}
		</div>
	{:else if factsState === 'loading'}
		<div class="storyEmpty">{lang === 'en' ? 'loading report facts …' : '정기보고서 팩트 불러오는 중 …'}</div>
	{:else}
		<div class="storyEmpty">{lang === 'en' ? 'No report-parquet facts for this company.' : '해당 회사 정기보고서 팩트 없음.'}</div>
	{/if}
</Panel>

<!-- 인력 · 생산성 (정기보고서 임직원 현황 — 인원·급여·근속·1인당매출) -->
{#if wfLast}
	<Panel {lang} className="eIndustry" prov="real" title={{ kr: '인력 · 생산성', en: 'WORKFORCE' }} sub={{ kr: 'report · 임직원 ' + wfLast.year, en: 'report · ' + wfLast.year }} flush>
		<div class="factGrid">
			<div class="factRow"><span class="factL">{lang === 'en' ? 'headcount' : '총원'}</span><span class="factV mono">{wfLast.total != null ? wfLast.total.toLocaleString() + (lang === 'en' ? '' : '명') : '—'}</span></div>
			<div class="factRow"><span class="factL">{lang === 'en' ? 'M / F' : '남 / 여'}</span><span class="factV mono">{wfLast.male != null ? wfLast.male.toLocaleString() : '—'} / {wfLast.female != null ? wfLast.female.toLocaleString() : '—'}</span></div>
			<div class="factRow"><span class="factL">{lang === 'en' ? 'regular : contract' : '정규 : 계약'}</span><span class="factV mono">{wfLast.regular != null ? wfLast.regular.toLocaleString() : '—'} : {wfLast.contract != null ? wfLast.contract.toLocaleString() : '—'}</span></div>
			<div class="factRow"><span class="factL">{lang === 'en' ? 'avg salary' : '평균급여'}</span><span class="factV mono">{wfLast.avgSalary != null ? (wfLast.avgSalary / 1e8).toFixed(2) + (lang === 'en' ? ' ×0.1B' : '억') : '—'}</span></div>
			<div class="factRow"><span class="factL">{lang === 'en' ? 'tenure' : '평균근속'}</span><span class="factV mono">{wfLast.tenure != null ? wfLast.tenure.toFixed(1) + (lang === 'en' ? 'y' : '년') : '—'}</span></div>
			<div class="factRow"><span class="factL">{lang === 'en' ? 'rev / emp' : '1인당 매출'}</span><span class="factV mono">{revPerEmp(wfLast) != null ? revPerEmp(wfLast) + (lang === 'en' ? ' ×0.1B' : '억') : '—'}</span></div>
		</div>
	</Panel>
{/if}

<!-- 주주환원 (배당 + 자사주 — 정기보고서) -->
{#if srLast}
	<Panel {lang} className="eValuation" prov="real" title={{ kr: '주주환원', en: 'SHAREHOLDER RETURN' }} sub={{ kr: 'report · 배당 ' + srLast.year + ' · 보통주', en: 'report · ' + srLast.year + ' · common' }} flush>
		<div class="factGrid">
			<div class="factRow"><span class="factL">DPS</span><span class="factV mono">{srLast.dps != null ? srLast.dps.toLocaleString() + (lang === 'en' ? ' KRW' : '원') : '—'}</span></div>
			<div class="factRow"><span class="factL">{lang === 'en' ? 'div yield' : '배당수익률'}</span><span class="factV mono">{srLast.yieldPct != null ? srLast.yieldPct.toFixed(1) + '%' : '—'}</span></div>
			<div class="factRow"><span class="factL">{lang === 'en' ? 'payout' : '배당성향'}</span><span class="factV mono">{srLast.payoutPct != null ? srLast.payoutPct.toFixed(1) + '%' : '—'}</span></div>
			<div class="factRow"><span class="factL">{lang === 'en' ? 'total dividend' : '현금배당총액'}</span><span class="factV mono">{srLast.totalDividend != null ? fmtKRW(srLast.totalDividend) : '—'}</span></div>
			<div class="factRow"><span class="factL">{lang === 'en' ? 'treasury (end)' : '자사주 기말'}</span><span class="factV mono">{fmtShares(srLast.treasuryEnd)}</span></div>
			<div class="factRow"><span class="factL">{lang === 'en' ? 'buyback / disposal' : '취득 / 처분'}</span><span class="factV mono">{fmtShares(srLast.buybackQty)} / {fmtShares(srLast.disposalQty)}</span></div>
		</div>
	</Panel>
{/if}

<!-- 타법인 출자 (자회사·투자 — 장부가액 상위) -->
{#if inv && inv.rows.length}
	<Panel {lang} className="eCredit" prov="real" title={{ kr: '타법인 출자', en: 'HOLDINGS' }} sub={{ kr: 'report · ' + inv.year + ' · 장부가순', en: 'report · ' + inv.year + ' · by book value' }} flush>
		{#snippet right()}<span class="dim">{(inv?.rows.length ?? 0) + (inv?.moreCount ?? 0)}{lang === 'en' ? '' : '개사'}</span><button class="finFullBtn" onclick={() => (holdingsOpen = true)} title={lang === 'en' ? 'Relationship analysis (fullscreen)' : '출자 관계 분석 — 전체화면'}>⤢</button>{/snippet}
		<div class="finScroll"><table class="finTable">
			<thead><tr>
				<th class="finAcct">{lang === 'en' ? 'COMPANY' : '법인명'}</th>
				<th>{lang === 'en' ? 'PURPOSE' : '목적'}</th>
				<th class="r">{lang === 'en' ? 'STAKE' : '지분'}</th>
				<th class="r">{lang === 'en' ? 'BOOK' : '장부가'}</th>
				<th class="r">{lang === 'en' ? 'TARGET NET' : '피출자 순익'}</th>
			</tr></thead>
			<tbody>
				{#each inv.rows as r (r.name)}
					<tr class={r.stakePct != null && r.stakePct >= 50 ? 'finKey' : ''}>
						<td class="finAcct" title={r.name}>{r.name}</td>
						<td>{r.purpose}</td>
						<td class="r mono">{r.stakePct != null ? r.stakePct.toFixed(1) + '%' : '—'}</td>
						<td class="r mono">{r.bookValue != null ? fmtKRW(r.bookValue) : '—'}</td>
						<td class={'r mono ' + (r.targetNet != null && r.targetNet < 0 ? 'tDn' : '')}>{r.targetNet != null ? (r.targetNet < 0 ? '-' : '') + fmtKRW(Math.abs(r.targetNet)) : '—'}</td>
					</tr>
				{/each}
			</tbody>
		</table></div>
		{#if inv.moreCount}
			<div class="finNote">{lang === 'en' ? `+${inv.moreCount} more · book ${fmtKRW(inv.moreBook)}` : `외 ${inv.moreCount}개사 · 장부가 합계 ${fmtKRW(inv.moreBook)}`}</div>
		{/if}
	</Panel>
{/if}

<!-- 출자 관계 분석 전체화면 — 성격·위계 / 가치 / 효율 3축 진단 (lazy: 닫혀 있으면 청크 무증가) -->
{#if holdingsOpen && inv}
	{#await import('./HoldingsDialog.svelte') then { default: HoldingsDialog }}
		<HoldingsDialog {co} year={inv.year} rows={inv.rows} trend={invTrend} {lang} {lookupListed} {onPick} onClose={() => (holdingsOpen = false)} />
	{/await}
{/if}

<!-- 공급망 (dartlab 고유 — 공급사·고객사 제품·매출비중) -->
{#if relations && (relations.suppliers.length || relations.customers.length)}
	<Panel {lang} className="eIndustry" prov="real" title={{ kr: '공급망 · 거래선', en: 'SUPPLY CHAIN' }} sub={{ kr: 'map · ego ' + relations.neighborCount, en: 'ego n=' + relations.neighborCount }} flush>
		<div class="scWrap">
			<div class="scCol">
				<div class="scHd tUp">▼ {lang === 'en' ? 'SUPPLIERS' : '공급사'}</div>
				{#each relations.suppliers as e (e.stockCode + e.product)}
					<div class="scRow" role="button" tabindex="0" onclick={() => onPick(e.stockCode)} onkeydown={(ev) => ev.key === 'Enter' && onPick(e.stockCode)}>
						<span class="scName"><b>{e.corpName}</b>{#if e.product}<span class="scProd">{e.product}</span>{/if}</span>
						{#if e.ratio != null}<span class="scRatio mono">{e.ratio.toFixed(1)}%</span>{/if}
					</div>
				{/each}
			</div>
			<div class="scCol">
				<div class="scHd tDn">▲ {lang === 'en' ? 'CUSTOMERS' : '고객사'}</div>
				{#each relations.customers as e (e.stockCode + (e.product || ''))}
					<div class="scRow" role="button" tabindex="0" onclick={() => onPick(e.stockCode)} onkeydown={(ev) => ev.key === 'Enter' && onPick(e.stockCode)}>
						<span class="scName"><b>{e.corpName}</b>{#if e.product}<span class="scProd">{e.product}</span>{/if}</span>
						{#if e.ratio != null}<span class="scRatio mono">{e.ratio.toFixed(1)}%</span>{/if}
					</div>
				{/each}
			</div>
		</div>
	</Panel>
{/if}

<div class="rowSplit">
	<!-- CREDIT -->
	<Panel {lang} className="eCredit" prov="derived" title={{ kr: 'dartlab 신용 스코어', en: 'dartlab CREDIT' }} sub={{ kr: '비공식 · 자체 피처', en: 'unofficial · own features' }} flush>
		{#snippet right()}<span class="dim">{lang === 'en' ? '5-feature' : '5피처'}</span>{/snippet}
		<div class="creditTop"><div class="creditGrade"><span class="cgVal tCredit">{cr.grade}</span><span class="cgSub">{lang === 'en' ? 'health' : '건전도'} <b class={toneClass(cr.tone)}>{cr.healthScore}</b>/100 · PD <b class="tNeu">{cr.pd}</b></span></div></div>
		<div class="creditTracks">{#each cr.tracks as t (t.en)}<div class="ctRow"><span class="ctName">{txc(t, lang)}</span><div class="ctTrack"><div class="ctFill" style={`width:${t.score}%`}></div></div><span class="ctVal mono">{t.score}</span></div>{/each}</div>
		<div class="creditDiv">{lang === 'en' ? `From finance.json: debt ${cr.basis.debtRatio != null ? cr.basis.debtRatio.toFixed(0) + '%' : '—'}, current ${cr.basis.curr != null ? cr.basis.curr + '%' : '—'}. Heuristic dCR — not official.` : `finance.json 기반: 부채비율 ${cr.basis.debtRatio != null ? cr.basis.debtRatio.toFixed(0) + '%' : '—'}, 유동비율 ${cr.basis.curr != null ? cr.basis.curr + '%' : '—'}. 휴리스틱 dCR — 공식등급 아님.`}</div>
	</Panel>
	<!-- CHANGES -->
	<Panel {lang} className="eChanges" prov="derived" title={{ kr: '전년 대비 변화', en: 'YoY CHANGES' }} sub={{ kr: 'finance Δ', en: 'finance Δ' }} flush>
		<div class="chgList">
			{#each ch as c (c.en)}
				{@const has = c.v != null}
				{@const good = has && (c.invert ? c.v! < 0 : c.v! > 0)}
				{@const w = has ? Math.min(50, (Math.abs(c.v!) / chMax) * 50) : 0}
				<div class="chgRow">
					<span class="chgName">{txc(c, lang)}</span>
					<div class="chgBarWrap"><div class="chgBarMid"></div>{#if has}<div class={'chgBar ' + (c.v! >= 0 ? 'pos' : 'neg')} style={`width:${w}%;${c.v! >= 0 ? 'left:50%' : 'right:50%'};background:${good ? 'var(--up)' : 'var(--dn)'}`}></div>{/if}</div>
					<span class={'chgVal ' + (has ? (good ? 'tUp' : 'tDn') : 'tNeu')}>{has ? sign(c.v, 1) + c.unit : '—'}</span>
				</div>
			{/each}
		</div>
		<div class="finNote">finance.json · 직전 사업연도 대비</div>
	</Panel>
</div>

<!-- 공시 변경 내역 (changes parquet — 섹션별 수치/구조 변경) -->
{#if disclChanges.length}
	<Panel {lang} className="eChanges" prov="real" title={{ kr: "공시 변경 추적", en: "WHAT CHANGED" }} sub={{ kr: "직전 공시 대비 바뀐 섹션·내용", en: "vs prior filing" }} flush>
		{#snippet right()}<a class="lensScan" href={viewerHref} target={externalTarget} rel={externalRel} title="공시 뷰어에서 보기">뷰어 ↗</a><span class="dim">{disclChanges.length}</span>{/snippet}
		<div class="chgFeed">
			{#each disclChanges as c, i (i)}
				<div class="chgFeedRow">
					<span class={'chgType ' + (c.changeType === 'structural' ? 'st' : 'nu')}>{c.changeType === 'structural' ? (lang === 'en' ? 'STRUCT' : '구조') : (lang === 'en' ? 'NUM' : '수치')}</span>
					<span class="chgSec">{c.sectionTitle}</span>
					<span class="chgPer mono">{c.fromPeriod}→{c.toPeriod}</span>
					{#if c.preview}<span class="chgPrev">{c.preview}</span>{/if}
				</div>
			{/each}
		</div>
	</Panel>
{/if}

<!-- 공시 목록 — 정기 ‖ 비정기(allFilings) 2분할. data-fdate = 주가차트 공시 dot 클릭 시 스크롤·하이라이트 대상 키(YYYYMMDD). -->
<div class="rowSplit" bind:this={filingWrap}>
	<Panel {lang} className="eChanges" prov="real" title={{ kr: '정기공시', en: 'REGULAR' }} sub={{ kr: 'panel · 보고서', en: 'reports' }} flush>
		{#snippet right()}<button class="finFullBtn" onclick={() => (viewerOpen = true)} title="공시뷰어 전체화면 — 터미널 안에서 열기">⤢</button>{/snippet}
		{#if regFilings.length}
			<div class="filingList">
				{#each regFilings as f (f.rceptNo)}
					<a class="filingRow" class:flash={flashDate === fdate(f.rceptDate)} data-fdate={fdate(f.rceptDate)} href={f.url} target="_blank" rel="noopener">
						<span class="flType">{f.reportType}</span>
						<span class="flYear mono">{f.year}</span>
						<span class="flDate mono">{f.rceptDate}</span>
						<span class="flArrow">↗</span>
					</a>
				{/each}
			</div>
		{:else}
			<div class="storyEmpty">{lang === 'en' ? 'no regular filings' : '정기공시 없음'}</div>
		{/if}
	</Panel>
	<Panel {lang} className="eChanges" prov="real" title={{ kr: '비정기공시', en: 'OTHER FILINGS' }} sub={{ kr: 'allFilings · 수시', en: 'allFilings' }} flush>
		{#snippet right()}<span class="dim">{nonRegState === 'ready' ? nonRegFilings.length : ''}</span>{/snippet}
		{#if nonRegState === 'ready'}
			<div class="filingList">
				{#each nonRegFilings as f (f.rceptNo)}
					<a class="filingRow nonreg" class:flash={flashDate === fdate(f.rceptDate)} data-fdate={fdate(f.rceptDate)} href={f.url} target="_blank" rel="noopener" title={f.reportNm + (f.filer ? ' · ' + f.filer : '')}>
						<span class="flType">{f.reportNm}</span>
						<span class="flDate mono">{f.rceptDate.slice(2)}</span>
						<span class="flArrow">↗</span>
					</a>
				{/each}
			</div>
		{:else if nonRegState === 'loading'}
			<div class="storyEmpty">{lang === 'en' ? 'scanning recent filings …' : '최근 공시 스캔 중 …'}</div>
		{:else}
			<div class="storyEmpty">{lang === 'en' ? 'no non-regular filings' : '비정기공시 없음'}</div>
		{/if}
	</Panel>
</div>

<div class="rowSplit">
	<!-- PEERS -->
	<Panel {lang} className="eIndustry" prov="real" title={{ kr: '동종업종', en: 'INDUSTRY PEERS' }} sub={{ kr: 'industry:peers', en: 'peers' }} flush>
		{#snippet right()}<a class="lensScan" href="{base}/map?focus={co.code}" target="_blank" rel="noopener" title={lang === 'en' ? 'industry map — full ecosystem view' : '산업지도 — 업종 생태계 전체 보기'}>{lang === 'en' ? 'map ↗' : '맵 ↗'}</a>{/snippet}
		<div class="peerList">
			{#each peers as p (p.code)}
				<div class={'peerRow' + (p.self ? ' self' : '')} role="button" tabindex="0" onclick={() => onPick(p.code)} onkeydown={(ev) => ev.key === 'Enter' && onPick(p.code)}>
					<div class="peerTop">
					<span class="peerName"><b>{p.name}</b><span class="pc">{p.code}</span></span>
					<span class="peerBar"><span class="peerBarTrack"><span class="peerBarFill" style={`width:${((p.revenue || 0) / peerMax) * 100}%`}></span></span><span class="peerRev">{p.revenue != null ? (p.revenue / 10000).toFixed(1) + '조' : '—'}</span></span>
					</div>
					{#if corpMeta?.[p.code]?.product}<span class="peerProd">{corpMeta?.[p.code]?.product}</span>{/if}
				</div>
			{/each}
		</div>
	</Panel>
	<!-- GOVERNANCE -->
	<Panel {lang} className="eIndustry" prov="real" title={{ kr: '거버넌스 · 현금흐름', en: 'GOVERNANCE' }} sub={{ kr: 'ecosystem', en: 'ecosystem' }} flush>
		{#if e.cfPattern}<div class="patBig"><div class="pv">{e.cfPattern}</div><div class="ps">{lang === 'en' ? 'cash-flow pattern' : '현금흐름 패턴'}{e.empCount != null ? ' · ' + e.empCount.toLocaleString() + (lang === 'en' ? ' emp' : '명') : ''}</div></div>{/if}
		<div class="govGrid">{#each govCells as c (c.l)}<div class="govCell"><span>{c.l}</span><b class={tcls(c.t)}>{c.v}</b></div>{/each}</div>
		<div class="cfRow">
			{#each cfCells as c (c.l)}
				<div class="cfCell"><span>{c.l}</span><b class={'mono ' + (c.v == null ? 'tNeu' : c.good === true ? 'tUp' : c.good === false ? 'tDn' : c.v < 0 ? 'tDn' : 'tNeu')}>{c.v == null ? '—' : (c.v >= 0 ? '+' : '') + c.v.toFixed(1) + '조'}</b></div>
			{/each}
		</div>
		{#if govDeltas.length}
			<div class="govDeltaRow">
				{#each govDeltas as d (d.l)}<span class="govDelta"><i>{d.l}</i><b class={(d.inv ? d.v < 0 : d.v > 0) ? 'tUp' : d.v === 0 ? 'tNeu' : 'tDn'}>{sign(d.v, 1)}{d.u}</b></span>{/each}
			</div>
		{/if}
	</Panel>
</div>

<div class="rowSplit">
	<!-- STORY -->
	<Panel {lang} className="eCredit" prov="real" title={{ kr: 'DART · 스토리', en: 'DART · STORY' }} sub={{ kr: 'story · 공시', en: 'filings' }} flush>
		{#if s}
			<div class="storyCard"><span class="storyTag">DARTLAB STORY</span><div class="storyTitle">{s.title}</div><div class="storyMeta">{s.date} · {s.readTime ?? ''} · <a class="storyLink" href="{base}/blog/{s.slug}" target="_blank" rel="noopener">read ↗</a></div></div>
		{:else}
			<div class="storyEmpty">{lang === 'en' ? 'No published dartlab story yet.' : '발간된 dartlab 스토리는 아직 없습니다.'}</div>
		{/if}
		<div class="storyCard" style="border-top:1px solid var(--bd)"><div class="storyMeta">{lang === "en" ? "Company homepage" : "회사 홈페이지"}</div>{#if homepage}<a class="storyLink" href={homepage} target="_blank" rel="noopener noreferrer" style="font-family:var(--mono);font-size:10px">{homepageHost} ↗</a>{:else}<span class="storyLink" style="font-family:var(--mono);font-size:10px;color:var(--dimmer)">{lang === "en" ? "n/a" : "홈페이지 정보 없음"}</span>{/if}</div>
	</Panel>
	<!-- SUMMARY (derived, 정직: 가짜 tool-call 제거) -->
	<Panel {lang} className="eAnalysis" prov="derived" title={{ kr: 'dartlab 요약', en: 'DARTLAB SUMMARY' }} sub={{ kr: 'derived', en: 'derived' }} flush>
		{#snippet right()}<span class="conf">CONF <b class={conf === 'HIGH' ? 'tUp' : 'tWarn'}>{conf}</b></span>{/snippet}
		<div class="aiQ">▸ {lang === 'en' ? `${co.name.kr} financial health` : `${co.name.kr} 재무건전성`}</div>
		<div class="aiSteps">
			<div class="aiStep"><span class="aiTool">finance</span><span class="aiCall mono">IS/BS/CF · {firstYr}–{lastYr}</span><span class="aiRef">조 KRW</span></div>
			<div class="aiStep"><span class="aiTool">ecosystem</span><span class="aiCall mono">7축 등급 · 백분위</span><span class="aiRef">n={pc?.n ?? '—'}</span></div>
			<div class="aiStep"><span class="aiTool">prices</span><span class="aiCall mono">return · 52w · σ</span><span class="aiRef">{co.price.asOf}</span></div>
		</div>
		<div class="aiAnswer">{lang === 'en'
			? `Derived dCR ${cr.grade} (health ${cr.healthScore}/100, PD ${cr.pd}). OP margin ${co.fundamentals.opm != null ? co.fundamentals.opm.toFixed(1) + '%' : '—'}, ROE ${co.fundamentals.roe != null ? co.fundamentals.roe.toFixed(1) + '%' : '—'}, debt ${co.fundamentals.dr != null ? co.fundamentals.dr.toFixed(0) + '%' : '—'}. All from real finance/ecosystem/prices data.`
			: `dartlab 파생 신용 ${cr.grade} (건전도 ${cr.healthScore}/100, PD ${cr.pd}). 영업이익률 ${co.fundamentals.opm != null ? co.fundamentals.opm.toFixed(1) + '%' : '—'}, ROE ${co.fundamentals.roe != null ? co.fundamentals.roe.toFixed(1) + '%' : '—'}, 부채비율 ${co.fundamentals.dr != null ? co.fundamentals.dr.toFixed(0) + '%' : '—'}. 모두 finance/ecosystem/prices 실데이터 산출.`}</div>
	</Panel>
</div>

{#if viewerOpen}
	<ViewerOverlay
		code={co.code}
		studio={hosts.viewerStudio}
		{repoUrl}
		onclose={() => (viewerOpen = false)}
	/>
{/if}

{#if tablesOpen}
	{#if hosts.financeDialog}
		{#await hosts.financeDialog() then m}
			{@const FinanceDialog = m.default}
			<!-- .dlTermFinSkin: --fin-* 토큰 오버라이드 (terminal.css) — CSS 변수는 fixed 모달에도 DOM 상속으로 관통 -->
			<div class="dlTermFinSkin">
				<FinanceDialog code={co.code} corpName={co.name.kr} open={tablesOpen} onclose={() => (tablesOpen = false)} />
			</div>
		{/await}
	{:else}
		<!-- 열화 안내 — 이 셸은 정량 재무제표 모달 미지원 (숨김 금지 원칙: 기능 존재는 보이고 한계를 안내) -->
		<div class="hostFallback" role="presentation" onclick={() => (tablesOpen = false)}>
			<div class="hostFallbackPanel" role="dialog" aria-modal="true" tabindex="-1" onclick={(e) => e.stopPropagation()} onkeydown={(e) => e.key === 'Escape' && (tablesOpen = false)}>
				<div class="hostFallbackBar"><span>재무제표</span><button type="button" onclick={() => (tablesOpen = false)}>×</button></div>
				<div class="hostFallbackBody">{lang === 'en' ? 'Quantitative statements modal is not available in this shell — use the finance panel.' : '이 셸에선 정량 재무제표 모달을 지원하지 않습니다 — 재무 패널에서 확인하세요.'}</div>
			</div>
		</div>
	{/if}
{/if}

<style>
	/* 공시 dot 클릭 동기화 — 그 날짜 공시 행 일시 하이라이트(주가차트 공시 레일 → 위치 찾기). 3.6s 후 자동 소거(스포트라이트 길게). */
	.filingRow.flash {
		animation: filingFlash 3.6s ease-out;
	}
	@keyframes filingFlash {
		0%,
		55% {
			background: rgba(91, 155, 240, 0.28);
			box-shadow: inset 2px 0 0 var(--amber, #fb923c);
		}
		100% {
			background: transparent;
			box-shadow: inset 2px 0 0 transparent;
		}
	}

	/* 열화 안내 모달 — hosts.financeDialog 미주입 셸 전용 (component-scoped, 터미널 스킨 토큰) */
	.hostFallback {
		position: fixed;
		inset: 0;
		z-index: 120;
		display: grid;
		place-items: center;
		background: rgba(0, 0, 0, 0.66);
	}
	.hostFallbackPanel {
		width: min(420px, calc(100vw - 32px));
		border: 1px solid rgba(255, 255, 255, 0.12);
		background: #0f0f10;
		color: #e8eaef;
		border-radius: 4px;
		overflow: hidden;
	}
	.hostFallbackBar {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 9px 12px;
		border-bottom: 1px solid rgba(255, 255, 255, 0.1);
		font: 700 11px/1 var(--dl-font-mono, ui-monospace, monospace);
		color: #fb923c;
	}
	.hostFallbackBar button {
		border: 0;
		background: transparent;
		color: #a3a8b3;
		font-size: 18px;
		cursor: pointer;
	}
	.hostFallbackBody {
		padding: 18px 12px;
		font-size: 13px;
		line-height: 1.5;
		color: #a3a8b3;
	}
</style>
