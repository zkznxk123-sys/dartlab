<script lang="ts">
	import '../app.css';
	import type { Snippet } from 'svelte';
	import CommandPalette from '$lib/components/CommandPalette.svelte';

	let { children }: { children: Snippet } = $props();
</script>

<CommandPalette />
{@render children()}

<style>
	/* 전역 모바일 보호 — viewport 가로 스크롤 차단
	   app.css에 두면 Tailwind v4 빌드에서 누락되므로 svelte global로 강제 */
	:global(html) {
		max-width: 100vw;
		overflow-x: hidden;
	}
	:global(body) {
		max-width: 100vw;
		overflow-x: hidden;
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
</style>
