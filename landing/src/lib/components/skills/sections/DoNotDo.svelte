<script lang="ts">
	import { AlertTriangle, Ban } from 'lucide-svelte';

	let {
		failureModes = [],
		forbidden = []
	}: {
		failureModes?: string[];
		forbidden?: string[];
	} = $props();
</script>

{#if failureModes.length > 0 || forbidden.length > 0}
	<section class="dont" aria-label="흔한 실패와 금지 사항">
		<header class="head">
			<p class="kicker">실패 회피</p>
			<h2>흔한 실패 · 절대 금지</h2>
		</header>

		{#if failureModes.length > 0}
			<div class="block warn">
				<div class="block-head">
					<AlertTriangle size={14} class="block-icon" />
					<span class="block-title">흔한 실패</span>
				</div>
				<ul>
					{#each failureModes as item}
						<li>{item}</li>
					{/each}
				</ul>
			</div>
		{/if}

		{#if forbidden.length > 0}
			<div class="block bad">
				<div class="block-head">
					<Ban size={14} class="block-icon" />
					<span class="block-title">절대 금지</span>
				</div>
				<ul>
					{#each forbidden as item}
						<li>{item}</li>
					{/each}
				</ul>
			</div>
		{/if}
	</section>
{/if}

<style>
	.dont {
		margin: 1.25rem 0;
		padding: 1.1rem 1.25rem;
		border: 1px solid var(--dl-line);
		border-left: 3px solid var(--dl-bad);
		border-radius: var(--dl-r-md);
		background: var(--dl-bg-raised);
	}

	.head {
		margin-bottom: 0.85rem;
	}

	.kicker {
		margin: 0 0 0.2rem;
		color: var(--dl-bad);
		font-size: 0.64rem;
		letter-spacing: 0.1em;
		text-transform: uppercase;
		font-weight: 700;
	}

	.head h2 {
		margin: 0;
		font-size: 1rem;
		color: var(--dl-ink-print);
		font-weight: 600;
	}

	.block + .block {
		margin-top: 0.7rem;
	}

	.block-head {
		display: flex;
		align-items: center;
		gap: 0.4rem;
		margin-bottom: 0.4rem;
	}

	.block-title {
		font-size: 0.78rem;
		font-weight: 600;
		font-family: var(--dl-font-mono);
		text-transform: lowercase;
		letter-spacing: 0.04em;
	}

	.block.warn .block-title { color: var(--dl-warn); }
	.block.warn :global(.block-icon) { color: var(--dl-warn); }
	.block.bad .block-title { color: var(--dl-bad); }
	.block.bad :global(.block-icon) { color: var(--dl-bad); }

	.block ul {
		list-style: disc;
		margin: 0;
		padding-left: 1.2rem;
		color: var(--dl-ink-mute);
		font-size: 0.86rem;
		line-height: 1.55;
	}

	.block li + li {
		margin-top: 0.18rem;
	}
</style>
