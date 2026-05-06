<script lang="ts">
	import { CheckSquare2 } from 'lucide-svelte';

	let {
		items = [],
		title = '필요한 근거',
		kicker = '검증'
	}: {
		items?: string[];
		title?: string;
		kicker?: string;
	} = $props();
</script>

{#if items.length > 0}
	<section class="checklist" aria-label={title}>
		<header class="head">
			<p class="kicker">{kicker}</p>
			<h2>{title}</h2>
		</header>
		<ul class="items">
			{#each items as item}
				<li class="item">
					<CheckSquare2 size={14} class="item-icon" />
					<span>{item}</span>
				</li>
			{/each}
		</ul>
	</section>
{/if}

<style>
	.checklist {
		margin: 1.25rem 0;
		padding: 1.1rem 1.25rem;
		border: 1px solid var(--dl-line);
		border-left: 3px solid var(--dl-good);
		border-radius: var(--dl-r-md);
		background: var(--dl-bg-raised);
	}

	.head {
		margin-bottom: 0.7rem;
	}

	.kicker {
		margin: 0 0 0.2rem;
		color: var(--dl-good);
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

	.items {
		list-style: none;
		margin: 0;
		padding: 0;
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
		gap: 0.4rem 0.85rem;
	}

	.item {
		display: flex;
		align-items: center;
		gap: 0.45rem;
		font-size: 0.85rem;
		color: var(--dl-ink-mute);
		line-height: 1.45;
	}

	.item :global(.item-icon) {
		flex-shrink: 0;
		color: var(--dl-good);
	}
</style>
