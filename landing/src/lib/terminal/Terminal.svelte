<script lang="ts">
	import { base } from '$app/paths';
	import './terminal.css';
	import type { Engine } from './data/engine';
	import type { Lang } from './data/types';
	import { chgClass, fmtNum, sign } from './ui/helpers';
	import LeftRail from './panels/LeftRail.svelte';
	import CenterStack from './panels/CenterStack.svelte';
	import RightStack from './panels/RightStack.svelte';

	interface Props {
		eng: Engine;
		initial?: string;
	}
	let { eng, initial = '005930' }: Props = $props();

	const first = eng.featured(1)[0] || initial;
	let sym = $state(eng.buildCompany(initial) ? initial : first);
	let lang = $state<Lang>('kr');
	let cmd = $state('');
	let flash = $state<string | null>(null);
	let flashTimer: ReturnType<typeof setTimeout> | null = null;

	const co = $derived(eng.buildCompany(sym));
	const tickerCodes = $derived(eng.featured(14));
	const langTabs: { k: Lang; l: string }[] = [{ k: 'kr', l: '한국어' }, { k: 'en', l: 'EN' }, { k: 'dual', l: 'KR+EN' }];

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
			<img class="brandLogo" src="{base}/avatar-detective.png" alt="DartLab" width="56" height="56" style="border-radius:14px" />
			<div class="bootMark">DART<span>LAB</span> TERMINAL</div>
			<div class="bootBar"><div class="bootFill"></div></div>
			<div class="bootMsg">{lang === 'en' ? 'company not found' : '회사 데이터를 찾을 수 없습니다'}</div>
		</div>
	{:else}
		<header class="topBar">
			<div class="brand">
				<img class="brandLogo" src="{base}/avatar-detective.png" alt="DartLab" />
				<span class="brandName">DARTLAB</span>
				<span class="brandTag">KR TERMINAL</span>
			</div>
			<form class="cmdBar" onsubmit={go}>
				<span class="cmdPrompt">‹GO›</span>
				<input class="cmdInput" bind:value={cmd} spellcheck={false}
					placeholder={lang === 'en' ? 'Search code or name  (005930 · 삼성전자 · 기아)' : '종목코드/이름 검색  (005930 · 삼성전자 · SK하이닉스)'} />
				<button class="cmdGo" type="submit">GO</button>
				{#if flash}<span class="cmdFlash">{flash}</span>{/if}
			</form>
			<div class="topRight">
				<div class="langSwitch">{#each langTabs as t (t.k)}<button class={'langBtn ' + (lang === t.k ? 'on' : '')} onclick={() => (lang = t.k)}>{t.l}</button>{/each}</div>
				<span class="clock mono">{clock}</span>
				<span class="connDot"><span class="dot"></span>HuggingFace</span>
			</div>
		</header>

		<div class="tickerStrip"><div class="tickerTrack">
			{#each tickerCodes.concat(tickerCodes) as c, i (i)}
				{@const px = eng.priceOf(c)}
				{#if px}
					<span class="tickerItem" role="button" tabindex="0" onclick={() => pick(c)} onkeydown={(ev) => ev.key === 'Enter' && pick(c)}>
						<b>{eng.nameOf(c)}</b><span class="mono">{fmtNum(px.currentPrice)}</span>
						<span class={'mono ' + chgClass(px.return1m)}>{sign(px.return1m, 1)}%</span>
					</span>
				{/if}
			{/each}
		</div></div>

		<main class="board">
			<div class="col colL"><LeftRail {eng} {lang} active={sym} onPick={pick} /></div>
			<div class="col colC"><CenterStack {co} {lang} /></div>
			<div class="col colR"><RightStack {co} {lang} onPick={pick} /></div>
		</main>

		<footer class="statusBar">
			<span class="sbItem"><b class="tAmber">F1</b> SCREENER</span>
			<span class="sbItem"><b class="tAmber">F2</b> TREND</span>
			<span class="sbItem"><b class="tAmber">F3</b> GRADES</span>
			<span class="sbItem dim">DATA · {eng.source}</span>
			<span class="sbItem" style="gap:6px">
				<span class="provTag pLive">LIVE</span><span class="dim">{lang === 'en' ? 'real' : '실데이터'}</span>
				<span class="provTag pDeriv">파생</span><span class="dim">{lang === 'en' ? 'computed' : '계산'}</span>
			</span>
			<span class="sbSpacer"></span>
			<span class="sbItem dim">prices {co.price.asOf} · {eng.raw.index.length} 종목 · KR</span>
			<span class="sbItem"><b class="tUp">{co.code}</b> {co.name.kr} · {co.marketLabel}</span>
		</footer>
	{/if}
</div>
