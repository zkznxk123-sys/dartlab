<script lang="ts">
	import { base } from '$app/paths';
	import type { Company, Lang, Statement } from '../data/types';
	import { gradeTone } from '../data/engine';
	import Panel from '../ui/Panel.svelte';
	import { tx, txc, chgClass, sign, toneClass, fmtNum } from '../ui/helpers';
	import {
		loadLiveCompanyReportFacts,
		loadLiveCompanyChanges,
		type LiveCompanyReportFact
	} from '$lib/browser/companyLive';
	import type { CompanyChange } from '$lib/scan/duckSql';
	import { loadCompanyRelations, type CompanyRelations } from '../data/relations';
	import { loadCompanyRegularFilings, type RegularFiling } from '$lib/data/companyFilingsRuntime';
	import { loadCompanyNonRegularFilings, type NonRegularFiling } from '$lib/data/companyNonRegularFilings';

	interface Props {
		co: Company;
		lang: Lang;
		onPick: (code: string) => void;
	}
	let { co, lang, onPick }: Props = $props();
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
		let cancelled = false;
		loadLiveCompanyReportFacts(code).then((f) => {
			if (cancelled) return;
			reportFacts = f;
			factsState = f.length ? 'ready' : 'empty';
		});
		loadLiveCompanyChanges(code, 8).then((c) => {
			if (!cancelled) disclChanges = c;
		});
		loadCompanyRelations(code).then((r) => {
			if (!cancelled) relations = r;
		});
		loadCompanyRegularFilings(code, 12).then((f) => {
			if (!cancelled) regFilings = f;
		});
		loadCompanyNonRegularFilings(code, { limit: 30 }).then((f) => {
			if (cancelled) return;
			nonRegFilings = f;
			nonRegState = f.length ? 'ready' : 'empty';
		});
		return () => {
			cancelled = true;
		};
	});

	let stmt = $state<'SUM' | 'IS' | 'BS' | 'CF' | 'RT'>('SUM');
	let acct = $state<'kr' | 'en'>('kr');
	const tabs = [{ k: 'SUM', kr: '요약', en: 'Key' }, { k: 'IS', kr: '손익', en: 'IS' }, { k: 'BS', kr: '재무상태', en: 'BS' }, { k: 'CF', kr: '현금흐름', en: 'CF' }, { k: 'RT', kr: '비율', en: 'Ratios' }] as const;
	const summary = $derived<Statement>({
		periods: co.income.periods,
		rows: co.income.rows.concat(co.balance.rows.filter((r) => ['totalAsset', 'totalLiab', 'totalEquity'].includes(r.id)))
	});
	const stmtData = $derived<Statement>(({ SUM: summary, IS: co.income, BS: co.balance, CF: co.cashflow, RT: summary } as Record<string, Statement>)[stmt]);

	const risks = $derived(co.risks);
	const pc = $derived(co.percentile);
	const pcCol = (p: number) => (p >= 80 ? 'var(--up)' : p >= 55 ? 'var(--good)' : p >= 35 ? 'var(--warn)' : 'var(--dn)');
	const pcFmtV = (m: { unit: string; v: number | null }) =>
		m.unit === 'rev' ? (m.v != null ? (m.v / 1e12).toFixed(1) + '조' : '—') : m.v != null ? m.v.toFixed(1) + (m.unit === '%' ? '%' : '') : '—';

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
		{ l: lang === 'en' ? 'QUALITY' : '이익질', v: e.qualGrade || '—', t: gradeTone('qual', e.qualGrade) }
	]);
	const s = $derived(co.story);
	const dartUrl = 'https://dart.fss.or.kr/dsab007/main.do';
	const lastYr = $derived(co.income.periods[0]);
	const firstYr = $derived(co.income.periods[co.income.periods.length - 1]);
	const conf = $derived(cr.healthScore >= 70 ? 'HIGH' : 'MEDIUM');
</script>

<!-- RISK FLAGS -->
<Panel {lang} className="eCredit" prov="live" title={{ kr: '리스크 경고등', en: 'RISK FLAGS' }} sub={{ kr: 'ecosystem', en: 'ecosystem' }}>
	{#snippet right()}<span><b class="tDn">{risks.filter((r) => r.lv === 'red').length}</b> <b class="tWarn">{risks.filter((r) => r.lv === 'yellow').length}</b></span>{/snippet}
	<div class="riskWrap">
		{#each risks as r, i (i)}
			<div class={'riskRow ' + r.lv}><span class={'riskDot ' + r.lv}></span><span class="riskName">{lang === 'en' ? r.en : r.kr}</span>{#if r.d}<span class="riskDetail">{r.d}</span>{/if}</div>
		{/each}
	</div>
</Panel>

<!-- PERCENTILE -->
{#if pc && pc.metrics.length}
	<Panel {lang} className="eQuant" prov="live" title={{ kr: '업종 내 백분위', en: 'INDUSTRY PERCENTILE' }} sub={{ kr: pc.industry + ' ' + pc.n + '사', en: pc.industry + ' n=' + pc.n }} flush>
		<div class="pctList">
			{#each pc.metrics as m (m.en)}
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

<!-- FINANCIALS -->
<Panel {lang} className="eAnalysis" prov="live" title={{ kr: '재무제표', en: 'FINANCIAL STATEMENTS' }} sub={{ kr: 'c.panel · 연간', en: 'c.panel · annual' }} flush>
	{#snippet right()}<span class="finCtl"><button class={'seg' + (acct === 'kr' ? ' on' : '')} onclick={() => (acct = acct === 'kr' ? 'en' : 'kr')}>{acct === 'kr' ? '한글' : 'EN'}</button></span>{/snippet}
	<div class="finTabs">{#each tabs as t (t.k)}<button class={'finTab ' + (stmt === t.k ? 'on' : '')} onclick={() => (stmt = t.k)}>{lang === 'en' ? t.en : t.kr}</button>{/each}</div>
	{#if stmt === 'RT'}
		<div class="finScroll"><table class="finTable"><tbody>
			{#each co.ratios as r (r.id)}<tr><td class="finAcct">{acct === 'kr' ? r.kr : r.en}</td><td class="finAcct dim">{acct === 'kr' ? r.en : r.kr}</td><td class={'r mono ' + toneClass(r.tone)}>{r.v}</td></tr>{/each}
		</tbody></table></div>
	{:else}
		<div class="finScroll"><table class="finTable">
			<thead><tr><th class="finAcct">{lang === 'en' ? 'ACCOUNT' : '계정'}</th>{#each stmtData.periods as p (p)}<th class="r">{p}</th>{/each}</tr></thead>
			<tbody>
				{#each stmtData.rows as r (r.id)}
					<tr class={['op', 'net', 'fcf', 'totalEquity', 'totalAsset'].includes(r.id) ? 'finKey' : ''}>
						<td class="finAcct">{acct === 'kr' ? r.kr : r.en}</td>
						{#each r.vals as val, i (i)}<td class={'r mono ' + (r.pct ? (val != null && val >= 8 ? 'tUp' : val != null && val < 0 ? 'tDn' : 'tNeu') : val != null && val < 0 ? 'tDn' : '')}>{val == null ? '—' : r.pct ? val.toFixed(1) + '%' : fmtNum(val, 1)}</td>{/each}
					</tr>
				{/each}
			</tbody>
		</table></div>
	{/if}
	<div class="finNote">finance.json · {firstYr}–{lastYr} · 조 KRW{stmt === 'CF' ? ' · CFO/CFI/CFF 실데이터' : ''}</div>
</Panel>

<!-- DART 정기보고서 팩트 (배당·자사주·임원·감사·대주주·회사채 — report parquet) -->
<Panel {lang} className="eCredit" prov="live" title={{ kr: 'DART 정기보고서 팩트', en: 'DART REPORT FACTS' }} sub={{ kr: 'report · 공시원문', en: 'report · filings' }} flush>
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

<!-- 공급망 (dartlab 고유 — 공급사·고객사 제품·매출비중) -->
{#if relations && (relations.suppliers.length || relations.customers.length)}
	<Panel {lang} className="eIndustry" prov="live" title={{ kr: '공급망 · 거래선', en: 'SUPPLY CHAIN' }} sub={{ kr: 'map · ego ' + relations.neighborCount, en: 'ego n=' + relations.neighborCount }} flush>
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
	<Panel {lang} className="eChanges" prov="live" title={{ kr: '공시 변경 내역', en: 'FILING CHANGES' }} sub={{ kr: 'changes · 섹션', en: 'changes · sections' }} flush>
		{#snippet right()}<a class="lensScan" href="{base}/viewer/company/{co.code}" target="_blank" rel="noopener" title="공시 뷰어에서 보기">뷰어 ↗</a><span class="dim">{disclChanges.length}</span>{/snippet}
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

<!-- 공시 목록 — 정기 ‖ 비정기(allFilings) 2분할 -->
<div class="rowSplit">
	<Panel {lang} className="eChanges" prov="live" title={{ kr: '정기공시', en: 'REGULAR' }} sub={{ kr: 'panel · 보고서', en: 'reports' }} flush>
		{#snippet right()}<a class="lensScan" href="{base}/viewer/company/{co.code}" target="_blank" rel="noopener" title="공시 뷰어에서 보기">뷰어 ↗</a>{/snippet}
		{#if regFilings.length}
			<div class="filingList">
				{#each regFilings as f (f.rceptNo)}
					<a class="filingRow" href={f.url} target="_blank" rel="noopener">
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
	<Panel {lang} className="eChanges" prov="live" title={{ kr: '비정기공시', en: 'OTHER FILINGS' }} sub={{ kr: 'allFilings · 수시', en: 'allFilings' }} flush>
		{#snippet right()}<span class="dim">{nonRegState === 'ready' ? nonRegFilings.length : ''}</span>{/snippet}
		{#if nonRegState === 'ready'}
			<div class="filingList">
				{#each nonRegFilings as f (f.rceptNo)}
					<a class="filingRow nonreg" href={f.url} target="_blank" rel="noopener" title={f.reportNm + (f.filer ? ' · ' + f.filer : '')}>
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
	<Panel {lang} className="eIndustry" prov="live" title={{ kr: '동종업종', en: 'INDUSTRY PEERS' }} sub={{ kr: 'industry:peers', en: 'peers' }} flush>
		<div class="peerList">
			{#each peers as p (p.code)}
				<div class={'peerRow' + (p.self ? ' self' : '')} role="button" tabindex="0" onclick={() => onPick(p.code)} onkeydown={(ev) => ev.key === 'Enter' && onPick(p.code)}>
					<span class="peerName"><b>{p.name}</b><span class="pc">{p.code}</span></span>
					<span class="peerBar"><span class="peerBarTrack"><span class="peerBarFill" style={`width:${((p.revenue || 0) / peerMax) * 100}%`}></span></span><span class="peerRev">{p.revenue != null ? (p.revenue / 10000).toFixed(1) + '조' : '—'}</span></span>
				</div>
			{/each}
		</div>
	</Panel>
	<!-- GOVERNANCE -->
	<Panel {lang} className="eIndustry" prov="live" title={{ kr: '거버넌스 · 현금흐름', en: 'GOVERNANCE' }} sub={{ kr: 'ecosystem', en: 'ecosystem' }} flush>
		{#if e.cfPattern}<div class="patBig"><div class="pv">{e.cfPattern}</div><div class="ps">{lang === 'en' ? 'cash-flow pattern' : '현금흐름 패턴'}{e.empCount != null ? ' · ' + e.empCount.toLocaleString() + (lang === 'en' ? ' emp' : '명') : ''}</div></div>{/if}
		<div class="govGrid">{#each govCells as c (c.l)}<div class="govCell"><span>{c.l}</span><b class={tcls(c.t)}>{c.v}</b></div>{/each}</div>
	</Panel>
</div>

<div class="rowSplit">
	<!-- STORY -->
	<Panel {lang} className="eCredit" prov="live" title={{ kr: 'DART · 스토리', en: 'DART · STORY' }} sub={{ kr: 'story · 공시', en: 'filings' }} flush>
		{#if s}
			<div class="storyCard"><span class="storyTag">DARTLAB STORY</span><div class="storyTitle">{s.title}</div><div class="storyMeta">{s.date} · {s.readTime ?? ''} · <a class="storyLink" href={'https://eddmpython.github.io/dartlab/blog/' + s.slug} target="_blank" rel="noopener">read ↗</a></div></div>
		{:else}
			<div class="storyEmpty">{lang === 'en' ? 'No published dartlab story yet.' : '발간된 dartlab 스토리는 아직 없습니다.'}</div>
		{/if}
		<div class="storyCard" style="border-top:1px solid var(--bd)"><div class="storyMeta">{lang === 'en' ? 'Primary filings — DART:' : '원문 공시 — DART:'}</div><a class="storyLink" href={dartUrl} target="_blank" rel="noopener" style="font-family:var(--mono);font-size:10px">dart.fss.or.kr · {co.name.kr} ↗</a></div>
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
