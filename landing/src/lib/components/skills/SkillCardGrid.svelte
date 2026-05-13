<script lang="ts">
	import { base } from '$app/paths';
	import { getSkillSubGroup } from '$lib/skills/catalog';
	import { ArrowUpRight } from 'lucide-svelte';

	interface RuntimeEntry {
		status?: string;
	}

	interface SkillDoc {
		id: string;
		title: string;
		category: string;
		categoryTitle?: string;
		status: string;
		purpose: string;
		runtimeCompatibility?: Record<string, RuntimeEntry>;
	}

	let {
		skills,
		selectedCategory = 'all',
		selectedSubGroup = null,
		query = ''
	}: {
		skills: SkillDoc[];
		selectedCategory?: string;
		selectedSubGroup?: string | null;
		query?: string;
	} = $props();

	const filtered = $derived.by(() => {
		const q = query.trim().toLowerCase();
		return skills.filter((s) => {
			if (selectedCategory !== 'all' && s.category !== selectedCategory) return false;
			if (selectedSubGroup && getSkillSubGroup(s) !== selectedSubGroup) return false;
			if (q) {
				const haystack = `${s.title} ${s.id} ${s.purpose}`.toLowerCase();
				if (!haystack.includes(q)) return false;
			}
			return true;
		});
	});

	const runtimeOrder = ['localPython', 'mcp', 'webAi', 'pyodide'];
	const runtimeLabel: Record<string, string> = {
		localPython: 'Local',
		mcp: 'MCP',
		webAi: 'Web AI',
		pyodide: 'Pyodide'
	};

	function runtimeChips(skill: SkillDoc): { label: string; status: string }[] {
		const rc = skill.runtimeCompatibility ?? {};
		return runtimeOrder
			.map((k) => ({ key: k, status: rc[k]?.status ?? 'unknown' }))
			.filter((x) => x.status === 'supported' || x.status === 'limited')
			.map((x) => ({ label: runtimeLabel[x.key], status: x.status }));
	}

	function statusBadgeClass(status: string): string {
		if (status === 'observed') return 'st-observed';
		if (status === 'unverified') return 'st-unverified';
		return 'st-unknown';
	}
</script>

<section class="grid-wrap" aria-label="Skill grid">
	<header class="grid-meta">
		<p class="count"><strong>{filtered.length}</strong> skills</p>
		{#if selectedSubGroup}
			<p class="filter-tag">filter: <code>{selectedCategory}.{selectedSubGroup}</code></p>
		{:else if selectedCategory !== 'all'}
			<p class="filter-tag">filter: <code>{selectedCategory}</code></p>
		{/if}
	</header>

	{#if filtered.length === 0}
		<p class="empty">조건에 맞는 skill 없음.</p>
	{:else}
		<ul class="grid">
			{#each filtered as skill (skill.id)}
				<li>
					<a href="{base}/skills/{skill.id}" class="card cat-{skill.category}">
						<div class="card-head">
							<span class="card-cat">{skill.categoryTitle ?? skill.category}</span>
							<span class="card-status {statusBadgeClass(skill.status)}">{skill.status}</span>
							<ArrowUpRight size={14} class="card-arrow" />
						</div>
						<h3 class="card-title">{skill.title}</h3>
						<p class="card-purpose">{skill.purpose}</p>
						<footer class="card-foot">
							<code class="card-id">{skill.id}</code>
							<div class="card-runtimes">
								{#each runtimeChips(skill) as chip}
									<span class="rt-chip" class:limited={chip.status === 'limited'}>
										{chip.label}
									</span>
								{/each}
							</div>
						</footer>
					</a>
				</li>
			{/each}
		</ul>
	{/if}
</section>

<style>
	.grid-wrap {
		min-width: 0;
	}

	.grid-meta {
		display: flex;
		align-items: baseline;
		gap: 0.85rem;
		padding-bottom: 0.85rem;
		border-bottom: 1px solid var(--dl-line);
		margin-bottom: 1rem;
	}

	.count {
		margin: 0;
		font-size: 0.85rem;
		color: var(--dl-ink-mute);
		font-family: var(--dl-font-mono);
	}

	.count strong {
		color: var(--dl-ink-print);
		font-weight: 700;
	}

	.filter-tag {
		margin: 0;
		font-size: 0.75rem;
		color: var(--dl-ink-dim);
	}

	.filter-tag code {
		padding: 0.08rem 0.4rem;
		border-radius: var(--dl-r-sm);
		background: var(--dl-bg-overlay);
		color: var(--dl-orange);
		font-family: var(--dl-font-mono);
		font-size: 0.74rem;
	}

	.grid {
		list-style: none;
		margin: 0;
		padding: 0;
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
		gap: 0.95rem;
	}

	.card {
		display: flex;
		flex-direction: column;
		gap: 0.55rem;
		min-height: 180px;
		padding: 1rem 1.1rem;
		border: 1px solid var(--dl-line);
		border-left: 3px solid var(--dl-ink-faint);
		border-radius: var(--dl-r-md);
		background: var(--dl-bg-raised);
		text-decoration: none;
		color: inherit;
		transition: border-color var(--dl-dur-hover) var(--dl-ease-soft),
			background var(--dl-dur-hover) var(--dl-ease-soft),
			transform var(--dl-dur-hover) var(--dl-ease-soft);
	}

	.card:hover {
		background: var(--dl-bg-overlay);
		transform: translateY(-1px);
	}

	.card.cat-start { border-left-color: var(--dl-cat-start); }
	.card.cat-start:hover { border-color: var(--dl-cat-start); }
	.card.cat-runtime { border-left-color: var(--dl-cat-runtime); }
	.card.cat-runtime:hover { border-color: var(--dl-cat-runtime); }
	.card.cat-operation { border-left-color: var(--dl-cat-operation); }
	.card.cat-operation:hover { border-color: var(--dl-cat-operation); }
	.card.cat-engines { border-left-color: var(--dl-cat-engines); }
	.card.cat-engines:hover { border-color: var(--dl-cat-engines); }
	.card.cat-recipes { border-left-color: var(--dl-cat-recipes); }
	.card.cat-recipes:hover { border-color: var(--dl-cat-recipes); }

	.card-head {
		display: flex;
		align-items: center;
		gap: 0.45rem;
	}

	.card-cat {
		font-size: 0.66rem;
		letter-spacing: 0.08em;
		text-transform: uppercase;
		font-weight: 700;
		color: var(--dl-ink-mute);
	}

	.card.cat-start .card-cat { color: var(--dl-cat-start); }
	.card.cat-runtime .card-cat { color: var(--dl-cat-runtime); }
	.card.cat-operation .card-cat { color: var(--dl-cat-operation); }
	.card.cat-engines .card-cat { color: var(--dl-cat-engines); }
	.card.cat-recipes .card-cat { color: var(--dl-cat-recipes); }

	.card-status {
		padding: 0.04rem 0.4rem;
		border-radius: var(--dl-r-sm);
		font-family: var(--dl-font-mono);
		font-size: 0.62rem;
		font-weight: 600;
		text-transform: lowercase;
	}

	.st-observed {
		background: var(--dl-good);
		color: #062f1c;
	}

	.st-unverified {
		background: rgba(251, 191, 36, 0.15);
		color: var(--dl-warn);
	}

	.st-unknown {
		background: var(--dl-bg-modal);
		color: var(--dl-ink-dim);
	}

	.card :global(.card-arrow) {
		margin-left: auto;
		color: var(--dl-ink-faint);
	}

	.card:hover :global(.card-arrow) {
		color: var(--dl-orange);
	}

	.card-title {
		margin: 0;
		font-size: 1rem;
		line-height: 1.3;
		color: var(--dl-ink-print);
		font-weight: 600;
	}

	.card-purpose {
		margin: 0;
		flex: 1;
		font-size: 0.83rem;
		line-height: 1.55;
		color: var(--dl-ink-mute);
		display: -webkit-box;
		-webkit-line-clamp: 3;
		-webkit-box-orient: vertical;
		overflow: hidden;
	}

	.card-foot {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		justify-content: space-between;
		padding-top: 0.55rem;
		border-top: 1px solid var(--dl-line);
		margin-top: auto;
	}

	.card-id {
		font-family: var(--dl-font-mono);
		font-size: 0.7rem;
		color: var(--dl-ink-dim);
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.card-runtimes {
		display: flex;
		gap: 0.25rem;
		flex-shrink: 0;
	}

	.rt-chip {
		padding: 0.05rem 0.4rem;
		border-radius: var(--dl-r-sm);
		background: var(--dl-bg-modal);
		color: var(--dl-ink-mute);
		font-family: var(--dl-font-mono);
		font-size: 0.62rem;
		font-weight: 500;
	}

	.rt-chip.limited {
		opacity: 0.6;
	}

	.empty {
		padding: 3rem 1rem;
		text-align: center;
		color: var(--dl-ink-dim);
		font-size: 0.9rem;
	}
</style>
