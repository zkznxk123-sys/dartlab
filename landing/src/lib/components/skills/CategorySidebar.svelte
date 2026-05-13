<script lang="ts">
	import {
		canonicalEngineSubGroups,
		canonicalEngineSubGroupSet,
		getSkillSubGroup,
		skillCategoryOrder,
		skillCategoryTitle,
		skills
	} from '$lib/skills/catalog';
	import { ChevronDown, ChevronRight, Layers } from 'lucide-svelte';

	interface SkillDoc {
		id: string;
		title: string;
		category: string;
		categoryTitle?: string;
	}

	interface CategoryMeta {
		id: string;
		title: string;
		description?: string;
		count: number;
	}

	let {
		selectedCategory = $bindable('all'),
		selectedSubGroup = $bindable<string | null>(null)
	}: {
		selectedCategory?: string;
		selectedSubGroup?: string | null;
	} = $props();

	const categories = $derived.by(() => {
		return skillCategoryOrder.map((id) => {
			const items = skills.filter((s) => s.category === id);
			return {
				id,
				title: skillCategoryTitle[id] ?? id,
				description: undefined,
				count: items.length
			};
		});
	});

	function getSubGroups(category: string) {
		const grouped = new Map<string, number>();
		for (const s of skills) {
			if (s.category !== category) continue;
			const sg = getSkillSubGroup(s);
			if (category === 'engines' && (!sg || !canonicalEngineSubGroupSet.has(sg))) continue;
			if (sg) grouped.set(sg, (grouped.get(sg) ?? 0) + 1);
		}
		if (category === 'engines') {
			return canonicalEngineSubGroups
				.map((id) => ({ id, count: grouped.get(id) ?? 0 }))
				.filter((group) => group.count > 0);
		}
		return [...grouped.entries()]
			.sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))
			.map(([id, count]) => ({ id, count }));
	}

	const engineSubGroups = $derived(getSubGroups('engines'));
	const recipeSubGroups = $derived(getSubGroups('recipes'));

	let enginesExpanded = $state(true);
	let recipesExpanded = $state(true);

	function selectCategory(id: string) {
		selectedCategory = id;
		selectedSubGroup = null;
		if (id === 'engines') enginesExpanded = true;
		if (id === 'recipes') recipesExpanded = true;
	}

	function toggleGroup(category: string, e: MouseEvent) {
		e.stopPropagation();
		if (category === 'engines') enginesExpanded = !enginesExpanded;
		if (category === 'recipes') recipesExpanded = !recipesExpanded;
	}

	function selectSubGroup(category: string, sg: string) {
		selectedCategory = category;
		selectedSubGroup = sg;
		if (category === 'engines') enginesExpanded = true;
		if (category === 'recipes') recipesExpanded = true;
	}

	function selectAll() {
		selectedCategory = 'all';
		selectedSubGroup = null;
	}

	const totalCount = $derived(skills.length);
</script>

<aside class="sidebar" aria-label="Skill categories">
	<div class="head">
		<p class="head-kicker">Catalog</p>
		<p class="head-title">{totalCount} skills · 5 카테고리</p>
	</div>

	<div class="cat-row all-row" class:active={selectedCategory === 'all'}>
		<button class="cat-main" onclick={selectAll}>
			<Layers size={14} class="row-icon" />
			<span class="cat-name">All</span>
			<span class="cat-count">{totalCount}</span>
		</button>
	</div>

	{#each categories as cat}
		<div class="cat-block">
			<div
				class="cat-row cat-{cat.id}"
				class:active={selectedCategory === cat.id && !selectedSubGroup}
			>
				<button
					class="cat-main"
					onclick={() => selectCategory(cat.id)}
					title={cat.description ?? ''}
				>
					{#if cat.id === 'engines' || cat.id === 'recipes'}
						<span class="cat-chevron-spacer"></span>
					{:else}
						<span class="cat-dot"></span>
					{/if}
					<span class="cat-name">{cat.title}</span>
					<span class="cat-count">{cat.count}</span>
				</button>
				{#if cat.id === 'engines' || cat.id === 'recipes'}
					<button
						class="expand-btn"
						class:recipes={cat.id === 'recipes'}
						onclick={(e) => toggleGroup(cat.id, e)}
						aria-label={(cat.id === 'engines' ? enginesExpanded : recipesExpanded) ? `Collapse ${cat.id}` : `Expand ${cat.id}`}
					>
						{#if cat.id === 'engines' ? enginesExpanded : recipesExpanded}
							<ChevronDown size={14} />
						{:else}
							<ChevronRight size={14} />
						{/if}
					</button>
				{/if}
			</div>

			{#if cat.id === 'engines' && enginesExpanded}
				<ul class="sub-list">
					{#each engineSubGroups as sg}
						<li>
							<button
								class="sub-row"
								class:active={selectedCategory === 'engines' && selectedSubGroup === sg.id}
								onclick={() => selectSubGroup('engines', sg.id)}
							>
								<span class="sub-name">{sg.id}</span>
								<span class="sub-count">{sg.count}</span>
							</button>
						</li>
					{/each}
				</ul>
			{/if}

			{#if cat.id === 'recipes' && recipesExpanded}
				<ul class="sub-list recipes">
					{#each recipeSubGroups as sg}
						<li>
							<button
								class="sub-row recipes"
								class:active={selectedCategory === 'recipes' && selectedSubGroup === sg.id}
								onclick={() => selectSubGroup('recipes', sg.id)}
							>
								<span class="sub-name">{sg.id}</span>
								<span class="sub-count">{sg.count}</span>
							</button>
						</li>
					{/each}
				</ul>
			{/if}
		</div>
	{/each}
</aside>

<style>
	.sidebar {
		position: sticky;
		top: 5rem;
		display: flex;
		flex-direction: column;
		gap: 0.25rem;
		padding: 1rem 0.85rem;
		border: 1px solid var(--dl-line);
		border-radius: var(--dl-r-md);
		background: var(--dl-bg-raised);
		max-height: calc(100vh - 6rem);
		overflow-y: auto;
	}

	.head {
		padding: 0 0.4rem 0.85rem;
		border-bottom: 1px solid var(--dl-line);
		margin-bottom: 0.6rem;
	}

	.head-kicker {
		margin: 0;
		font-size: 0.65rem;
		letter-spacing: 0.1em;
		text-transform: uppercase;
		font-weight: 700;
		color: var(--dl-orange);
	}

	.head-title {
		margin: 0.2rem 0 0;
		font-size: 0.78rem;
		color: var(--dl-ink-mute);
		font-family: var(--dl-font-mono);
	}

	.cat-row {
		display: flex;
		align-items: center;
		width: 100%;
		border-radius: var(--dl-r-sm);
		transition: background var(--dl-dur-hover) var(--dl-ease-soft);
	}

	.cat-row:hover {
		background: var(--dl-bg-overlay);
	}

	.cat-row.active {
		background: var(--dl-bg-overlay);
	}

	.cat-main {
		display: flex;
		flex: 1;
		align-items: center;
		gap: 0.55rem;
		min-width: 0;
		padding: 0.5rem 0.55rem;
		border: none;
		background: transparent;
		color: var(--dl-ink-mute);
		font-size: 0.85rem;
		text-align: left;
		cursor: pointer;
		border-radius: var(--dl-r-sm);
		transition: color var(--dl-dur-hover) var(--dl-ease-soft);
	}

	.cat-row:hover .cat-main {
		color: var(--dl-ink);
	}

	.cat-row.active .cat-main {
		color: var(--dl-ink-print);
		font-weight: 600;
	}

	.all-row .cat-main {
		flex: 1;
	}

	.cat-name {
		flex: 1;
	}

	.cat-count {
		padding: 0.05rem 0.4rem;
		border-radius: var(--dl-r-pill);
		background: var(--dl-bg-modal);
		color: var(--dl-ink-dim);
		font-size: 0.7rem;
		font-family: var(--dl-font-mono);
	}

	.cat-row.active .cat-count {
		color: var(--dl-ink);
	}

	.cat-dot {
		display: inline-block;
		width: 8px;
		height: 8px;
		border-radius: 50%;
		background: var(--dl-ink-dim);
		flex-shrink: 0;
	}

	.cat-chevron-spacer {
		display: inline-block;
		width: 8px;
		flex-shrink: 0;
	}

	.cat-start .cat-dot { background: var(--dl-cat-start); }
	.cat-runtime .cat-dot { background: var(--dl-cat-runtime); }
	.cat-operation .cat-dot { background: var(--dl-cat-operation); }
	.cat-recipes .cat-dot { background: var(--dl-cat-recipes); }

	.expand-btn {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		width: 24px;
		height: 24px;
		margin-right: 0.25rem;
		padding: 0;
		border: none;
		border-radius: 3px;
		background: transparent;
		color: var(--dl-cat-engines);
		cursor: pointer;
		transition: background var(--dl-dur-hover);
	}

	.expand-btn:hover {
		background: var(--dl-cat-engines-soft);
	}

	.expand-btn.recipes {
		color: var(--dl-cat-recipes);
	}

	.expand-btn.recipes:hover {
		background: var(--dl-cat-recipes-soft);
	}

	.sub-list {
		list-style: none;
		margin: 0.3rem 0 0.3rem 1.4rem;
		padding: 0 0 0 0.35rem;
		border-left: 1px solid var(--dl-line);
		max-height: 18rem;
		overflow-y: auto;
	}

	.sub-list li + li {
		margin-top: 0.1rem;
	}

	.sub-row {
		display: flex;
		align-items: center;
		gap: 0.45rem;
		width: 100%;
		padding: 0.32rem 0.45rem;
		border: none;
		border-radius: var(--dl-r-sm);
		background: transparent;
		color: var(--dl-ink-dim);
		font-size: 0.78rem;
		font-family: var(--dl-font-mono);
		text-align: left;
		cursor: pointer;
		transition: background var(--dl-dur-hover);
	}

	.sub-row:hover {
		background: var(--dl-cat-engines-soft);
		color: var(--dl-cat-engines);
	}

	.sub-row.active {
		background: var(--dl-cat-engines-soft);
		color: var(--dl-cat-engines);
		font-weight: 600;
	}

	.sub-row.recipes:hover {
		background: var(--dl-cat-recipes-soft);
		color: var(--dl-cat-recipes);
	}

	.sub-row.recipes.active {
		background: var(--dl-cat-recipes-soft);
		color: var(--dl-cat-recipes);
	}

	.sub-name { flex: 1; }
	.sub-count {
		font-size: 0.68rem;
		color: var(--dl-ink-faint);
	}

	@media (max-width: 920px) {
		.sidebar {
			position: static;
			max-height: none;
		}
	}
</style>
