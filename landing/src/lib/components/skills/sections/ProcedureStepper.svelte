<script lang="ts">
	let { steps = [] }: { steps?: string[] } = $props();
</script>

{#if steps.length > 0}
	<section class="stepper" aria-label="실행 절차">
		<header class="head">
			<p class="kicker">절차</p>
			<h2>실행 순서</h2>
		</header>
		<ol class="steps">
			{#each steps as step, i}
				<li class="step">
					<span class="step-num">{i + 1}</span>
					<p class="step-text">{step}</p>
				</li>
			{/each}
		</ol>
	</section>
{/if}

<style>
	.stepper {
		margin: 1.5rem 0;
		padding: 1.25rem 1.4rem;
		border: 1px solid var(--dl-line);
		border-left: 3px solid var(--dl-orange);
		border-radius: var(--dl-r-md);
		background: var(--dl-bg-raised);
	}

	.head {
		margin-bottom: 1rem;
		padding-bottom: 0.75rem;
		border-bottom: 1px solid var(--dl-line);
	}

	.kicker {
		margin: 0 0 0.25rem;
		color: var(--dl-orange);
		font-size: 0.66rem;
		letter-spacing: 0.1em;
		text-transform: uppercase;
		font-weight: 700;
	}

	.head h2 {
		margin: 0;
		font-size: 1.1rem;
		color: var(--dl-ink-print);
		font-family: var(--dl-font-head);
		font-weight: 600;
	}

	.steps {
		list-style: none;
		margin: 0;
		padding: 0;
		display: flex;
		flex-direction: column;
		gap: 0.7rem;
	}

	.step {
		display: flex;
		gap: 0.85rem;
		align-items: flex-start;
		padding: 0.6rem 0.8rem;
		border-radius: var(--dl-r-sm);
		background: var(--dl-bg-overlay);
	}

	.step-num {
		flex-shrink: 0;
		display: inline-flex;
		align-items: center;
		justify-content: center;
		width: 26px;
		height: 26px;
		border-radius: 50%;
		background: var(--dl-orange-soft);
		color: var(--dl-orange);
		font-family: var(--dl-font-mono);
		font-size: 0.78rem;
		font-weight: 700;
	}

	.step-text {
		margin: 0.18rem 0 0;
		flex: 1;
		font-size: 0.9rem;
		line-height: 1.6;
		color: var(--dl-ink);
	}
</style>
