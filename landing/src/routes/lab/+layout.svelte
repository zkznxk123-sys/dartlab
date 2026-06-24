<script lang="ts">
	import '@dartlab/ui-design/styles/tokens.css';
	import '@dartlab/ui-design/styles/typography.css';
	import { BrandSwitch } from '@dartlab/ui-surfaces/terminal'; // 브랜드 색 테마 — 공유 컨트롤(터미널 topbar 와 동일)
	import type { Snippet } from 'svelte';

	let { children }: { children: Snippet } = $props();
</script>

<div class="lab-shell">
	<div class="lab-brandswitch"><BrandSwitch /></div>
	{@render children()}
</div>

<style>
	/* 브랜드 색 테마 아이콘 — 터미널 topbar(36px) 바로 아래 우측, SNS 아이콘과 같은 영역. 팝오버는 아래로 열림. */
	.lab-brandswitch {
		position: fixed;
		top: 42px;
		right: 10px;
		z-index: 300;
	}
	.lab-shell {
		min-height: 100vh;
		background: var(--dl-bg-base);
		background-image: var(--dl-grad-bleed);
		color: var(--dl-ink);
		font-family: var(--dl-font-ui);
		-webkit-font-smoothing: antialiased;
		-moz-osx-font-smoothing: grayscale;
		text-rendering: optimizeLegibility;
	}
</style>
