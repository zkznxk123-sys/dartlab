<script lang="ts">
	import { base } from '$app/paths';
	import { isCatalogSkillId, getSkillMeta } from '$lib/skills/catalog';
	import { ArrowRight, Link2 } from 'lucide-svelte';

	interface RecipeStep {
		skillId: string;
		note?: string;
	}

	let {
		recipeSteps = [],
		linkedSkills = []
	}: {
		recipeSteps?: RecipeStep[];
		linkedSkills?: string[];
	} = $props();

	function stepTitle(skillId: string): string {
		return getSkillMeta(skillId)?.title ?? skillId;
	}

	function stepHref(skillId: string): string | null {
		return isCatalogSkillId(skillId) ? `${base}/skills/${skillId}` : null;
	}

	const hasRecipe = $derived(recipeSteps.length > 0);
	const onlyLinked = $derived(!hasRecipe && linkedSkills.length > 0);
</script>

{#if hasRecipe}
	<section class="recipe" aria-label="연계 절차">
		<header class="head">
			<p class="kicker">연계 절차</p>
			<h2>이 절차의 단계</h2>
		</header>
		<ol class="steps">
			{#each recipeSteps as step, i}
				{@const href = stepHref(step.skillId)}
				{@const title = stepTitle(step.skillId)}
				<li class="step">
					<span class="num">{i + 1}</span>
					<div class="body">
						<div class="title-row">
							{#if href}
								<a class="title" href={href}>
									{title}
									<ArrowRight size={12} class="arrow" />
								</a>
							{:else}
								<span class="title">{title}</span>
							{/if}
							<code class="ref">{step.skillId}</code>
						</div>
						{#if step.note}
							<p class="note">{step.note}</p>
						{/if}
					</div>
				</li>
			{/each}
		</ol>
	</section>
{:else if onlyLinked}
	<section class="linked-only" aria-label="이어 가기">
		<header class="head">
			<p class="kicker linked-kicker">이어 가기</p>
		</header>
		<ul class="chip-row">
			{#each linkedSkills as sid}
				{@const href = stepHref(sid)}
				{@const title = stepTitle(sid)}
				<li>
					{#if href}
						<a class="chip" href={href}>
							<Link2 size={11} />
							<span>{title}</span>
							<code>{sid}</code>
						</a>
					{:else}
						<span class="chip dim">
							<Link2 size={11} />
							<span>{title}</span>
							<code>{sid}</code>
						</span>
					{/if}
				</li>
			{/each}
		</ul>
	</section>
{/if}

<style>
	.recipe {
		margin: 1.5rem 0;
		padding: 1.25rem 1.4rem;
		border: 1px solid var(--dl-line);
		border-left: 3px solid var(--dl-cat-engines);
		border-radius: var(--dl-r-md);
		background: linear-gradient(
			135deg,
			rgba(251, 146, 60, 0.06),
			rgba(15, 18, 25, 0.45)
		);
	}

	.head {
		margin-bottom: 1rem;
		padding-bottom: 0.7rem;
		border-bottom: 1px solid var(--dl-line);
	}

	.kicker {
		margin: 0 0 0.25rem;
		color: var(--dl-cat-engines);
		font-size: 0.66rem;
		letter-spacing: 0.1em;
		text-transform: uppercase;
		font-weight: 700;
	}

	.linked-kicker {
		color: var(--dl-cat-start);
	}

	.head h2 {
		margin: 0;
		font-size: 1.05rem;
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
		gap: 0.55rem;
	}

	.step {
		display: flex;
		gap: 0.85rem;
		align-items: flex-start;
		padding: 0.7rem 0.9rem;
		border: 1px solid var(--dl-line);
		border-radius: var(--dl-r-sm);
		background: var(--dl-bg-overlay);
		transition: border-color var(--dl-dur-hover), transform var(--dl-dur-hover);
	}

	.step:has(a:hover) {
		border-color: var(--dl-cat-engines);
		transform: translateX(2px);
	}

	.num {
		flex-shrink: 0;
		display: inline-flex;
		align-items: center;
		justify-content: center;
		width: 26px;
		height: 26px;
		border-radius: 50%;
		background: var(--dl-orange-soft);
		color: var(--dl-cat-engines);
		font-family: var(--dl-font-mono);
		font-size: 0.78rem;
		font-weight: 700;
	}

	.body {
		flex: 1;
		min-width: 0;
	}

	.title-row {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		flex-wrap: wrap;
	}

	.title {
		display: inline-flex;
		align-items: center;
		gap: 0.3rem;
		color: var(--dl-ink-print);
		font-size: 0.92rem;
		font-weight: 600;
		text-decoration: none;
	}

	a.title:hover {
		color: var(--dl-cat-engines);
	}

	.title :global(.arrow) {
		color: var(--dl-ink-faint);
		transition: color var(--dl-dur-hover), transform var(--dl-dur-hover);
	}

	a.title:hover :global(.arrow) {
		color: var(--dl-cat-engines);
		transform: translateX(2px);
	}

	.ref {
		padding: 0.05rem 0.35rem;
		border-radius: var(--dl-r-sm);
		background: var(--dl-bg-modal);
		color: var(--dl-ink-dim);
		font-family: var(--dl-font-mono);
		font-size: 0.66rem;
	}

	.note {
		margin: 0.3rem 0 0;
		font-size: 0.83rem;
		line-height: 1.55;
		color: var(--dl-ink-mute);
	}

	.linked-only {
		margin: 1.25rem 0;
		padding: 1rem 1.2rem;
		border: 1px solid var(--dl-line);
		border-left: 3px solid var(--dl-cat-start);
		border-radius: var(--dl-r-md);
		background: var(--dl-bg-raised);
	}

	.linked-only .head {
		margin-bottom: 0.7rem;
		padding-bottom: 0;
		border-bottom: none;
	}

	.chip-row {
		list-style: none;
		margin: 0;
		padding: 0;
		display: flex;
		flex-wrap: wrap;
		gap: 0.4rem;
	}

	.chip {
		display: inline-flex;
		align-items: center;
		gap: 0.35rem;
		padding: 0.32rem 0.6rem;
		border: 1px solid var(--dl-line-strong);
		border-radius: var(--dl-r-pill);
		background: var(--dl-bg-overlay);
		color: var(--dl-ink-mute);
		font-size: 0.78rem;
		text-decoration: none;
		transition: border-color var(--dl-dur-hover), color var(--dl-dur-hover);
	}

	a.chip:hover {
		border-color: var(--dl-cat-start);
		color: var(--dl-cat-start);
	}

	.chip code {
		font-family: var(--dl-font-mono);
		font-size: 0.66rem;
		color: var(--dl-ink-dim);
	}

	.chip.dim {
		opacity: 0.6;
	}
</style>
