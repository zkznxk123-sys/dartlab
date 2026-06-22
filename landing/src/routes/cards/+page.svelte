<script lang="ts">
	// 라이브 카드 캐러셀 라우터 — 전 종목 피드(무한스크롤·검색·hero 썸네일) + 클릭 시 인스타식 플레이어.
	// 공통배선: 데이터는 loadJson(dartlabData)·미디어는 hfMedia origin. dev 도 :8400 없이 퍼블릭 기준으로 뜬다.
	import type { PageData } from './$types';
	import { base } from '$app/paths';
	import { goto } from '$app/navigation';
	import { setStaticBase, loadJson } from '@dartlab/ui-runtime/data/dartlabData';
	import type { IndexRow } from '@dartlab/ui-contracts';
	import { getPublicRuntime } from '$lib/runtime/publicRuntime';
	import '@dartlab/ui-surfaces/terminal/terminal.css';
	import { DARTLAB_BRAND_LINKS, SupportDialog, fetchGithubStars, fmtStars } from '@dartlab/ui-surfaces/terminal';
	import { loadMediaIndex, heroUrl } from '$lib/cards/media';
	import type { MediaIndex } from '$lib/cards/model';
	import Deck from '$lib/cards/Deck.svelte';

	let { data }: { data: PageData } = $props();

	setStaticBase(base);
	const rt = getPublicRuntime();
	const links = DARTLAB_BRAND_LINKS;

	let ghStars = $state<number | null>(null);
	fetchGithubStars(links.repo).then((n) => (ghStars = n));

	let index = $state<IndexRow[]>([]);
	let media = $state<MediaIndex | null>(null);
	let query = $state('');
	let visibleCount = $state(36);
	let searchEl = $state<HTMLInputElement | null>(null);
	let sentinel = $state<HTMLDivElement | null>(null);
	let supportOpen = $state(false);

	// 선택 종목 — URL ?sym= 동기화(공유 가능). 없으면 피드만.
	let selectedSym = $state(data.sym || '');
	let perspectiveKey = $state(data.perspective || 'earningsPower');

	loadJson<IndexRow[]>('map/search-index.json', { fetchFn: fetch, preferLocal: true })
		.then((rows) => (index = rows ?? []))
		.catch(() => {});
	loadMediaIndex().then((m) => (media = m));

	const filtered = $derived.by(() => {
		const q = query.trim().toLowerCase();
		if (!q) return index;
		return index.filter((r) => r.corpName?.toLowerCase().includes(q) || r.stockCode?.includes(q));
	});
	const visible = $derived(filtered.slice(0, visibleCount));

	// 무한 스크롤 — sentinel 가 보이면 더 그린다.
	$effect(() => {
		if (!sentinel) return;
		const io = new IntersectionObserver(
			(entries) => {
				if (entries[0]?.isIntersecting && visibleCount < filtered.length) visibleCount += 36;
			},
			{ rootMargin: '600px' }
		);
		io.observe(sentinel);
		return () => io.disconnect();
	});

	// 검색이 바뀌면 보이는 수 리셋.
	$effect(() => {
		query;
		visibleCount = 36;
	});

	function open(row: IndexRow) {
		selectedSym = row.stockCode;
		goto(`${base}/cards?sym=${row.stockCode}&view=${perspectiveKey}`, { replaceState: false, keepFocus: true, noScroll: true });
	}
	function closeDeck() {
		selectedSym = '';
		goto(`${base}/cards`, { replaceState: false, keepFocus: true, noScroll: true });
	}

	function onWinKey(e: KeyboardEvent) {
		if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
			e.preventDefault();
			searchEl?.focus();
		}
	}
</script>

<svelte:window onkeydown={onWinKey} />
<svelte:head><title>카드 캐러셀 · DartLab</title></svelte:head>

<div class="dlTerm cardsPage">
	<header class="cHeader">
		<a class="brand" href="{base}/">DartLab</a>
		<span class="cTitleTag">카드 캐러셀</span>
		<div class="cSearch">
			<input
				bind:this={searchEl}
				bind:value={query}
				type="search"
				placeholder="회사명·종목코드 검색  (⌘K)"
				aria-label="회사 검색"
			/>
		</div>
		<nav class="cLinks" aria-label="공유·후원">
			<a href={links.repo} target="_blank" rel="noopener" title="GitHub">★ {ghStars != null ? fmtStars(ghStars) : 'GitHub'}</a>
			<button onclick={() => (supportOpen = true)} class="cSupport">후원</button>
		</nav>
	</header>

	{#if selectedSym}
		<div class="player" role="dialog" aria-modal="true" aria-label="카드 플레이어">
			<Deck {rt} sym={selectedSym} bind:perspectiveKey onClose={closeDeck} />
		</div>
	{/if}

	<main class="feed" aria-label="전 종목 카드 피드">
		{#if index.length === 0}
			<p class="feedEmpty">회사 목록을 불러오는 중…</p>
		{:else}
			<div class="grid">
				{#each visible as row (row.stockCode)}
					{@const hero = heroUrl(media, row.stockCode)}
					<button class=" feedCard" class:hasHero={!!hero} onclick={() => open(row)}>
						{#if hero}<img class="fcHero" src={hero} alt={row.corpName} loading="lazy" />{/if}
						<span class="fcBody">
							<span class="fcName">{row.corpName}</span>
							<span class="fcCode">{row.stockCode}{row.industry ? ` · ${row.industry}` : ''}</span>
						</span>
					</button>
				{/each}
			</div>
			<div bind:this={sentinel} class="sentinel"></div>
			{#if filtered.length === 0}<p class="feedEmpty">"{query}" 검색 결과가 없습니다.</p>{/if}
		{/if}
	</main>
</div>

<SupportDialog lang="kr" {links} {base} open={supportOpen} onClose={() => (supportOpen = false)} />

<style>
	.cardsPage {
		min-height: 100vh;
		background: #070b11;
		color: #e7ecf3;
		display: flex;
		flex-direction: column;
	}
	.cHeader {
		position: sticky;
		top: 0;
		z-index: 20;
		display: flex;
		align-items: center;
		gap: 14px;
		padding: 12px 20px;
		background: rgba(8, 12, 18, 0.92);
		backdrop-filter: blur(8px);
		border-bottom: 1px solid #182433;
	}
	.brand {
		font-weight: 700;
		color: #f1f5f9;
		text-decoration: none;
		font-size: 16px;
	}
	.cTitleTag {
		font-size: 12px;
		color: #7dd3fc;
		border: 1px solid #1f4a63;
		border-radius: 999px;
		padding: 2px 9px;
	}
	.cSearch {
		flex: 1;
		max-width: 460px;
	}
	.cSearch input {
		width: 100%;
		padding: 8px 14px;
		border-radius: 999px;
		border: 1px solid #243244;
		background: #0e1722;
		color: #e7ecf3;
		font-size: 13px;
	}
	.cLinks {
		display: flex;
		align-items: center;
		gap: 10px;
		margin-left: auto;
		font-size: 13px;
	}
	.cLinks a {
		color: #cbd5e1;
		text-decoration: none;
	}
	.cSupport {
		background: transparent;
		border: 1px solid #243244;
		color: #cbd5e1;
		border-radius: 999px;
		padding: 5px 12px;
		cursor: pointer;
		font-size: 13px;
	}
	.player {
		position: fixed;
		inset: 0;
		z-index: 40;
		display: flex;
		align-items: stretch;
		justify-content: center;
		padding: clamp(8px, 3vh, 40px) clamp(8px, 4vw, 60px);
		background: rgba(3, 6, 10, 0.86);
		backdrop-filter: blur(4px);
	}
	.player :global(.deck) {
		width: min(520px, 100%);
		max-height: 100%;
	}
	.feed {
		flex: 1;
		padding: 22px 20px 80px;
	}
	.grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
		gap: 14px;
		max-width: 1200px;
		margin: 0 auto;
	}
	.feedCard {
		position: relative;
		aspect-ratio: 4 / 5;
		border-radius: 14px;
		overflow: hidden;
		border: 1px solid #1a2533;
		background: linear-gradient(160deg, #16202e, #0c1521);
		cursor: pointer;
		text-align: left;
		padding: 0;
		color: inherit;
	}
	.fcHero {
		position: absolute;
		inset: 0;
		width: 100%;
		height: 100%;
		object-fit: cover;
		opacity: 0.92;
	}
	.fcBody {
		position: absolute;
		inset: auto 0 0 0;
		display: flex;
		flex-direction: column;
		gap: 2px;
		padding: 14px;
		background: linear-gradient(0deg, rgba(6, 10, 15, 0.92) 25%, rgba(6, 10, 15, 0) 100%);
	}
	.fcName {
		font-size: 15px;
		font-weight: 600;
		color: #f1f5f9;
	}
	.fcCode {
		font-size: 11px;
		color: #94a3b8;
	}
	.sentinel {
		height: 1px;
	}
	.feedEmpty {
		text-align: center;
		color: #64748b;
		padding: 40px 0;
	}
</style>
