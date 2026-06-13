<script lang="ts">
	import type { Snippet } from 'svelte';
	import type { Bilingual, Lang, Prov } from '../data/types';
	import { tx, PROV } from './helpers';

	interface Props {
		title: Bilingual | string;
		sub?: Bilingual | string;
		lang: Lang;
		className?: string;
		flush?: boolean;
		prov?: Prov;
		right?: Snippet;
		children: Snippet;
	}
	let { title, sub, lang, className = '', flush = false, prov, right, children }: Props = $props();
	const p = $derived(prov ? PROV[prov] : null);
</script>

<section class={'panel ' + className}>
	<header class="panelHead">
		<span class="panelTitle">{tx(title, lang)}</span>
		{#if p}
			<span class={'provTag ' + p.cls} title={lang === 'en' ? p.t.en : p.t.kr}>{lang === 'en' ? p.en : p.kr}</span>
		{/if}
		{#if sub}<span class="panelSub">{tx(sub, lang)}</span>{/if}
		<span class="panelRight">{#if right}{@render right()}{/if}</span>
	</header>
	<div class={'panelBody' + (flush ? ' flush' : '')}>
		{@render children()}
	</div>
</section>
