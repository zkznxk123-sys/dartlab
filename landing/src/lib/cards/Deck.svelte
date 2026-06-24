<script lang="ts">
	// 인스타식 4:5 카드 캐러셀(인라인) — 첫 슬라이드(표지)는 hfMedia 만으로 즉시, 뷰포트에 들어오면
	// buildDeck(라이브)로 전체 슬라이드 업그레이드(피드 가벼움). 코너 크롬 = 회사뱃지·dartlab 아바타·페이지뱃지.
	// 색감·규격은 기존 SNS 캐러셀(colors.ts·1080×1350) 재현. 키보드 ←→ 는 포커스된 덱에만.
	import type { DartLabRuntime } from '@dartlab/ui-contracts';
	import { buildDeck, DECK_PERSPECTIVES } from './build';
	import type { CarouselDeck } from './model';
	import CardSlide from './CardSlide.svelte';

	let {
		rt,
		sym,
		slug,
		corpName,
		heroUrls = [],
		perspectiveKey = 'earningsPower',
		onEnlarge
	}: {
		rt: DartLabRuntime;
		sym: string;
		slug: string;
		corpName: string;
		heroUrls?: string[];
		perspectiveKey?: string;
		onEnlarge?: () => void;
	} = $props();

	// 표지 미리보기 — buildReport 없이 hfMedia 사진+이름만(피드에서 첫장 즉시 노출).
	function previewDeck(): CarouselDeck {
		return {
			stockCode: sym,
			corpName,
			perspectiveKey,
			perspectiveLabel: DECK_PERSPECTIVES.find((p) => p.key === perspectiveKey)?.label ?? '',
			asOf: '',
			heroUrls,
			cards: [
				{
					kind: 'cover',
					corpName,
					stockCode: sym,
					perspectiveLabel: DECK_PERSPECTIVES.find((p) => p.key === perspectiveKey)?.label ?? '',
					conclusion: '',
					dataBasis: '',
					bg: heroUrls[0]
				}
			]
		};
	}

	let deck = $state<CarouselDeck>(previewDeck());
	let built = $state(false);
	let idx = $state(0);
	let track = $state<HTMLDivElement | null>(null);
	let root = $state<HTMLElement | null>(null);
	let tok = 0;

	// 빌드 전에는 미디어(회사명·사진) 비동기 로드에 맞춰 표지 미리보기를 갱신 — 코드("000270")만 뜨고
	// 사진이 빈 첫 페인트 방지. previewDeck() 이 corpName/heroUrls prop 을 읽으므로 그 갱신을 추종한다.
	$effect(() => {
		if (!built) deck = previewDeck();
	});

	// 관점이 바뀌면(사용자 조작) 재빌드. 첫 진입은 IntersectionObserver 가 트리거.
	function load() {
		const t = ++tok;
		buildDeck(rt, { code: sym, slug }, perspectiveKey)
			.then((d) => {
				if (t === tok) {
					deck = d;
					built = true;
					idx = 0;
				}
			})
			.catch(() => {});
	}

	// 뷰포트 진입 시 1회 빌드.
	$effect(() => {
		if (!root) return;
		const io = new IntersectionObserver(
			(e) => {
				if (e[0]?.isIntersecting && !built) load();
			},
			{ rootMargin: '300px' }
		);
		io.observe(root);
		return () => io.disconnect();
	});

	const total = $derived(deck.cards.length);

	function go(to: number) {
		if (!track) return;
		const n = Math.max(0, Math.min(total - 1, to));
		idx = n;
		(track.children[n] as HTMLElement | undefined)?.scrollIntoView({ behavior: 'smooth', inline: 'start', block: 'nearest' });
	}
	function onScroll() {
		if (!track) return;
		idx = Math.round(track.scrollLeft / (track.clientWidth || 1));
	}
	function onKey(e: KeyboardEvent) {
		if (e.key === 'ArrowRight') {
			e.preventDefault();
			go(idx + 1);
		} else if (e.key === 'ArrowLeft') {
			e.preventDefault();
			go(idx - 1);
		}
	}

	// 자동재생 — 점 좌측 재생버튼 토글. 3초마다 다음 슬라이드(끝이면 처음으로 순환). 다시 누르면 정지.
	let playing = $state(false);
	let timer: ReturnType<typeof setInterval> | null = null;
	function togglePlay() {
		playing = !playing;
		if (timer) {
			clearInterval(timer);
			timer = null;
		}
		if (playing) timer = setInterval(() => go(idx >= total - 1 ? 0 : idx + 1), 3000);
	}
	$effect(() => () => {
		if (timer) clearInterval(timer);
	});
</script>

<section
	class="deck"
	bind:this={root}
	tabindex="0"
	role="group"
	aria-roledescription="carousel"
	aria-label="{corpName} 카드 캐러셀"
	onkeydown={onKey}
>
	<div class="frame">
		<div class="track" bind:this={track} onscroll={onScroll}>
			{#each deck.cards as card, i (i)}
				<div class="slot" aria-hidden={i !== idx}><CardSlide {card} {rt} /></div>
			{/each}
		</div>

		<!-- 코너 크롬(전 슬라이드 고정) — 회사명·코드 + 페이지 + 확대. dartlab 서명은 우측 캡션 패널에 있어
		     캐러셀 이미지엔 안 얹는다(중복 + 슬라이드 본문과 겹침 방지). -->
		<div class="badge">{deck.corpName}{sym ? ` · ${sym}` : ''}</div>
		{#if total > 1}<div class="pageBadge">{idx + 1} / {total}</div>{/if}
		{#if onEnlarge}<button class="enlarge" onclick={onEnlarge} title="확대" aria-label="확대">⤢</button>{/if}

		<!-- 좌우 네비 -->
		{#if total > 1}
			<button class="nav left" onclick={() => go(idx - 1)} disabled={idx === 0} aria-label="이전">‹</button>
			<button class="nav right" onclick={() => go(idx + 1)} disabled={idx >= total - 1} aria-label="다음">›</button>
			<div class="dots">
				<button class="playBtn" class:on={playing} onclick={togglePlay} aria-label={playing ? '자동재생 정지' : '자동재생'} title={playing ? '정지' : '자동재생 (3초)'}>
					{#if playing}
						<svg viewBox="0 0 10 10" width="8" height="8" aria-hidden="true"><rect x="1.5" y="1" width="2.5" height="8" /><rect x="6" y="1" width="2.5" height="8" /></svg>
					{:else}
						<svg viewBox="0 0 10 10" width="8" height="8" aria-hidden="true"><path d="M2 1 L9 5 L2 9 Z" /></svg>
					{/if}
				</button>
				{#each deck.cards as _, i (i)}
					<button class="dot" class:on={i === idx} onclick={() => go(i)} aria-label="{i + 1}번" aria-current={i === idx}></button>
				{/each}
			</div>
		{/if}
		<p class="live" aria-live="polite">{idx + 1} / {total}</p>
	</div>
</section>

<style>
	.deck {
		outline: none;
	}
	.deck:focus-visible .frame {
		box-shadow: 0 0 0 2px var(--dl-accent);
	}
	.frame {
		position: relative;
		aspect-ratio: 1080 / 1350;
		width: 100%;
		border-radius: 16px;
		overflow: hidden;
		background: #050811;
		border: 1px solid #1e2433;
	}
	.track {
		display: flex;
		height: 100%;
		overflow-x: auto;
		scroll-snap-type: x mandatory;
		scrollbar-width: none;
	}
	.track::-webkit-scrollbar {
		display: none;
	}
	.slot {
		flex: 0 0 100%;
		width: 100%;
		height: 100%;
		scroll-snap-align: start;
	}
	/* chrome */
	.badge {
		position: absolute;
		top: 14px;
		right: 16px;
		font-size: 13px;
		font-weight: 700;
		color: #f1f5f9;
		padding: 6px 13px;
		background: rgba(5, 8, 17, 0.78);
		border: 1px solid rgba(232, 234, 237, 0.12);
		border-radius: 999px;
		z-index: 3;
	}
	.pageBadge {
		position: absolute;
		right: 16px;
		bottom: 14px;
		font-size: 12px;
		font-weight: 700;
		color: #f1f5f9;
		padding: 5px 11px;
		background: rgba(5, 8, 17, 0.78);
		border: 1px solid rgba(232, 234, 237, 0.12);
		border-radius: 999px;
		z-index: 3;
	}
	.enlarge {
		position: absolute;
		top: 12px;
		left: 12px;
		width: 30px;
		height: 30px;
		border-radius: 8px;
		border: 1px solid rgba(232, 234, 237, 0.14);
		background: rgba(5, 8, 17, 0.6);
		color: #e7ecf3;
		font-size: 15px;
		cursor: pointer;
		z-index: 3;
		opacity: 0;
		transition: opacity 0.15s;
	}
	.frame:hover .enlarge {
		opacity: 1;
	}
	.nav {
		position: absolute;
		top: 50%;
		transform: translateY(-50%);
		width: 34px;
		height: 34px;
		border-radius: 50%;
		border: none;
		background: rgba(5, 8, 17, 0.5);
		color: #f1f5f9;
		font-size: 18px;
		cursor: pointer;
		z-index: 3;
		opacity: 0;
		transition: opacity 0.15s;
	}
	.frame:hover .nav {
		opacity: 1;
	}
	.nav:disabled {
		opacity: 0 !important;
	}
	.nav.left {
		left: 8px;
	}
	.nav.right {
		right: 8px;
	}
	.dots {
		position: absolute;
		bottom: 16px;
		left: 50%;
		transform: translateX(-50%);
		display: flex;
		align-items: center;
		gap: 5px;
		flex-wrap: wrap;
		justify-content: center;
		max-width: 64%;
		z-index: 3;
	}
	/* 재생/정지 — 점 행 맨 좌측 작은 토글. 켜지면 테마색. */
	.playBtn {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		width: 14px;
		height: 14px;
		margin-right: 3px;
		border-radius: 50%;
		border: none;
		padding: 0;
		cursor: pointer;
		background: rgba(255, 255, 255, 0.4);
		color: #050811;
	}
	.playBtn svg {
		fill: currentColor;
	}
	.playBtn.on,
	.playBtn:hover {
		background: var(--dl-accent);
	}
	.dot {
		width: 6px;
		height: 6px;
		border-radius: 50%;
		border: none;
		background: rgba(255, 255, 255, 0.4);
		cursor: pointer;
		padding: 0;
	}
	.dot.on {
		background: var(--dl-accent);
	}
	.live {
		position: absolute;
		width: 1px;
		height: 1px;
		overflow: hidden;
		clip: rect(0 0 0 0);
	}
</style>
