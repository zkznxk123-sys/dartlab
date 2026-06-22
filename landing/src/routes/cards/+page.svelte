<script lang="ts">
	// 라이브 카드 캐러셀 라우터 — 전 종목의 인스타식 4:5 캐러셀 피드. 각 카드는 첫 슬라이드(회사 사진+이름)가
	// 바로 보이고 그 자리에서 스와이프, 뷰포트 진입 시 라이브 빌드. 공통배선: 데이터=loadJson·미디어=hfMedia.
	import type { PageData } from './$types';
	import { base } from '$app/paths';
	import { setStaticBase, loadJson } from '@dartlab/ui-runtime/data/dartlabData';
	import type { IndexRow } from '@dartlab/ui-contracts';
	import { getPublicRuntime } from '$lib/runtime/publicRuntime';
	import '@dartlab/ui-surfaces/terminal/terminal.css';
	import { DARTLAB_BRAND_LINKS, SupportDialog, fetchGithubStars, fmtStars } from '@dartlab/ui-surfaces/terminal';
	import { loadMediaIndex, heroUrls } from '$lib/cards/media';
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
	let query = $state(data.sym || '');
	let visibleCount = $state(24);
	let searchEl = $state<HTMLInputElement | null>(null);
	let sentinel = $state<HTMLDivElement | null>(null);
	let supportOpen = $state(false);

	loadJson<IndexRow[]>('map/search-index.json', { fetchFn: fetch, preferLocal: true })
		.then((rows) => (index = rows ?? []))
		.catch(() => {});
	loadMediaIndex().then((m) => (media = m));

	// 사진 있는 회사 우선(피드 첫 화면이 채워지게) — 그다음 나머지.
	const ordered = $derived.by(() => {
		const q = query.trim().toLowerCase();
		const rows = q ? index.filter((r) => r.corpName?.toLowerCase().includes(q) || r.stockCode?.includes(q)) : index;
		if (!media) return rows;
		const has = (r: IndexRow) => (media!.companies[/^\d{6}$/.test(r.stockCode) ? r.stockCode : r.stockCode.toUpperCase()]?.assets.length ?? 0) > 0;
		return [...rows].sort((a, b) => Number(has(b)) - Number(has(a)));
	});
	const visible = $derived(ordered.slice(0, visibleCount));

	$effect(() => {
		if (!sentinel) return;
		const io = new IntersectionObserver(
			(e) => {
				if (e[0]?.isIntersecting && visibleCount < ordered.length) visibleCount += 24;
			},
			{ rootMargin: '800px' }
		);
		io.observe(sentinel);
		return () => io.disconnect();
	});

	$effect(() => {
		query;
		visibleCount = 24;
	});

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
		<a class="brand" href="{base}/">
			<picture><source srcset="{base}/avatar.webp" type="image/webp" /><img src="{base}/avatar.png" alt="DartLab" width="22" height="22" /></picture>
			DartLab
		</a>
		<span class="tag">카드 캐러셀</span>
		<div class="cSearch">
			<input bind:this={searchEl} bind:value={query} type="search" placeholder="회사명·종목코드 검색  (⌘K)" aria-label="회사 검색" />
		</div>
		<nav class="cLinks" aria-label="공유·후원">
			<a href={links.repo} target="_blank" rel="noopener" title="GitHub">★ {ghStars != null ? fmtStars(ghStars) : 'GitHub'}</a>
			<button onclick={() => (supportOpen = true)} class="cSupport">후원</button>
		</nav>
	</header>

	<main class="feed" aria-label="전 종목 카드 캐러셀 피드">
		{#if index.length === 0}
			<p class="feedEmpty">회사 목록을 불러오는 중…</p>
		{:else}
			<div class="grid">
				{#each visible as row (row.stockCode)}
					<Deck {rt} sym={row.stockCode} corpName={row.corpName} {base} heroUrls={heroUrls(media, row.stockCode)} />
				{/each}
			</div>
			<div bind:this={sentinel} class="sentinel"></div>
			{#if ordered.length === 0}<p class="feedEmpty">"{query}" 검색 결과가 없습니다.</p>{/if}
		{/if}
	</main>
</div>

<SupportDialog lang="kr" {links} {base} open={supportOpen} onClose={() => (supportOpen = false)} />

<style>
	.cardsPage {
		min-height: 100vh;
		background: #030509;
		color: #f1f5f9;
		display: flex;
		flex-direction: column;
		font-family: 'Pretendard Variable', 'Pretendard', system-ui, sans-serif;
	}
	.cHeader {
		position: sticky;
		top: 0;
		z-index: 20;
		display: flex;
		align-items: center;
		gap: 14px;
		padding: 12px 20px;
		background: rgba(5, 8, 17, 0.92);
		backdrop-filter: blur(8px);
		border-bottom: 1px solid #1e2433;
	}
	.brand {
		display: inline-flex;
		align-items: center;
		gap: 8px;
		font-weight: 800;
		color: #f1f5f9;
		text-decoration: none;
		font-size: 16px;
	}
	.tag {
		font-size: 12px;
		color: #fb923c;
		border: 1px solid rgba(251, 146, 60, 0.4);
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
		color: #f1f5f9;
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
	.feed {
		flex: 1;
		padding: 24px 20px 80px;
	}
	.grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
		gap: 22px;
		max-width: 1320px;
		margin: 0 auto;
		align-items: start;
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
