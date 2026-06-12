<script lang="ts">
	import '../app.css';
	import '$lib/styles/v2-tokens.css';
	import '$lib/styles/tokens.css';
	import '$lib/styles/typography.css';
	import type { Snippet } from 'svelte';
	import CloudflareWebAnalytics from '$lib/components/CloudflareWebAnalytics.svelte';
	import CommandPalette from '$lib/components/CommandPalette.svelte';

	let { children }: { children: Snippet } = $props();
</script>

<CloudflareWebAnalytics />
<CommandPalette />
{@render children()}

<style>
	/* 전역 모바일 보호 — viewport 가로 스크롤 차단
	   app.css에 두면 Tailwind v4 빌드에서 누락되므로 svelte global로 강제 */
	:global(html) {
		max-width: 100vw;
		overflow-x: clip;
	}
	:global(body) {
		max-width: 100vw;
		overflow-x: clip;
		word-break: keep-all;
		overflow-wrap: anywhere;
	}
	:global(img),
	:global(svg),
	:global(video),
	:global(canvas),
	:global(iframe) {
		max-width: 100%;
		height: auto;
	}
	:global(body > div) {
		max-width: 100vw;
	}

	/* dartlab 다크 톤 scrollbar 통일 — 모든 element 의 native scrollbar.
	   WebKit 기반 (Chrome/Safari/Edge) + Firefox scrollbar-color. */
	:global(*::-webkit-scrollbar) {
		width: 10px;
		height: 10px;
	}
	:global(*::-webkit-scrollbar-track) {
		background: transparent;
	}
	:global(*::-webkit-scrollbar-thumb) {
		background: #334155;
		border-radius: 5px;
		border: 2px solid transparent;
		background-clip: padding-box;
	}
	:global(*::-webkit-scrollbar-thumb:hover) {
		background: #475569;
		background-clip: padding-box;
		border: 2px solid transparent;
	}
	:global(*::-webkit-scrollbar-corner) {
		background: transparent;
	}
	:global(html) {
		scrollbar-color: #334155 transparent;
		scrollbar-width: thin;
	}
</style>
