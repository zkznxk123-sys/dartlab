<script lang="ts">
	// 라이브 카드 캐러셀 라우터 — 전 종목의 인스타식 4:5 캐러셀 피드. 각 카드는 첫 슬라이드(회사 사진+이름)가
	// 바로 보이고 그 자리에서 스와이프, 뷰포트 진입 시 라이브 빌드. 공통배선: 데이터=loadJson·미디어=hfMedia.
	import type { PageData } from './$types';
	import { base } from '$app/paths';
	import { setStaticBase } from '@dartlab/ui-runtime/data/dartlabData';
	import { getPublicRuntime } from '$lib/runtime/publicRuntime';
	import '@dartlab/ui-surfaces/terminal/terminal.css';
	import { DARTLAB_BRAND_LINKS, SupportDialog, fetchGithubStars, fmtStars } from '@dartlab/ui-surfaces/terminal';
	import { loadMediaIndex, heroUrls } from '$lib/cards/media';
	import { loadContractCodes, loadContract } from '$lib/cards/contract';
	import type { MediaIndex, CarouselContract } from '$lib/cards/model';
	import Deck from '$lib/cards/Deck.svelte';
	import CoverThumb from '$lib/cards/CoverThumb.svelte';

	let { data }: { data: PageData } = $props();

	setStaticBase(base);
	const rt = getPublicRuntime();
	const links = DARTLAB_BRAND_LINKS;

	let ghStars = $state<number | null>(null);
	fetchGithubStars(links.repo).then((n) => (ghStars = n));

	let media = $state<MediaIndex | null>(null);
	let contractCodes = $state<string[]>([]); // 편집 계약(손글 카피) 있는 회사 = 피드(이미지 있는 것만)
	let loaded = $state(false);
	let query = $state(data.sym || '');
	let visibleCount = $state(12);
	let searchEl = $state<HTMLInputElement | null>(null);
	let sentinel = $state<HTMLDivElement | null>(null);
	let supportOpen = $state(false);
	// 인스타 포스트 모달 — 첫장 클릭 시 좌 캐러셀 + 우 캡션. 계약(caption/title/pinned) 로드 후 오픈.
	let post = $state<{ code: string; corpName: string; contract: CarouselContract | null } | null>(null);

	function openPost(code: string, corpName: string) {
		post = { code, corpName, contract: null };
		loadContract(code).then((c) => {
			if (post && post.code === code) post = { code, corpName, contract: c };
		});
	}
	// 캡션 산문 → 문단 배열(빈 줄 구분). 문단 내부 \n 은 pre-line 으로 보존.
	function captionParas(caption?: string): string[] {
		return String(caption ?? '')
			.split(/\n\s*\n/)
			.map((p) => p.trim())
			.filter(Boolean);
	}

	loadMediaIndex().then((m) => (media = m));
	loadContractCodes().then((s) => {
		// index.json 순서 그대로 = 발간 최신순(build 가 meta date 내림차순 정렬). 재정렬 금지.
		contractCodes = [...s];
		loaded = true;
		// 터미널 카드 버튼이 sym 으로 들어왔는데 그 회사 카드가 없으면 전체 피드로(빈 화면 방지).
		if (data.sym && !contractCodes.includes(data.sym)) query = '';
	});

	// 피드 = 편집 계약 있는 회사(=큐레이션·이미지 있는 것만). 이름은 hfMedia 매니페스트에서.
	const feedRows = $derived.by(() => {
		const rows = contractCodes.map((code) => ({ stockCode: code, corpName: media?.companies[code]?.displayName ?? code }));
		const q = query.trim().toLowerCase();
		return q ? rows.filter((r) => r.corpName.toLowerCase().includes(q) || r.stockCode.toLowerCase().includes(q)) : rows;
	});
	const visible = $derived(feedRows.slice(0, visibleCount));

	$effect(() => {
		if (!sentinel) return;
		const io = new IntersectionObserver(
			(e) => {
				if (e[0]?.isIntersecting && visibleCount < feedRows.length) visibleCount += 24;
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
		} else if (e.key === 'Escape' && post) {
			post = null;
		}
	}
</script>

<svelte:window onkeydown={onWinKey} />
<svelte:head><title>카드 캐러셀 · DartLab</title></svelte:head>

<div class="dlTerm cardsPage">
	<!-- 헤더 = 터미널 top bar 그대로(.dlTerm + terminal.css 재사용). brand · 검색 · SNS 아이콘(터미널 동일 정본). -->
	<header class="cHeader">
		<div class="topBar">
			<a class="brand" href="{base}/" title="DartLab 홈">
				<picture>
					<source srcset="{base}/avatar.webp" type="image/webp" />
					<img class="brandLogo" src="{base}/avatar.png" alt="DartLab" width="22" height="22" />
				</picture>
				<span class="brandName">DartLab</span>
				<span class="brandSlash">/</span>
				<span class="brandTag">cards</span>
			</a>

			<form class="cmdBar" role="search" onsubmit={(e) => e.preventDefault()}>
				<span class="cmdPrompt">‹GO›</span>
				<input class="cmdInput" bind:this={searchEl} bind:value={query} spellcheck={false} placeholder="회사명·종목코드 검색" aria-label="회사 검색" />
				<kbd class="cmdKbd">⌘K</kbd>
			</form>

			<div class="topRight">
				<nav class="sns" aria-label="dartlab 채널">
					<a class="snsBtn" href={links.repo} target="_blank" rel="noopener" title="GitHub" aria-label="GitHub">
						<svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M15 22v-4a4.8 4.8 0 0 0-1-3.5c3 0 6-2 6-5.5.08-1.25-.27-2.48-1-3.5.28-1.15.28-2.35 0-3.5 0 0-1 0-3 1.5-2.64-.5-5.36-.5-8 0C6 2 5 2 5 2c-.3 1.15-.3 2.35 0 3.5A5.403 5.403 0 0 0 4 9c0 3.5 3 5.5 6 5.5-.39.49-.68 1.05-.85 1.65-.17.6-.22 1.23-.15 1.85v4" /><path d="M9 18c-4.51 2-5-2-7-2" /></svg>
					</a>
					{#if ghStars != null}
						<a class="ghStars" href={links.repo} target="_blank" rel="noopener" title="GitHub 스타로 응원"><span class="ghStar">★</span>{fmtStars(ghStars)}</a>
					{/if}
					<button class="snsBtn snsHeart" onclick={() => (supportOpen = true)} title="후원·기여" aria-label="후원·기여">
						<svg viewBox="0 0 24 24" width="15" height="15" fill="rgba(251, 113, 133, 0.32)" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.76 0-3 .5-4.5 2-1.5-1.5-2.74-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.3 1.5 4.05 3 5.5l7 7Z" /></svg>
					</button>
					<a class="snsBtn" href={links.youtube} target="_blank" rel="noopener" title="YouTube" aria-label="YouTube">
						<svg viewBox="0 0 24 24" width="15" height="15" fill="currentColor" aria-hidden="true"><path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z" /></svg>
					</a>
					<a class="snsBtn" href={links.threads} target="_blank" rel="noopener" title="Threads · @dartlab.ai" aria-label="Threads">
						<svg viewBox="0 0 24 24" width="15" height="15" fill="currentColor" aria-hidden="true"><path d="M12.186 24h-.007c-3.581-.024-6.334-1.205-8.184-3.509C2.35 18.44 1.5 15.586 1.472 12.01v-.017c.03-3.579.879-6.43 2.525-8.482C5.845 1.205 8.6.024 12.18 0h.014c2.746.02 5.043.725 6.826 2.098 1.677 1.29 2.858 3.13 3.509 5.467l-2.04.569c-1.104-3.96-3.898-5.984-8.304-6.015-2.91.022-5.11.936-6.54 2.717C4.307 6.504 3.616 8.914 3.589 12c.027 3.086.718 5.496 2.057 7.164 1.43 1.783 3.631 2.698 6.54 2.717 2.623-.02 4.358-.631 5.8-2.045 1.647-1.613 1.618-3.593 1.09-4.798-.31-.71-.873-1.3-1.634-1.75-.192 1.352-.622 2.446-1.284 3.272-.886 1.102-2.14 1.704-3.73 1.79-1.202.065-2.361-.218-3.259-.801-1.063-.689-1.685-1.74-1.752-2.964-.065-1.19.408-2.285 1.33-3.082.88-.76 2.119-1.207 3.583-1.291a13.853 13.853 0 0 1 3.02.142c-.126-.742-.375-1.332-.75-1.757-.513-.586-1.308-.883-2.359-.89h-.029c-.844 0-1.992.232-2.721 1.32L7.734 7.847c.98-1.454 2.568-2.256 4.478-2.256h.044c3.194.02 5.097 1.975 5.287 5.388.108.046.216.094.321.142 1.49.7 2.58 1.761 3.154 3.07.797 1.82.871 4.79-1.548 7.158-1.85 1.81-4.094 2.628-7.277 2.65Zm1.003-11.69c-.242 0-.487.007-.739.021-1.836.103-2.98.946-2.916 2.143.067 1.256 1.452 1.839 2.784 1.767 1.224-.065 2.818-.543 3.086-3.71a10.5 10.5 0 0 0-2.215-.221z" /></svg>
					</a>
					<a class="snsBtn" href={links.instagram} target="_blank" rel="noopener" title="Instagram · @dartlab.ai" aria-label="Instagram">
						<svg viewBox="0 0 24 24" width="15" height="15" fill="currentColor" aria-hidden="true"><path d="M12 0C8.74 0 8.333.015 7.053.072 5.775.132 4.905.333 4.14.63c-.789.306-1.459.717-2.126 1.384S.935 3.35.63 4.14C.333 4.905.131 5.775.072 7.053.012 8.333 0 8.74 0 12s.015 3.667.072 4.947c.06 1.277.261 2.148.558 2.913.306.788.717 1.459 1.384 2.126.667.666 1.336 1.079 2.126 1.384.766.296 1.636.499 2.913.558C8.333 23.988 8.74 24 12 24s3.667-.015 4.947-.072c1.277-.06 2.148-.262 2.913-.558.788-.306 1.459-.718 2.126-1.384.666-.667 1.079-1.335 1.384-2.126.296-.765.499-1.636.558-2.913.06-1.28.072-1.687.072-4.947s-.015-3.667-.072-4.947c-.06-1.277-.262-2.149-.558-2.913-.306-.789-.718-1.459-1.384-2.126C21.319 1.347 20.651.935 19.86.63c-.765-.297-1.636-.499-2.913-.558C15.667.012 15.26 0 12 0zm0 2.16c3.203 0 3.585.016 4.85.071 1.17.055 1.805.249 2.227.415.562.217.96.477 1.382.896.419.42.679.819.896 1.381.164.422.36 1.057.413 2.227.057 1.266.07 1.646.07 4.85s-.015 3.585-.074 4.85c-.061 1.17-.256 1.805-.421 2.227-.224.562-.479.96-.899 1.382-.419.419-.824.679-1.38.896-.42.164-1.065.36-2.235.413-1.274.057-1.649.07-4.859.07-3.211 0-3.586-.015-4.859-.074-1.171-.061-1.816-.256-2.236-.421-.569-.224-.96-.479-1.379-.899-.421-.419-.69-.824-.9-1.38-.165-.42-.359-1.065-.42-2.235-.045-1.26-.061-1.649-.061-4.844 0-3.196.016-3.586.061-4.861.061-1.17.255-1.814.42-2.234.21-.57.479-.96.9-1.381.419-.419.81-.689 1.379-.898.42-.166 1.051-.361 2.221-.421 1.275-.045 1.65-.06 4.859-.06l.045.03zm0 3.678c-3.405 0-6.162 2.76-6.162 6.162 0 3.405 2.76 6.162 6.162 6.162 3.405 0 6.162-2.76 6.162-6.162 0-3.405-2.76-6.162-6.162-6.162zM12 16c-2.21 0-4-1.79-4-4s1.79-4 4-4 4 1.79 4 4-1.79 4-4 4zm7.846-10.405c0 .795-.646 1.44-1.44 1.44-.795 0-1.44-.646-1.44-1.44 0-.794.646-1.439 1.44-1.439.793-.001 1.44.645 1.44 1.439z" /></svg>
					</a>
				</nav>
			</div>
		</div>
	</header>

	<main class="feed" aria-label="기업이야기 카드 캐러셀 피드">
		{#if !loaded}
			<p class="feedEmpty">캐러셀 불러오는 중…</p>
		{:else}
			<div class="grid">
				{#each visible as row (row.stockCode)}
					<CoverThumb {rt} code={row.stockCode} corpName={row.corpName} {base} {media} onOpen={() => openPost(row.stockCode, row.corpName)} />
				{/each}
			</div>
			<div bind:this={sentinel} class="sentinel"></div>
			{#if feedRows.length === 0}<p class="feedEmpty">{query ? `"${query}" 검색 결과가 없습니다.` : '게시된 편집 캐러셀이 없습니다.'}</p>{/if}
		{/if}
	</main>

	{#if post}
		<!-- 인스타 포스트 모달 — 좌 캐러셀(스와이프) + 우 캡션. 배경 클릭/Esc 닫기. -->
		<div class="post" role="dialog" aria-modal="true" aria-label="{post.corpName} 포스트" onclick={() => (post = null)}>
			<div class="postInner" role="document" onclick={(e) => e.stopPropagation()}>
				<div class="postLeft">
					<Deck {rt} sym={post.code} corpName={post.corpName} {base} heroUrls={heroUrls(media, post.code)} />
				</div>
				<aside class="postRight">
					<header class="prHead">
						<picture>
							<source srcset="{base}/avatar.webp" type="image/webp" />
							<img src="{base}/avatar.png" alt="DartLab" width="34" height="34" />
						</picture>
						<div class="prWho"><b>dartlab</b><small>COMPANY STORY BY TICKER</small></div>
					</header>
					<div class="prScroll">
						<p class="prMeta">{post.contract?.name ?? post.corpName} · {post.code}</p>
						{#if post.contract?.title}<h2 class="prTitle">{post.contract.title}</h2>{/if}
						{#if post.contract}
							{#each captionParas(post.contract.caption) as para (para)}<p class="prPara">{para}</p>{/each}
							{#if post.contract.pinnedComment}<p class="prPinned">{post.contract.pinnedComment}</p>{/if}
							{#if !post.contract.caption}<p class="prPara prMuted">캡션이 아직 준비되지 않았습니다.</p>{/if}
						{:else}
							<p class="prPara prMuted">불러오는 중…</p>
						{/if}
					</div>
				</aside>
				<button class="postClose" onclick={() => (post = null)} aria-label="닫기">✕</button>
			</div>
		</div>
	{/if}
</div>

<SupportDialog lang="kr" {links} {base} open={supportOpen} onClose={() => (supportOpen = false)} />

<style>
	.cardsPage {
		/* ⚠ .dlTerm(terminal.css)은 height:100vh·overflow:hidden(고정 풀스크린 앱)이라 그대로 두면 페이지가
		   스크롤되지 않는다. /cards 는 일반 문서 스크롤이라 height/overflow 를 여기서 덮어쓴다(specificity 우위). */
		min-height: 100vh;
		height: auto;
		overflow: visible;
		background: #030509;
		color: #f1f5f9;
		display: flex;
		flex-direction: column;
		font-size: 16px;
		font-family: 'Pretendard Variable', 'Pretendard', system-ui, sans-serif;
	}
	/* 헤더 내부(topBar·brand·cmdBar·sns·snsBtn 등)는 terminal.css(.dlTerm 스코프) 정본 그대로. 여기선
	   sticky 래퍼만. */
	.cHeader {
		position: sticky;
		top: 0;
		z-index: 20;
		padding: 10px 18px;
		background: rgba(5, 8, 17, 0.92);
		backdrop-filter: blur(8px);
	}
	/* 터미널 topBar 정본은 하단에 amber 보더(.dlTerm .topBar border-bottom: var(--bdAmber))를 긋는다.
	   /cards 는 그 줄을 원치 않음 → 스코프 우위로 제거(헤더 SNS 마크업은 그대로 재사용). */
	.cardsPage :global(.topBar) {
		border-bottom: none;
	}
	.feed {
		flex: 1;
		padding: 24px 20px 80px;
	}
	.grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
		gap: 24px;
		max-width: 1480px;
		margin: 0 auto;
		align-items: start;
	}
	.sentinel {
		height: 1px;
	}
	/* 인스타 포스트 모달 — 좌 캐러셀(4:5) + 우 캡션 패널 */
	.post {
		position: fixed;
		inset: 0;
		z-index: 50;
		display: flex;
		align-items: center;
		justify-content: center;
		padding: 3vh 3vw;
		background: rgba(2, 4, 8, 0.92);
		backdrop-filter: blur(6px);
	}
	.postInner {
		display: flex;
		height: min(90vh, 880px);
		max-width: 96vw;
		background: #0b0e14;
		border: 1px solid #1e2433;
		border-radius: 14px;
		overflow: hidden;
	}
	.postLeft {
		height: 100%;
		aspect-ratio: 1080 / 1350;
		flex: 0 0 auto;
		background: #050811;
	}
	.postRight {
		width: 360px;
		max-width: 42vw;
		height: 100%;
		display: flex;
		flex-direction: column;
		border-left: 1px solid #1e2433;
	}
	.prHead {
		display: flex;
		align-items: center;
		gap: 10px;
		padding: 16px 18px;
		border-bottom: 1px solid #161b26;
		flex: 0 0 auto;
	}
	.prHead img {
		border-radius: 50%;
	}
	.prWho {
		display: flex;
		flex-direction: column;
		line-height: 1.2;
	}
	.prWho b {
		font-size: 14px;
		font-weight: 800;
		color: #f6f8fb;
	}
	.prWho small {
		font-size: 8px;
		letter-spacing: 0.14em;
		color: #94a3b8;
		text-transform: uppercase;
	}
	.prScroll {
		flex: 1;
		overflow-y: auto;
		padding: 18px;
	}
	.prMeta {
		margin: 0 0 6px;
		font-family: Menlo, Consolas, monospace;
		font-size: 12px;
		letter-spacing: 0.08em;
		color: #ff3f6f;
		font-weight: 700;
	}
	.prTitle {
		margin: 0 0 14px;
		font-size: 19px;
		font-weight: 800;
		line-height: 1.3;
		color: #f6f8fb;
		word-break: keep-all;
	}
	.prPara {
		margin: 0 0 13px;
		font-size: 14.5px;
		line-height: 1.62;
		color: #d8e2f0;
		white-space: pre-line;
		word-break: keep-all;
	}
	.prPinned {
		margin: 16px 0 0;
		padding-top: 14px;
		border-top: 1px solid #1e2433;
		font-size: 12.5px;
		line-height: 1.55;
		color: #94a3b8;
		white-space: pre-line;
		word-break: keep-all;
	}
	.prMuted {
		color: #64748b;
	}
	.postClose {
		position: absolute;
		top: 18px;
		right: 22px;
		width: 40px;
		height: 40px;
		border-radius: 50%;
		border: 1px solid #243244;
		background: rgba(8, 12, 18, 0.8);
		color: #cbd5e1;
		font-size: 18px;
		cursor: pointer;
		z-index: 2;
	}
	/* 좁은 화면 — 세로 스택(캐러셀 위, 캡션 아래) */
	@media (max-width: 820px) {
		.postInner {
			flex-direction: column;
			height: auto;
			max-height: 92vh;
			overflow-y: auto;
		}
		.postLeft {
			height: auto;
			width: 100%;
			aspect-ratio: 1080 / 1350;
		}
		.postRight {
			width: 100%;
			max-width: none;
			border-left: none;
			border-top: 1px solid #1e2433;
		}
	}
	.feedEmpty {
		text-align: center;
		color: #64748b;
		padding: 40px 0;
	}
</style>
