<script lang="ts">
	import { Sparkles } from 'lucide-svelte';

	let { examples = [] }: { examples?: string[] } = $props();
</script>

{#if examples.length > 0}
	<section class="examples" aria-label="사용 예시">
		<header class="head">
			<p class="kicker">예시</p>
			<h2>이런 질문이 들어오면 이 skill 을 쓴다</h2>
		</header>
		<ul class="list">
			{#each examples as ex}
				<li class="item">
					<Sparkles size={12} class="item-icon" />
					<span>{ex}</span>
				</li>
			{/each}
		</ul>
	</section>
{/if}

<style>
	.examples {
		margin: 1.25rem 0;
		padding: 1.1rem 1.25rem;
		border: 1px solid var(--dl-line);
		border-left: 3px solid var(--dl-info);
		border-radius: var(--dl-r-md);
		background: var(--dl-bg-raised);
	}

	.head {
		margin-bottom: 0.7rem;
	}

	.kicker {
		margin: 0 0 0.2rem;
		color: var(--dl-info);
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

	.list {
		list-style: none;
		margin: 0;
		padding: 0;
		display: flex;
		flex-direction: column;
		gap: 0.35rem;
	}

	.item {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		padding: 0.4rem 0.65rem;
		border-radius: var(--dl-r-sm);
		background: var(--dl-bg-overlay);
		color: var(--dl-ink);
		font-size: 0.86rem;
		line-height: 1.5;
	}

	.item :global(.item-icon) {
		flex-shrink: 0;
		color: var(--dl-info);
	}
</style>
