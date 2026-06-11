<script lang="ts">
	// ── 터미널 구역 규칙 (불가침) ──
	// 좌측 레일 + 상단 헤더 = 네비게이션 (검색·목록·이동·상태)
	// 중앙 스택            = 시각화 중심 (차트·그래프·전체화면 분석)
	// 우측 스택            = 테이블·텍스트·수치·정성 — 그래프 배치 금지 (그래프는 중앙으로)
	import { base } from '$app/paths';
	import { Github } from 'lucide-svelte';
	import { brand } from '$lib/brand';
	import './terminal.css';
	import type { Engine } from './data/engine';
	import type { Lang } from './data/types';
	import { chgClass, fmtNum, sign } from './ui/helpers';
	import LeftRail from './panels/LeftRail.svelte';
	import CenterStack from './panels/CenterStack.svelte';
	import RightStack from './panels/RightStack.svelte';
	import SourcesModal from './panels/SourcesModal.svelte';
	import { prefetch as prefetchCompany, LAST_SYM_KEY } from './data/workbench';
	import { loadMacroLatest, type MacroLatest } from './data/macroSeries';
	import { loadTerminalFinance } from './data/terminalFinance';
	import { loadGovRecent } from './data/govPrice';
	import type { Candle } from './data/priceSeries';

	interface Props {
		eng: Engine;
		initial?: string;
	}
	let { eng, initial = '005930' }: Props = $props();

	// 마지막 본 종목 복원 — 재접속 시 그 종목으로 (localStorage, SSR 안전 가드)
	const lastSym = typeof localStorage !== 'undefined' ? localStorage.getItem(LAST_SYM_KEY) : null;
	const first = eng.featured(1)[0] || initial;
	let sym = $state(lastSym && eng.buildCompany(lastSym) ? lastSym : eng.buildCompany(initial) ? initial : first);
	let lang = $state<Lang>('kr');
	let sourcesOpen = $state(false);
	// 출처 모달 "최근 일자" — 라이브 재무 최신 분기 (loadTerminalFinance in-flight dedup, 추가 다운로드 0)
	let finLatest = $state('');
	$effect(() => {
		const c = co?.code;
		finLatest = '';
		if (!c) return;
		void loadTerminalFinance(c).then((b) => {
			if (co?.code !== c) return;
			finLatest = b?.views.quarter?.periods.at(-1) ?? b?.views.annual?.periods.at(-1) ?? '';
		});
	});
	let cmd = $state('');
	let flash = $state<string | null>(null);
	let flashTimer: ReturnType<typeof setTimeout> | null = null;

	// viewer 식 자동완성 검색
	let cmdInput = $state<HTMLInputElement | null>(null);
	let showSuggest = $state(false);
	let selIdx = $state(-1);
	const suggestions = $derived(showSuggest ? eng.suggest(cmd, 8) : []);
	function onInput() {
		showSuggest = cmd.trim().length > 0;
		selIdx = -1;
	}
	function onKey(e: KeyboardEvent) {
		if (!suggestions.length) return;
		if (e.key === 'ArrowDown') { e.preventDefault(); selIdx = (selIdx + 1) % suggestions.length; }
		else if (e.key === 'ArrowUp') { e.preventDefault(); selIdx = (selIdx - 1 + suggestions.length) % suggestions.length; }
		else if (e.key === 'Escape') { showSuggest = false; selIdx = -1; }
		else if (e.key === 'Enter' && selIdx >= 0) { e.preventDefault(); choose(suggestions[selIdx].code); }
	}
	function choose(code: string) {
		pick(code);
		cmd = '';
		showSuggest = false;
		selIdx = -1;
	}
	$effect(() => {
		const onDocKey = (e: KeyboardEvent) => {
			const tag = (e.target as HTMLElement | null)?.tagName;
			const inInput = tag === 'INPUT' || tag === 'TEXTAREA';
			if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') { e.preventDefault(); cmdInput?.focus(); }
			else if (e.key === '/' && !inInput) { e.preventDefault(); cmdInput?.focus(); }
		};
		window.addEventListener('keydown', onDocKey);
		return () => window.removeEventListener('keydown', onDocKey);
	});

	const co = $derived(eng.buildCompany(sym));
	// 회사 선택 시 워크벤치로 모든 온디맨드 소스를 병렬 워밍업(패널 effect 전 캐시 준비).
	$effect(() => {
		const c = co;
		if (c) prefetchCompany(c.code, +c.price.asOf.slice(0, 4) || new Date().getFullYear());
	});
	const tickerCodes = $derived(eng.featured(14));
	// 회사 티커 스파크라인 — recent.parquet(최근 30거래일 전종목) 재사용, 추가 다운로드 0 (모듈 캐시 공유)
	let recentMap = $state<Map<string, Candle[]> | null>(null);
	loadGovRecent().then((m) => (recentMap = m));
	const sparkPts = (s: number[], w = 34, hh = 11): string => {
		const lo = Math.min(...s);
		const hi = Math.max(...s);
		const rng = hi - lo || 1;
		return s.map((v, i) => `${((i / (s.length - 1)) * w).toFixed(1)},${(hh - ((v - lo) / rng) * (hh - 1.5) - 0.75).toFixed(1)}`).join(' ');
	};
	// 실 경제지표 최신값 (ECOS·FRED 시계열) — 종목명·주가차트 윗단 KPI 티커에 합류.
	let macroLatest = $state<MacroLatest[]>([]);
	loadMacroLatest().then((m) => (macroLatest = m));
	const fmtMacro = (m: MacroLatest): string => {
		const v = m.v.toLocaleString('en-US', { maximumFractionDigits: m.def.digits ?? 2 });
		const signed = m.def.yoy && m.v > 0 ? '+' + v : v;
		const u = m.def.unit;
		return u === 'pt' || u === '원' ? signed : u === '$/t' ? '$' + signed : signed + u;
	};
	// 경제·시장 KPI (CenterStack 헤더 티커) — 실 지표 최신값+스파크라인 + 매크로 국면 KR/US + 섹터 순풍·역풍 + 시장폭/평균.
	const macroKpis = $derived.by<{ l: string; v: string; t: string; s?: number[] }[]>(() => {
		const m = eng.raw.macro;
		const tw = eng.sectorTailwinds();
		const r1 = Object.values(eng.raw.prices.data).map((p) => p.return1m).filter((x): x is number => x != null);
		const up = r1.length ? (r1.filter((x) => x > 0).length / r1.length) * 100 : null;
		const avg = r1.length ? r1.reduce((a, b) => a + b, 0) / r1.length : null;
		const out: { l: string; v: string; t: string; s?: number[] }[] = [];
		for (const ml of macroLatest)
			out.push({ l: lang === 'en' ? ml.def.en : ml.def.kr, v: fmtMacro(ml), t: ml.chg == null || ml.chg === 0 ? 'tNeu' : ml.chg > 0 ? 'tUp' : 'tDn', s: ml.spark });
		if (m) {
			const dir = (g: string) => (g === 'rising' || g === '상승' ? 'tUp' : 'tDn');
			out.push({ l: 'KR', v: lang === 'en' ? m.kr.phase : m.kr.phaseLabel, t: dir(m.kr.quadrant.growth) });
			out.push({ l: 'US', v: lang === 'en' ? m.us.phase : m.us.phaseLabel, t: dir(m.us.quadrant.growth) });
		}
		if (tw[0]) out.push({ l: lang === 'en' ? 'tailwind' : '순풍', v: (lang === 'en' ? tw[0].en : tw[0].kr) + ' +' + tw[0].blended.toFixed(2), t: 'tUp' });
		if (tw.length > 1) { const lo = tw[tw.length - 1]; out.push({ l: lang === 'en' ? 'headwind' : '역풍', v: (lang === 'en' ? lo.en : lo.kr) + ' ' + lo.blended.toFixed(2), t: 'tDn' }); }
		if (up != null) out.push({ l: lang === 'en' ? 'breadth' : '시장폭', v: up.toFixed(0) + '%↑', t: up >= 50 ? 'tUp' : 'tDn' });
		if (avg != null) out.push({ l: lang === 'en' ? 'avg 1M' : '평균1M', v: sign(avg, 1) + '%', t: avg >= 0 ? 'tUp' : 'tDn' });
		return out;
	});
	const langTabs: { k: Lang; l: string }[] = [{ k: 'kr', l: '한국어' }, { k: 'en', l: 'EN' }];

	function setFlash(msg: string, ms = 900) {
		flash = msg;
		if (flashTimer) clearTimeout(flashTimer);
		flashTimer = setTimeout(() => (flash = null), ms);
	}
	function pick(code: string) {
		const built = eng.buildCompany(code);
		if (!built) {
			setFlash(lang === 'en' ? 'no data' : '데이터 없음', 1400);
			return;
		}
		sym = code;
		try { localStorage.setItem(LAST_SYM_KEY, code); } catch { /* 시크릿 모드 등 */ }
		setFlash(code + ' · ' + built.name.kr);
	}
	function go(e: Event) {
		e.preventDefault();
		const r = eng.search(cmd);
		if (r) {
			pick(r);
			cmd = '';
		} else setFlash(lang === 'en' ? 'no match' : '검색 결과 없음', 1300);
	}

	// clock
	let now = $state(new Date());
	$effect(() => {
		const id = setInterval(() => (now = new Date()), 1000);
		return () => clearInterval(id);
	});
	const pad = (n: number) => String(n).padStart(2, '0');
	const clock = $derived(`${pad(now.getHours())}:${pad(now.getMinutes())}:${pad(now.getSeconds())} KST`);
</script>

<div class="dlTerm">
	{#if !co}
		<div class="bootScreen">
			<img class="brandLogo" src="{base}/avatar.png" alt="DartLab" width="56" height="56" style="border-radius:50%" />
			<div class="bootMark">DartLab <span>terminal</span></div>
			<div class="bootBar"><div class="bootFill"></div></div>
			<div class="bootMsg">{lang === 'en' ? 'company not found' : '회사 데이터를 찾을 수 없습니다'}</div>
		</div>
	{:else}
		<header class="topBar">
			<a class="brand" href="{base}/" title="dartlab">
				<picture>
					<source srcset="{base}/avatar.webp" type="image/webp" />
					<img class="brandLogo" src="{base}/avatar.png" alt="DartLab" width="24" height="24" />
				</picture>
				<span class="brandName">DartLab</span>
				<span class="brandSlash">/</span>
				<span class="brandTag">terminal</span>
			</a>
			<form class="cmdBar" onsubmit={go} role="search">
				<span class="cmdPrompt">‹GO›</span>
				<input class="cmdInput" bind:this={cmdInput} bind:value={cmd} spellcheck={false}
					oninput={onInput} onkeydown={onKey} onfocus={onInput}
					onblur={() => setTimeout(() => (showSuggest = false), 120)}
					placeholder={lang === 'en' ? 'Search code or name  (005930 · 삼성전자 · 기아)' : '종목코드 · 회사명 검색'} />
				<kbd class="cmdKbd">⌘K</kbd>
				<button class="cmdGo" type="submit">GO</button>
				{#if flash}<span class="cmdFlash">{flash}</span>{/if}
				{#if showSuggest && suggestions.length}
					<div class="suggest">
						{#each suggestions as s, i (s.code)}
							<button type="button" class={'suggestRow' + (i === selIdx ? ' on' : '')}
								onmousedown={() => choose(s.code)} onmouseenter={() => (selIdx = i)}>
								<span class="sgName">{s.name}</span>
								<span class="sgCode mono">{s.code}</span>
								<span class="sgInd">{s.industry}</span>
							</button>
						{/each}
					</div>
				{/if}
			</form>
			<div class="topRight">
				<div class="langSwitch">{#each langTabs as t (t.k)}<button class={'langBtn ' + (lang === t.k ? 'on' : '')} onclick={() => (lang = t.k)}>{t.l}</button>{/each}</div>
				<span class="clock mono">{clock}</span>
				<span class="connDot"><span class="dot"></span>HF</span>
				<div class="hdrLinks">
					<a class="hdrLink" href="{brand.repo}/discussions" target="_blank" rel="noopener" title="GitHub 토론 — 의견·제안">{lang === 'en' ? 'Discuss' : '토론'}</a>
					<a class="hdrLink" href="{brand.repo}/issues/new" target="_blank" rel="noopener" title="GitHub 이슈 등록 — 버그·요청">{lang === 'en' ? 'Issue' : '이슈'}</a>
				</div>
				<nav class="sns">
					<a class="snsBtn" href={brand.repo} target="_blank" rel="noopener" title="GitHub"><Github size={15} /></a>
					<a class="snsBtn" href={brand.coffee} target="_blank" rel="noopener" title="Buy Me a Coffee" aria-label="Buy Me a Coffee">
						<svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M17 8h1a4 4 0 1 1 0 8h-1" /><path d="M3 8h14v9a4 4 0 0 1-4 4H7a4 4 0 0 1-4-4Z" /><line x1="6" y1="2" x2="6" y2="4" /><line x1="10" y1="2" x2="10" y2="4" /><line x1="14" y1="2" x2="14" y2="4" /></svg>
					</a>
					<a class="snsBtn" href={brand.youtube} target="_blank" rel="noopener" title="YouTube" aria-label="YouTube">
						<svg viewBox="0 0 24 24" width="15" height="15" fill="currentColor" aria-hidden="true"><path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z"/></svg>
					</a>
					<a class="snsBtn" href={brand.threads} target="_blank" rel="noopener" title="Threads · @dartlab.ai" aria-label="Threads">
						<svg viewBox="0 0 24 24" width="15" height="15" fill="currentColor" aria-hidden="true"><path d="M12.186 24h-.007c-3.581-.024-6.334-1.205-8.184-3.509C2.35 18.44 1.5 15.586 1.472 12.01v-.017c.03-3.579.879-6.43 2.525-8.482C5.845 1.205 8.6.024 12.18 0h.014c2.746.02 5.043.725 6.826 2.098 1.677 1.29 2.858 3.13 3.509 5.467l-2.04.569c-1.104-3.96-3.898-5.984-8.304-6.015-2.91.022-5.11.936-6.54 2.717C4.307 6.504 3.616 8.914 3.589 12c.027 3.086.718 5.496 2.057 7.164 1.43 1.783 3.631 2.698 6.54 2.717 2.623-.02 4.358-.631 5.8-2.045 1.647-1.613 1.618-3.593 1.09-4.798-.31-.71-.873-1.3-1.634-1.75-.192 1.352-.622 2.446-1.284 3.272-.886 1.102-2.14 1.704-3.73 1.79-1.202.065-2.361-.218-3.259-.801-1.063-.689-1.685-1.74-1.752-2.964-.065-1.19.408-2.285 1.33-3.082.88-.76 2.119-1.207 3.583-1.291a13.853 13.853 0 0 1 3.02.142c-.126-.742-.375-1.332-.75-1.757-.513-.586-1.308-.883-2.359-.89h-.029c-.844 0-1.992.232-2.721 1.32L7.734 7.847c.98-1.454 2.568-2.256 4.478-2.256h.044c3.194.02 5.097 1.975 5.287 5.388.108.046.216.094.321.142 1.49.7 2.58 1.761 3.154 3.07.797 1.82.871 4.79-1.548 7.158-1.85 1.81-4.094 2.628-7.277 2.65Zm1.003-11.69c-.242 0-.487.007-.739.021-1.836.103-2.98.946-2.916 2.143.067 1.256 1.452 1.839 2.784 1.767 1.224-.065 2.818-.543 3.086-3.71a10.5 10.5 0 0 0-2.215-.221z"/></svg>
					</a>
					<a class="snsBtn" href={brand.instagram} target="_blank" rel="noopener" title="Instagram · @dartlab.ai" aria-label="Instagram">
						<svg viewBox="0 0 24 24" width="15" height="15" fill="currentColor" aria-hidden="true"><path d="M12 0C8.74 0 8.333.015 7.053.072 5.775.132 4.905.333 4.14.63c-.789.306-1.459.717-2.126 1.384S.935 3.35.63 4.14C.333 4.905.131 5.775.072 7.053.012 8.333 0 8.74 0 12s.015 3.667.072 4.947c.06 1.277.261 2.148.558 2.913.306.788.717 1.459 1.384 2.126.667.666 1.336 1.079 2.126 1.384.766.296 1.636.499 2.913.558C8.333 23.988 8.74 24 12 24s3.667-.015 4.947-.072c1.277-.06 2.148-.262 2.913-.558.788-.306 1.459-.718 2.126-1.384.666-.667 1.079-1.335 1.384-2.126.296-.765.499-1.636.558-2.913.06-1.28.072-1.687.072-4.947s-.015-3.667-.072-4.947c-.06-1.277-.262-2.149-.558-2.913-.306-.789-.718-1.459-1.384-2.126C21.319 1.347 20.651.935 19.86.63c-.765-.297-1.636-.499-2.913-.558C15.667.012 15.26 0 12 0zm0 2.16c3.203 0 3.585.016 4.85.071 1.17.055 1.805.249 2.227.415.562.217.96.477 1.382.896.419.42.679.819.896 1.381.164.422.36 1.057.413 2.227.057 1.266.07 1.646.07 4.85s-.015 3.585-.074 4.85c-.061 1.17-.256 1.805-.421 2.227-.224.562-.479.96-.899 1.382-.419.419-.824.679-1.38.896-.42.164-1.065.36-2.235.413-1.274.057-1.649.07-4.859.07-3.211 0-3.586-.015-4.859-.074-1.171-.061-1.816-.256-2.236-.421-.569-.224-.96-.479-1.379-.899-.421-.419-.69-.824-.9-1.38-.165-.42-.359-1.065-.42-2.235-.045-1.26-.061-1.649-.061-4.844 0-3.196.016-3.586.061-4.861.061-1.17.255-1.814.42-2.234.21-.57.479-.96.9-1.381.419-.419.81-.689 1.379-.898.42-.166 1.051-.361 2.221-.421 1.275-.045 1.65-.06 4.859-.06l.045.03zm0 3.678c-3.405 0-6.162 2.76-6.162 6.162 0 3.405 2.76 6.162 6.162 6.162 3.405 0 6.162-2.76 6.162-6.162 0-3.405-2.76-6.162-6.162-6.162zM12 16c-2.21 0-4-1.79-4-4s1.79-4 4-4 4 1.79 4 4-1.79 4-4 4zm7.846-10.405c0 .795-.646 1.44-1.44 1.44-.795 0-1.44-.646-1.44-1.44 0-.794.646-1.439 1.44-1.439.793-.001 1.44.645 1.44 1.439z"/></svg>
					</a>
				</nav>
			</div>
		</header>

		<div class="tickerStrip"><div class="tickerTrack">
			{#each tickerCodes.concat(tickerCodes) as c, i (i)}
				{@const px = eng.priceOf(c)}
				{#if px}
					{@const sp = recentMap?.get(c)}
					<span class="tickerItem" role="button" tabindex="0" onclick={() => pick(c)} onkeydown={(ev) => ev.key === 'Enter' && pick(c)}>
						<b>{eng.nameOf(c)}</b>
						{#if sp && sp.length > 1}<svg class={'kpiSpark ' + chgClass(px.return1m)} viewBox="0 0 34 11" preserveAspectRatio="none" aria-hidden="true"><polyline points={sparkPts(sp.map((k) => k.c))} fill="none" stroke="currentColor" stroke-width="1.1" /></svg>{/if}
						<span class="mono">{fmtNum(px.currentPrice)}</span>
						<span class={'mono ' + chgClass(px.return1m)}>{sign(px.return1m, 1)}%</span>
					</span>
				{/if}
			{/each}
		</div></div>

		<main class="board">
			<div class="col colL"><LeftRail {eng} {lang} active={sym} onPick={pick} /></div>
			<div class="col colC"><CenterStack {co} {lang} kpis={macroKpis} /></div>
			<div class="col colR"><RightStack {co} {lang} onPick={pick} /></div>
		</main>

		<footer class="statusBar">
			<span class="sbItem"><b class="tAmber">⌘K</b> {lang === 'en' ? 'SEARCH' : '검색'}</span>
			<span class="sbItem"><b class="tAmber">/</b> {lang === 'en' ? 'FOCUS' : '검색창'}</span>
			<button class="sbItem sbSrcBtn" onclick={() => (sourcesOpen = true)} title={lang === 'en' ? 'data sources & licenses' : '데이터 출처·라이선스'}>
				<b class="tAmber">ⓘ</b> {lang === 'en' ? 'SOURCES' : '데이터 출처'}
			</button>
			<span class="sbItem dim">DATA · {eng.source}</span>
			<span class="sbItem" style="gap:6px">
				<span class="provTag pReal">{lang === 'en' ? 'REAL' : '실데이터'}</span><span class="dim">{lang === 'en' ? 'EOD · daily batch' : 'EOD·일배치'}</span>
				<span class="provTag pDeriv">파생</span><span class="dim">{lang === 'en' ? 'computed' : '계산'}</span>
			</span>
			<span class="sbSpacer"></span>
			<span class="sbItem dim">prices {co.price.asOf} · {eng.raw.index.length} 종목 · KR</span>
			<span class="sbItem"><b class="tUp">{co.code}</b> {co.name.kr} · {co.marketLabel}</span>
		</footer>
		<SourcesModal {lang} open={sourcesOpen} onClose={() => (sourcesOpen = false)} pricesAsOf={co.price.asOf} macroAsOf={eng.raw.macro?.asOf ?? ''} financeLatest={finLatest || (co.trendQuarter?.periods.at(-1) ?? '')} />
	{/if}
</div>
