<script lang="ts">
	// @ts-nocheck
	import DonateCTA from '$lib/components/sections/DonateCTA.svelte';

	let { data } = $props();
	const stockCode = $derived(data?.stockCode ?? '');
	const mapLink = $derived(data?.mapLink ?? '/map');
</script>

<DonateCTA variant="full" showMap showRepo mapHref={mapLink} />

<div class="dl-dash-footer mono container">
	{stockCode} · v16 · DART 전자공시 · <a href="/">dartlab.io</a>
</div>

<style>
	.dl-dash-footer {
		padding: 20px 32px 48px;
		text-align: center;
		font-size: 11px;
		color: var(--text-faint);
	}
	.dl-dash-footer a {
		color: var(--text-dim);
		text-decoration: underline;
	}
</style>
