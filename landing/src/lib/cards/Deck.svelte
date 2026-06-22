<script lang="ts">
	// 인스타식 슬라이드 플레이어 — buildDeck(라이브) 결과를 scroll-snap 트랙으로. 키보드(←→·Space·Esc)·
	// aria-live 진행바·관점 탭. 굽지 않음(조회 시점 조립). 한 종목 1덱, 관점 전환은 재빌드.
	import type { DartLabRuntime } from '@dartlab/ui-contracts';
	import { buildDeck, DECK_PERSPECTIVES } from './build';
	import type { CarouselDeck } from './model';
	import CardSlide from './CardSlide.svelte';

	let {
		rt,
		sym,
		perspectiveKey = $bindable('earningsPower'),
		onClose
	}: {
		rt: DartLabRuntime;
		sym: string;
		perspectiveKey?: string;
		onClose?: () => void;
	} = $props();

	let deck = $state<CarouselDeck | null>(null);
	let loading = $state(true);
	let idx = $state(0);
	let track = $state<HTMLDivElement | null>(null);
	let tok = 0;

	$effect(() => {
		const code = sym;
		const pk = perspectiveKey;
		const t = ++tok;
		loading = true;
		deck = null;
		idx = 0;
		buildDeck(rt, code, pk)
			.then((d) => {
				if (t === tok) {
					deck = d;
					loading = false;
				}
			})
			.catch(() => {
				if (t === tok) loading = false;
			});
	});

	const total = $derived(deck?.cards.length ?? 0);

	function go(to: number) {
		if (!deck || !track) return;
		const n = Math.max(0, Math.min(total - 1, to));
		idx = n;
		const slide = track.children[n] as HTMLElement | undefined;
		slide?.scrollIntoView({ behavior: 'smooth', inline: 'start', block: 'nearest' });
	}

	function onScroll() {
		if (!track) return;
		const w = track.clientWidth || 1;
		idx = Math.round(track.scrollLeft / w);
	}

	function onKey(e: KeyboardEvent) {
		if (e.key === 'ArrowRight' || e.key === ' ') {
			e.preventDefault();
			go(idx + 1);
		} else if (e.key === 'ArrowLeft') {
			e.preventDefault();
			go(idx - 1);
		} else if (e.key === 'Escape') {
			onClose?.();
		}
	}
</script>

<svelte:window onkeydown={onKey} />

<section class="deck" aria-roledescription="carousel" aria-label="{deck?.corpName ?? sym} 카드 캐러셀">
	<header class="dTop">
		<div class="dTitle">
			<strong>{deck?.corpName ?? sym}</strong>
			<span class="dCode">{sym}</span>
		</div>
		<nav class="dTabs" aria-label="관점 선택">
			{#each DECK_PERSPECTIVES as p (p.key)}
				<button class="dTab" class:on={perspectiveKey === p.key} onclick={() => (perspectiveKey = p.key)}>{p.label}</button>
			{/each}
		</nav>
		{#if onClose}<button class="dClose" onclick={onClose} aria-label="닫기">✕</button>{/if}
	</header>

	{#if loading}
		<div class="dLoad">불러오는 중…</div>
	{:else if deck}
		<div class="dTrack" bind:this={track} onscroll={onScroll} tabindex="-1">
			{#each deck.cards as card, i (i)}
				<div class="dSlot" aria-hidden={i !== idx}>
					<CardSlide {card} {rt} />
				</div>
			{/each}
		</div>

		<footer class="dFoot">
			<button class="dNav" onclick={() => go(idx - 1)} disabled={idx === 0} aria-label="이전 슬라이드">‹</button>
			<div class="dDots" role="group" aria-label="슬라이드 위치">
				{#each deck.cards as _, i (i)}
					<button class="dDot" class:on={i === idx} onclick={() => go(i)} aria-label="{i + 1}번 슬라이드" aria-current={i === idx}></button>
				{/each}
			</div>
			<button class="dNav" onclick={() => go(idx + 1)} disabled={idx >= total - 1} aria-label="다음 슬라이드">›</button>
		</footer>
		<p class="dLive" aria-live="polite">{idx + 1} / {total}</p>
	{/if}
</section>

<style>
	.deck {
		display: flex;
		flex-direction: column;
		height: 100%;
		background: #0b1119;
		border: 1px solid #1c2838;
		border-radius: 16px;
		overflow: hidden;
	}
	.dTop {
		display: flex;
		align-items: center;
		gap: 12px;
		padding: 12px 16px;
		border-bottom: 1px solid #182433;
	}
	.dTitle {
		display: flex;
		align-items: baseline;
		gap: 8px;
	}
	.dTitle strong {
		font-size: 15px;
		color: #f1f5f9;
	}
	.dCode {
		font-size: 12px;
		color: #64748b;
		font-variant-numeric: tabular-nums;
	}
	.dTabs {
		display: flex;
		gap: 4px;
		margin-left: auto;
		flex-wrap: wrap;
	}
	.dTab {
		padding: 5px 10px;
		font-size: 12px;
		color: #93a4b8;
		background: transparent;
		border: 1px solid transparent;
		border-radius: 999px;
		cursor: pointer;
	}
	.dTab.on {
		color: #7dd3fc;
		border-color: #1f4a63;
		background: rgba(125, 211, 252, 0.08);
	}
	.dClose {
		background: transparent;
		border: none;
		color: #94a3b8;
		font-size: 16px;
		cursor: pointer;
		padding: 4px 8px;
	}
	.dLoad {
		flex: 1;
		display: flex;
		align-items: center;
		justify-content: center;
		color: #64748b;
	}
	.dTrack {
		flex: 1;
		display: flex;
		overflow-x: auto;
		scroll-snap-type: x mandatory;
		scrollbar-width: none;
	}
	.dTrack::-webkit-scrollbar {
		display: none;
	}
	.dSlot {
		flex: 0 0 100%;
		width: 100%;
		scroll-snap-align: start;
	}
	.dFoot {
		display: flex;
		align-items: center;
		gap: 12px;
		padding: 10px 16px;
		border-top: 1px solid #182433;
	}
	.dNav {
		width: 30px;
		height: 30px;
		border-radius: 50%;
		border: 1px solid #243244;
		background: #121b27;
		color: #cbd5e1;
		font-size: 16px;
		cursor: pointer;
	}
	.dNav:disabled {
		opacity: 0.35;
		cursor: default;
	}
	.dDots {
		display: flex;
		gap: 6px;
		margin: 0 auto;
		flex-wrap: wrap;
		justify-content: center;
	}
	.dDot {
		width: 7px;
		height: 7px;
		border-radius: 50%;
		border: none;
		background: #2b3a4d;
		cursor: pointer;
		padding: 0;
	}
	.dDot.on {
		background: #7dd3fc;
	}
	.dLive {
		position: absolute;
		width: 1px;
		height: 1px;
		overflow: hidden;
		clip: rect(0 0 0 0);
	}
</style>
